from typing import Any, Dict, Optional, Tuple
from loguru import logger
import re

from app.core.config import settings
from app.infrastructure.clients.redis_client import redis_cache
from app.infrastructure.clients.llm_clients import ollama_client, gemini_client
from app.infrastructure.engine.duckdb_client import duckdb_client


class AIBudgetManager:
    """Enterprise AI Cost Optimization Engine.

    Intercepts analytical intents, routes to deterministic tools or local models, 
    tracks cloud token costs, and handles semantic caching.
    """

    def __init__(self):
        self.cache = redis_cache
        self.ollama = ollama_client
        self.gemini = gemini_client

    def is_deterministic(self, user_query: str) -> bool:
        """Analyze user query keywords to determine if the question can be resolved

        entirely with SQL, statistics, or Polars (no LLM).
        """
        query_lower = user_query.lower().strip()
        
        deterministic_patterns = [
            r"\b(average|mean|median|std|min|max|sum|count)\b",
            r"\b(duplicate|missing|null|empty)\b",
            r"\b(kpi|metric|total|percentage|ratio)\b",
            r"\b(correlation|covariance|significance|t-test|anova)\b",
            r"\b(forecast|predict|regression|trend|timeseries)\b",
            r"\b(anomal|outlier|deviation)\b"
        ]
        
        for pattern in deterministic_patterns:
            if re.search(pattern, query_lower):
                return True
                
        return False

    def get_current_daily_spend(self) -> float:
        """Fetch current daily spend from Redis."""
        spend = self.cache.get("aura:budget:daily_spend")
        if not spend:
            return 0.0
        return float(spend)

    def increment_daily_spend(self, amount: float):
        """Deduct token cost from daily budget allowance."""
        current = self.get_current_daily_spend()
        new_spend = current + amount
        # Expire budget record at end of day (86400 seconds)
        self.cache.set("aura:budget:daily_spend", str(new_spend), expire_seconds=86400)
        logger.info(f"Daily budget updated: spent ${new_spend:.5f} / limit ${settings.AI_BUDGET_LIMIT_USD:.2f}")

    async def execute_query(self, dataset_path: str, user_query: str) -> Dict[str, Any]:
        """Routes analysis queries through the cost-optimized decision tree.

        Returns structured analytics output or semantic narration.
        """
        logger.info(f"Received query: '{user_query}' for dataset {dataset_path}")

        # --- STEP 1: Route to Deterministic Code First ---
        if self.is_deterministic(user_query):
            logger.info("Decision: Query matches deterministic signature. Routing to DuckDB engine.")
            
            # Formulate simple queries (this is a simplified demo parser; in production, 
            # parsing is handled by the semantic parser workspace, but we run a mock query here)
            try:
                # E.g., we dynamically count rows and check columns via DuckDB
                row_count_res = duckdb_client.query(f"SELECT count(*) as total_rows FROM read_parquet('{dataset_path}')")
                total_rows = row_count_res[0]["total_rows"]
                
                return {
                    "source": "deterministic_sql",
                    "data": {
                        "query_executed": f"SELECT count(*) FROM read_parquet('{dataset_path}')",
                        "result": {
                            "total_rows": total_rows
                        }
                    },
                    "explanation": f"The dataset contains a total of {total_rows} rows. Computed deterministically."
                }
            except Exception as e:
                logger.error(f"Fallback direct query execution failed: {e}")
                raise ValueError(f"Failed executing deterministic parser: {e}") from e

        # --- STEP 2: Check Semantic Cache for Explanations ---
        cache_key = f"aura:q_cache:{hash(user_query)}"
        cached_result = self.cache.get_json(cache_key)
        
        from app.core.observability import system_monitor
        if cached_result:
            logger.info("Decision: Cache hit. Returning cached response.")
            system_monitor.record_cache_hit()
            return {
                "source": "semantic_cache",
                **cached_result
            }
        
        system_monitor.record_cache_miss()

        # --- STEP 3: Route to Local LLM (Ollama) ---
        # Generate structural evidence first to supply to LLM (never send raw tables)
        evidence_summary = {
            "dataset_info": {
                "path": os.path.basename(dataset_path),
                "columns_count": len(duckdb_client.query(f"DESCRIBE SELECT * FROM read_parquet('{dataset_path}')"))
            },
            "user_question": user_query
        }
        
        system_prompt = (
            "You are AURA, an enterprise decision intelligence agent. "
            "You explain analytical findings using ONLY the provided evidence. "
            "Never hallucinate numbers. Be concise."
        )
        prompt_content = f"Evidence JSON:\n{evidence_summary}\n\nQuestion:\n{user_query}"

        try:
            logger.info("Decision: Routing to Local LLM (Ollama) for zero-cost semantic inference.")
            response_text, in_tokens, out_tokens = await self.ollama.generate(prompt_content, system_prompt)
            
            result = {
                "response": response_text,
                "evidence_references": evidence_summary
            }
            self.cache.set_json(cache_key, result, expire_seconds=1800)
            return {
                "source": "local_llm",
                **result
            }
        except Exception as local_err:
            logger.warning(f"Local LLM (Ollama) request failed or was unavailable: {local_err}. Falling back to Cloud LLM.")

        # --- STEP 4: Fallback to Cloud LLM (Gemini) with Budget Cap ---
        current_spend = self.get_current_daily_spend()
        if current_spend >= settings.AI_BUDGET_LIMIT_USD:
            logger.error("Decision block: Cloud LLM fallback aborted. Daily budget limit exceeded.")
            return {
                "source": "budget_blocker",
                "response": "Unable to generate semantic explanation: daily AI budget limit reached.",
                "evidence_references": evidence_summary
            }

        try:
            logger.info("Decision: Querying Cloud LLM (Gemini). Budget checks passed.")
            response_text, in_tokens, out_tokens = await self.gemini.generate(prompt_content, system_prompt)
            
            # Calculate cost
            input_cost = (in_tokens / 1000) * settings.LLM_COST_PER_1K_INPUT_TOKENS
            output_cost = (out_tokens / 1000) * settings.LLM_COST_PER_1K_OUTPUT_TOKENS
            total_cost = input_cost + output_cost
            
            self.increment_daily_spend(total_cost)

            result = {
                "response": response_text,
                "evidence_references": evidence_summary
            }
            self.cache.set_json(cache_key, result, expire_seconds=3600)
            return {
                "source": "cloud_llm",
                **result
            }
        except Exception as cloud_err:
            logger.error(f"All LLM routing options failed: {cloud_err}")
            # Final rule-based fallback
            return {
                "source": "fallback_rule_engine",
                "response": "Could not generate semantic explanation. Detailed metrics can be inspected directly in the statistics panel.",
                "evidence_references": evidence_summary
            }


ai_budget_manager = AIBudgetManager()
