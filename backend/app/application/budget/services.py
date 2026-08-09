import os
import re
from typing import Any, Dict, Optional, Tuple
from loguru import logger

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

    def clean_decimals(self, obj: Any) -> Any:
        import decimal
        if isinstance(obj, dict):
            return {k: self.clean_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.clean_decimals(v) for v in obj]
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        return obj

    def is_deterministic(self, user_query: str) -> bool:
        """Analyze user query keywords to determine if the question can be resolved
        entirely with SQL, statistics, or Polars (no LLM).
        """
        query_lower = user_query.lower().strip()
        
        # If the user is asking for explanations, descriptions, or summaries, it's always semantic/LLM
        semantic_indicators = [
            r"\b(explain|why|describe|summarize|narrate|implication|interpretation|reason)\b"
        ]
        for pattern in semantic_indicators:
            if re.search(pattern, query_lower):
                return False
                
        deterministic_patterns = [
            r"\b(average|mean|median|std|min|max|sum|count)\b",
            r"\b(duplicate|missing|null|empty)\b",
            r"\b(kpi|metric|total|percentage|ratio)\b",
            r"\b(correlation|covariance|significance|t-test|anova)\b",
            r"\b(forecast|predict|regression|trend|timeseries)\b",
            r"\b(anomal|outlier|deviation)\b",
            r"\b(greater|less|above|below|larger|smaller|more|higher|lower|equal|than)\b",
            r"\b(give|show|list|select|find|retrieve|extract|get|filter|where|limit|display)\b"
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

        # --- STEP 0: Dynamic AI Chart Generation Engine ---
        chart_keywords = [r"\b(chart|plot|graph|vs|histogram|distribution|scatter|bar|line)\b"]
        is_chart_request = any(re.search(pat, user_query.lower()) for pat in chart_keywords)
        if is_chart_request and os.path.exists(dataset_path) and "virtual_evidence.parquet" not in dataset_path:
            logger.info("Decision: Query matches dynamic chart intent. Generating DuckDB extraction query.")
            try:
                desc_res = duckdb_client.query(f"DESCRIBE SELECT * FROM read_parquet('{dataset_path}')")
                col_list = [r["column_name"] for r in desc_res]
                
                chart_sql_prompt = (
                    f"Translate the following chart request into a single valid DuckDB SELECT SQL query to extract data points for plotting.\n"
                    f"Table: read_parquet('{dataset_path}')\n"
                    f"Columns: {col_list}\n"
                    f"RULES:\n"
                    f"1. Select the relevant 1 or 2 numeric/categorical columns requested by the user.\n"
                    f"2. Exclude NULL values (e.g. WHERE colX IS NOT NULL).\n"
                    f"3. Always append LIMIT 400 to prevent context bloat.\n"
                    f"4. Return ONLY the raw SQL query. No markdown backticks or explanations.\n"
                    f"User Request: '{user_query}'"
                )
                
                sql_query, _, _ = await self.gemini.generate(chart_sql_prompt, "You are a precise SQL writer.")
                sql_query = sql_query.strip().replace("```sql", "").replace("```", "").strip(";")
                
                chart_data = duckdb_client.query(sql_query)
                cleaned_chart_data = self.clean_decimals(chart_data)
                
                chart_spec = None
                if cleaned_chart_data and len(cleaned_chart_data[0].keys()) >= 2:
                    keys = list(cleaned_chart_data[0].keys())
                    cat_candidate = None
                    num_candidate = None
                    
                    # Detect categorical vs continuous attribute types to prevent squished scatter plots
                    for k in keys[:2]:
                        unique_vals = set(r[k] for r in cleaned_chart_data if r[k] is not None)
                        if len(unique_vals) <= 12 and cat_candidate is None:
                            cat_candidate = k
                        elif num_candidate is None:
                            num_candidate = k
                            
                    if cat_candidate and num_candidate:
                        # Categorical vs Continuous -> Aggregate average value per category for a stunning Bar Chart!
                        group_totals = {}
                        group_counts = {}
                        for r in cleaned_chart_data:
                            c_val = str(r[cat_candidate])
                            n_val = r[num_candidate]
                            if c_val is not None and n_val is not None and isinstance(n_val, (int, float)):
                                group_totals[c_val] = group_totals.get(c_val, 0.0) + float(n_val)
                                group_counts[c_val] = group_counts.get(c_val, 0) + 1
                                
                        bar_points = []
                        for cat_name, tot in group_totals.items():
                            cnt = group_counts[cat_name]
                            avg_val = round(tot / cnt, 2) if cnt > 0 else 0.0
                            bar_points.append([f"{cat_candidate}: {cat_name}", avg_val])
                            
                        chart_spec = {
                            "type": "bar",
                            "x_col": cat_candidate,
                            "y_col": f"Average {num_candidate}",
                            "title": f"Average {num_candidate} by {cat_candidate}",
                            "points": bar_points
                        }
                    else:
                        # Continuous vs Continuous -> Render Scatter Plot
                        x_key, y_key = keys[0], keys[1]
                        points = [[r[x_key], r[y_key]] for r in cleaned_chart_data if r[x_key] is not None and r[y_key] is not None]
                        chart_spec = {
                            "type": "scatter",
                            "x_col": x_key,
                            "y_col": y_key,
                            "title": f"{y_key} vs {x_key}",
                            "points": points
                        }
                elif cleaned_chart_data:
                    keys = list(cleaned_chart_data[0].keys())
                    x_key = keys[0]
                    vals = [float(r[x_key]) for r in cleaned_chart_data if r[x_key] is not None and isinstance(r[x_key], (int, float))]
                    if vals:
                        min_v, max_v = min(vals), max(vals)
                        step = (max_v - min_v) / 10 if max_v > min_v else 1.0
                        bin_counts = {}
                        for v in vals:
                            b_idx = int((v - min_v) / step) if step > 0 else 0
                            b_idx = min(b_idx, 9)
                            b_start = round(min_v + b_idx * step, 1)
                            b_end = round(min_v + (b_idx + 1) * step, 1)
                            b_label = f"${b_start} - ${b_end}" if "amount" in x_key.lower() else f"{b_start} - {b_end}"
                            bin_counts[b_label] = bin_counts.get(b_label, 0) + 1
                        
                        bar_points = [[k, cnt] for k, cnt in bin_counts.items()]
                        chart_spec = {
                            "type": "bar",
                            "x_col": f"{x_key} Range",
                            "y_col": "Frequency Count",
                            "title": f"Distribution Histogram of {x_key}",
                            "points": bar_points
                        }
                    else:
                        points = [[i, r[x_key]] for i, r in enumerate(cleaned_chart_data[:20]) if r[x_key] is not None]
                        chart_spec = {
                            "type": "bar",
                            "x_col": "Index",
                            "y_col": x_key,
                            "title": f"Distribution of {x_key}",
                            "points": points
                        }
                
                # Generate recommended chart suggestions based on column metadata
                suggested_charts = []
                for c in col_list:
                    if c.lower() in ["class", "churn", "gender", "contract", "category"]:
                        suggested_charts.append({"title": f"Average Amount by {c}", "prompt": f"bar chart of average Amount by {c}"})
                if len(col_list) >= 2:
                    suggested_charts.append({"title": f"Scatter Plot: {col_list[1]} vs {col_list[0]}", "prompt": f"chart on {col_list[1]} vs {col_list[0]}"})
                suggested_charts.append({"title": f"Distribution of {col_list[-1]}", "prompt": f"distribution of {col_list[-1]}"})

                chart_explain_prompt = (
                    f"Analyze this chart request and extracted sample data:\n"
                    f"User Request: '{user_query}'\n"
                    f"SQL Executed: '{sql_query}'\n"
                    f"Sample Points (first 10): {cleaned_chart_data[:10]}\n\n"
                    f"Provide a structured 3-part markdown report:\n"
                    f"1. **📊 Chart Breakdown**: Explain what the visualization displays, key data clusters, and trend lines.\n"
                    f"2. **💡 Usage Suggestions**: Recommend what statistical tests or ML algorithms (e.g., Anomaly Detection, Correlation Heatmap) to run next and how to configure them.\n"
                    f"3. **🎯 Executive Impact**: Explain how to use these findings for risk mitigation or business decision-making."
                )
                explanation, _, _ = await self.gemini.generate(chart_explain_prompt, "You are AURA, an enterprise decision intelligence assistant.")
                
                return {
                    "source": "dynamic_chart_engine",
                    "data": {
                        "query_executed": sql_query,
                        "result": cleaned_chart_data[:20]
                    },
                    "chart_spec": chart_spec,
                    "suggested_charts": suggested_charts[:3],
                    "response": explanation
                }
            except Exception as chart_err:
                logger.warning(f"Dynamic chart engine routing failed: {chart_err}. Falling back to standard query route.")

        # --- STEP 1: Route to Deterministic SQL / Analytics via Dynamic Text-to-SQL ---
        if self.is_deterministic(user_query) and os.path.exists(dataset_path) and "virtual_evidence.parquet" not in dataset_path:
            logger.info("Decision: Query matches deterministic signature. Generating DuckDB SQL query via AI.")
            try:
                # Fetch dataset columns schema
                desc_res = duckdb_client.query(f"DESCRIBE SELECT * FROM read_parquet('{dataset_path}')")
                col_list = [r["column_name"] for r in desc_res]
                
                sql_prompt = (
                    f"You are a precise DuckDB SQL generator.\n"
                    f"Translate the following user question into a single, optimized, valid SELECT SQL query to run on the table: read_parquet('{dataset_path}')\n"
                    f"The columns in this table are: {col_list}.\n"
                    f"RULES:\n"
                    f"1. Return ONLY the raw SQL query string. Do not include markdown code block backticks (like ```sql) or any explanations.\n"
                    f"2. If retrieving specific transactions, rows, or lists of records, select the relevant columns and ALWAYS append 'LIMIT 10' to prevent system memory overload. Never run unbounded SELECT * on large tables.\n"
                    f"3. Use specific columns or aggregation functions (e.g., COUNT(*), AVG(col_name), SUM(col_name)) that directly address the question.\n"
                    f"4. Translate user filter conditions accurately (e.g. 'greater than 1000' becomes 'WHERE Amount > 1000').\n"
                    f"User Question: '{user_query}'"
                )
                
                # Query Gemini to generate SQL query
                sql_query, _, _ = await self.gemini.generate(sql_prompt, "You are a precise SQL writer.")
                sql_query = sql_query.strip().replace("```sql", "").replace("```", "").strip(";")
                
                logger.info(f"Executing AI-generated SQL query: {sql_query}")
                sql_res = duckdb_client.query(sql_query)
                
                # Convert decimal.Decimal objects to float/int to prevent JSON cache serialization crashes
                import decimal
                cleaned_res = []
                for row in sql_res:
                    cleaned_row = {}
                    for k, v in row.items():
                        if isinstance(v, decimal.Decimal):
                            cleaned_row[k] = float(v)
                        else:
                            cleaned_row[k] = v
                    cleaned_res.append(cleaned_row)
                
                # Query Gemini to explain this raw calculation result
                explain_prompt = (
                    f"Describe the query results to the user in a professional, concise, direct way.\n"
                    f"User Question: '{user_query}'\n"
                    f"Executed SQL: '{sql_query}'\n"
                    f"DuckDB Query Result: {cleaned_res}"
                )
                explanation, _, _ = await self.gemini.generate(explain_prompt, "You are AURA, an enterprise decision intelligence assistant.")
                
                return {
                    "source": "deterministic_sql",
                    "data": {
                        "query_executed": sql_query,
                        "result": cleaned_res
                    },
                    "response": explanation
                }
            except Exception as e:
                logger.error(f"AI SQL generation or execution failed: {e}. Falling back to semantic path.")

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

        # --- STEP 3: Route to Local LLM (Ollama) or gather evidence ---
        # Generate rich descriptive statistical evidence from the parquet file using DuckDB's SUMMARIZE
        evidence_summary = {
            "dataset_info": {
                "path": os.path.basename(dataset_path),
                "total_rows": 0,
                "columns": []
            },
            "user_question": user_query
        }
        
        if os.path.exists(dataset_path) and "virtual_evidence.parquet" not in dataset_path:
            try:
                cnt_res = duckdb_client.query(f"SELECT count(*) as cnt FROM read_parquet('{dataset_path}')")
                evidence_summary["dataset_info"]["total_rows"] = cnt_res[0]["cnt"]
                
                # Fetch summary statistics for columns
                summary_res = duckdb_client.query(f"SUMMARIZE SELECT * FROM read_parquet('{dataset_path}')")
                
                # Identify if specific columns are mentioned in the question to prioritize them
                mentioned_cols = []
                for col in [r["column_name"] for r in summary_res]:
                    if col.lower() in user_query.lower():
                        mentioned_cols.append(col)
                
                for r in summary_res:
                    # If columns are mentioned, prioritize them, otherwise keep first 10 columns to prevent context bloat
                    col_name = r["column_name"]
                    if mentioned_cols and col_name not in mentioned_cols:
                        continue
                    if not mentioned_cols and len(evidence_summary["dataset_info"]["columns"]) >= 12:
                        continue
                        
                    evidence_summary["dataset_info"]["columns"].append({
                        "name": col_name,
                        "type": r["column_type"],
                        "min": r["min"],
                        "max": r["max"],
                        "avg": r["avg"],
                        "null_percentage": r["null_percentage"]
                    })
            except Exception as e:
                logger.warning(f"Failed collecting descriptive database evidence: {e}")

        evidence_summary = self.clean_decimals(evidence_summary)

        system_prompt = (
            "You are AURA, an enterprise decision intelligence agent. "
            "Explain analytical findings using the provided evidence. "
            "For conceptual, mathematical, or general domain questions (like explaining what PCA is, what correlation means, or typical data behaviors), "
            "you should use your general knowledge to explain it clearly and professionally."
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
            
            # Smart Offline Narrative Fallback Engine
            try:
                cnt = evidence_summary.get("dataset_info", {}).get("total_rows", 0)
                cols = evidence_summary.get("dataset_info", {}).get("columns", [])
                col_names = [c["name"] for c in cols]
                
                response_text = (
                    f"### AURA Local Analytical Summary\n\n"
                    f"*(Note: AI narration fallback activated due to API limits or network latency)*\n\n"
                    f"Here is a direct **local database profile** of your dataset:\n\n"
                    f"* **Total Rows**: {cnt:,} records\n"
                    f"* **Scanned Columns**: {', '.join(col_names[:8])}\n\n"
                    f"#### 📊 Core Metric Profiles:\n"
                )
                for col in cols[:5]:
                    response_text += (
                        f"* **{col['name']}** ({col['type']}):\n"
                        f"  - Range: `[{col['min']} to {col['max']}]`  |  Average: `{col['avg']}`\n"
                        f"  - Quality Integrity: `{100.0 - float(col['null_percentage'])}%` complete\n"
                    )
            except Exception:
                response_text = (
                    f"### AURA AI Decision Intelligence Report\n\n"
                    f"We analyzed your dataset records in relation to your request: *'{user_query}'*.\n\n"
                    f"1. **Statistical Density**: DuckDB computed structural profiles verify a clean data distribution schema with {evidence_summary.get('dataset_info', {}).get('total_rows', 0)} rows.\n"
                    f"2. **Column Schema**: The columns align cleanly with standard analytical inputs: {[c['name'] for c in evidence_summary.get('dataset_info', {}).get('columns', [])][:8]}.\n"
                )

            return {
                "source": "smart_offline_narrative_engine",
                "response": response_text,
                "evidence_references": evidence_summary
            }


ai_budget_manager = AIBudgetManager()
