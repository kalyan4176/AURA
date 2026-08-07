import psutil
import time
import threading
from typing import Dict, Any

class SystemMonitor:
    """Enterprise Systems Observability Engine.

    Tracks containerized CPU/Memory metrics and cache performance indicators
    without relying on external daemon configurations.
    """
    
    # Thread-safe global metric counters
    _lock = threading.Lock()
    _api_request_count = 0
    _api_total_latency = 0.0
    
    _cache_hits = 0
    _cache_misses = 0

    @classmethod
    def record_api_call(cls, duration: float):
        with cls._lock:
            cls._api_request_count += 1
            cls._api_total_latency += duration

    @classmethod
    def record_cache_hit(cls):
        with cls._lock:
            cls._cache_hits += 1

    @classmethod
    def record_cache_miss(cls):
        with cls._lock:
            cls._cache_misses += 1

    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        """Fetch real-time host resource levels and engine diagnostics."""
        cpu = 0.0
        memory = 0.0
        disk = 0.0
        
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem_info = psutil.virtual_memory()
            memory = mem_info.percent
            disk = psutil.disk_usage('.').percent
        except Exception:
            # Fallback if psutil fails in highly restricted containers
            pass

        with cls._lock:
            avg_latency = (
                cls._api_total_latency / cls._api_request_count 
                if cls._api_request_count > 0 else 0.0
            )
            cache_total = cls._cache_hits + cls._cache_misses
            cache_hit_ratio = (
                cls._cache_hits / cache_total 
                if cache_total > 0 else 1.0
            )

            return {
                "system": {
                    "cpu_utilization_percent": cpu,
                    "memory_utilization_percent": memory,
                    "disk_occupancy_percent": disk,
                },
                "api": {
                    "total_requests": cls._api_request_count,
                    "average_response_latency_seconds": round(avg_latency, 4),
                },
                "cache": {
                    "hit_count": cls._cache_hits,
                    "miss_count": cls._cache_misses,
                    "hit_ratio": round(cache_hit_ratio, 4),
                }
            }


# Global systems monitor reference
system_monitor = SystemMonitor()
