#!/usr/bin/env python3
"""
vLLM Test Runner - Prometheus-Based Metrics

Simplified version that uses Prometheus for ALL metric computations.
No manual delta calculations - everything derived via PromQL queries.

Requires:
- Prometheus running at localhost:9090
- Prometheus scraping vLLM at localhost:8000/metrics
"""

import multiprocessing
import subprocess
import requests
import time
import json
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict, field

# Configuration
VLLM_CONFIG = {
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "host": "0.0.0.0",
    "port": 8000,
    "trust_remote_code": True,
    "enable_auto_tool_choice": True,
    "tool_call_parser": "hermes",
    "enable_prefix_cache": True,
    "context_window": 32768,
}

RESULTS_DIR = Path("../ciso_traces")
VLLM_URL = f"http://localhost:{VLLM_CONFIG['port']}"
PROMETHEUS_URL = "http://localhost:9090"


@dataclass
class TestMetrics:
    """All metrics derived from Prometheus queries."""
    test_id: str
    test_name: str
    start_time: str
    end_time: str
    duration_seconds: float
    
    # Token counts (from increase())
    prompt_tokens: Optional[int] = None
    generation_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Request counts
    num_requests: Optional[int] = None
    
    # Latency metrics - averages (from rate(sum)/rate(count))
    avg_ttft_seconds: Optional[float] = None
    avg_e2e_latency_seconds: Optional[float] = None
    avg_tpot_seconds: Optional[float] = None
    avg_prefill_seconds: Optional[float] = None
    avg_decode_seconds: Optional[float] = None
    
    # Throughput
    tokens_per_second: Optional[float] = None
    
    # Gauge metrics - max values (from max_over_time())
    max_kv_cache_usage_perc: Optional[float] = None
    max_requests_running: Optional[int] = None
    max_requests_waiting: Optional[int] = None
    
    # Prefix cache
    prefix_cache_hit_rate_perc: Optional[float] = None


def _run_vllm_server(config: dict):
    """Run vLLM server using the CLI entry point."""
    import sys
    sys.argv = [
        "vllm", "serve", config["model"],
        "--host", config["host"],
        "--port", str(config["port"]),
        "--trust-remote-code",
        "--enable-auto-tool-choice",
        "--tool-call-parser", config["tool_call_parser"],
    ]
    try:
        from vllm.entrypoints.cli.main import main as vllm_main
    except ImportError:
        from vllm.scripts import main as vllm_main
    vllm_main()


class VLLMServer:
    """Manages vLLM server lifecycle."""
    
    def __init__(self, config: dict = None):
        self.config = config or VLLM_CONFIG
        self.process: Optional[multiprocessing.Process] = None
    
    def start(self) -> None:
        print("[INFO] Starting vLLM server...")
        ctx = multiprocessing.get_context("spawn")
        self.process = ctx.Process(target=_run_vllm_server, args=(self.config,), daemon=False)
        self.process.start()
        print(f"[INFO] vLLM started with PID: {self.process.pid}")
    
    def wait_until_ready(self, timeout: int = 300) -> bool:
        print("[INFO] Waiting for vLLM to be ready...")
        start = time.time()
        while time.time() - start < timeout:
            if self.process and not self.process.is_alive():
                print("\n[ERROR] vLLM process died")
                return False
            try:
                if requests.get(f"{VLLM_URL}/health", timeout=2).status_code == 200:
                    print("\n[INFO] vLLM is ready")
                    return True
            except requests.RequestException:
                print(".", end="", flush=True)
            time.sleep(2)
        print(f"\n[ERROR] vLLM timeout after {timeout}s")
        return False
    
    def stop(self) -> None:
        print("[INFO] Stopping vLLM server...")
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=10)
            if self.process.is_alive():
                self.process.kill()
        self.process = None
        time.sleep(3)
    
    def __enter__(self):
        self.start()
        if not self.wait_until_ready():
            self.stop()
            raise RuntimeError("vLLM failed to start")
        return self
    
    def __exit__(self, *args):
        self.stop()


class PrometheusMetrics:
    """Query all metrics from Prometheus - no local calculations."""
    
    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self.prometheus_url = prometheus_url
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def start(self) -> None:
        """Record start time."""
        self.start_time = datetime.now(timezone.utc)
        print(f"[INFO] Metrics collection started at {self.start_time.isoformat()}")
    
    def stop(self) -> None:
        """Record end time."""
        self.end_time = datetime.now(timezone.utc)
        print(f"[INFO] Metrics collection ended at {self.end_time.isoformat()}")
    
    @property
    def duration(self) -> float:
        """Duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0
    
    def _query_instant(self, query: str) -> Optional[float]:
        """Execute instant query at end_time."""
        try:
            resp = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query, "time": self.end_time.timestamp()},
                timeout=10,
            )
            data = resp.json()
            if data.get("status") == "success" and data["data"]["result"]:
                return float(data["data"]["result"][0]["value"][1])
        except Exception as e:
            print(f"[WARN] Query failed: {query[:50]}... - {e}")
        return None
    
    def _query_range_max(self, metric: str) -> Optional[float]:
        """Query max value over the test time range."""
        try:
            resp = requests.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params={
                    "query": metric,
                    "start": self.start_time.timestamp(),
                    "end": self.end_time.timestamp(),
                    "step": "5s",
                },
                timeout=10,
            )
            data = resp.json()
            if data.get("status") == "success" and data["data"]["result"]:
                values = [float(v[1]) for v in data["data"]["result"][0]["values"]]
                return max(values) if values else None
        except Exception as e:
            print(f"[WARN] Range query failed: {metric} - {e}")
        return None
    
    def collect(self) -> Dict[str, Any]:
        """Collect all metrics using Prometheus queries."""
        d = int(self.duration) + 10  # Add buffer for scrape interval
        
        metrics = {}
        
        # === Counter metrics (use increase()) ===
        metrics["prompt_tokens"] = self._to_int(self._query_instant(
            f"increase(vllm:prompt_tokens_total[{d}s])"
        ))
        metrics["generation_tokens"] = self._to_int(self._query_instant(
            f"increase(vllm:generation_tokens_total[{d}s])"
        ))
        metrics["num_requests"] = self._to_int(self._query_instant(
            f"increase(vllm:request_success_total[{d}s])"
        ))
        
        # Total tokens
        if metrics["prompt_tokens"] and metrics["generation_tokens"]:
            metrics["total_tokens"] = metrics["prompt_tokens"] + metrics["generation_tokens"]
        
        # === Latency averages (rate(sum)/rate(count)) ===
        metrics["avg_ttft_seconds"] = self._query_instant(
            f"rate(vllm:time_to_first_token_seconds_sum[{d}s]) / rate(vllm:time_to_first_token_seconds_count[{d}s])"
        )
        metrics["avg_e2e_latency_seconds"] = self._query_instant(
            f"rate(vllm:e2e_request_latency_seconds_sum[{d}s]) / rate(vllm:e2e_request_latency_seconds_count[{d}s])"
        )
        metrics["avg_tpot_seconds"] = self._query_instant(
            f"rate(vllm:inter_token_latency_seconds_sum[{d}s]) / rate(vllm:inter_token_latency_seconds_count[{d}s])"
        )
        metrics["avg_prefill_seconds"] = self._query_instant(
            f"rate(vllm:request_prefill_time_seconds_sum[{d}s]) / rate(vllm:request_prefill_time_seconds_count[{d}s])"
        )
        metrics["avg_decode_seconds"] = self._query_instant(
            f"rate(vllm:request_decode_time_seconds_sum[{d}s]) / rate(vllm:request_decode_time_seconds_count[{d}s])"
        )
        
        # Round latencies
        for key in ["avg_ttft_seconds", "avg_e2e_latency_seconds", "avg_tpot_seconds", 
                    "avg_prefill_seconds", "avg_decode_seconds"]:
            if metrics[key] is not None:
                metrics[key] = round(metrics[key], 6)
        
        # === Gauge metrics (use max_over_time via query_range) ===
        kv_cache = self._query_range_max("vllm:kv_cache_usage_perc")
        metrics["max_kv_cache_usage_perc"] = round(kv_cache * 100, 2) if kv_cache else None
        
        metrics["max_requests_running"] = self._to_int(
            self._query_range_max("vllm:num_requests_running")
        )
        metrics["max_requests_waiting"] = self._to_int(
            self._query_range_max("vllm:num_requests_waiting")
        )
        
        # === Prefix cache hit rate ===
        queries = self._query_instant(f"increase(vllm:prefix_cache_queries_total[{d}s])")
        hits = self._query_instant(f"increase(vllm:prefix_cache_hits_total[{d}s])")
        if queries and queries > 0:
            metrics["prefix_cache_hit_rate_perc"] = round((hits or 0) / queries * 100, 2)
        else:
            metrics["prefix_cache_hit_rate_perc"] = None
        
        # === Throughput ===
        if metrics["total_tokens"] and self.duration > 0:
            metrics["tokens_per_second"] = round(metrics["total_tokens"] / self.duration, 2)
        else:
            metrics["tokens_per_second"] = None
        
        return metrics
    
    @staticmethod
    def _to_int(value: Optional[float]) -> Optional[int]:
        return int(round(value)) if value is not None else None


def run_test_script(test_id: str, test_name: str, log_file: Path) -> int:
    """Run test script with output to terminal and log file."""
    script_path = f"./ciso_scripts/scripts_{test_id}.sh"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[INFO] Running: {script_path}")
    print(f"[INFO] Logging to: {log_file}\n")
    
    result = subprocess.run(
        f"bash {script_path} 2>&1 | tee {log_file}",
        shell=True, executable="/bin/bash",
    )
    return result.returncode


def run_single_test(test_id: str, test_name: str) -> TestMetrics:
    """Run a single test with fresh vLLM and Prometheus-based metrics."""
    print("=" * 60)
    print(f"[TEST] {test_name} (ID: {test_id})")
    print("=" * 60)
    
    with VLLMServer():
        prom = PrometheusMetrics()
        prom.start()
        
        run_test_script(test_id, test_name, RESULTS_DIR / test_name / "run.log")
        
        prom.stop()
        metrics = prom.collect()
        
        return TestMetrics(
            test_id=test_id,
            test_name=test_name,
            start_time=prom.start_time.isoformat(),
            end_time=prom.end_time.isoformat(),
            duration_seconds=round(prom.duration, 3),
            **metrics,
        )


def save_metrics(metrics: TestMetrics, test_name : str) -> Path:
    """Save metrics to JSON file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = RESULTS_DIR / test_name / f"vllm_metrics_{timestamp}.json"
    
    with open(filepath, "w") as f:
        json.dump(asdict(metrics), f, indent=2)
    
    print(f"[INFO] Metrics saved to: {filepath}")
    return filepath


def print_summary(m: TestMetrics):
    """Print test results summary."""
    print(f"\n{'='*60}")
    print(f"[RESULTS] {m.test_name}")
    print(f"{'='*60}")
    print(f"Duration:\t{m.duration_seconds}s")
    print(f"Requests:\t{m.num_requests}")
    print(f"Tokens:\t{m.prompt_tokens} prompt + {m.generation_tokens} gen = {m.total_tokens}")
    print(f"Throughput:\t{m.tokens_per_second} tokens/sec")
    print(f"Avg TTFT:\t{m.avg_ttft_seconds}s")
    print(f"Avg E2E Latency/request:\t{m.avg_e2e_latency_seconds}s")
    print(f"Avg Time/Token:\t{m.avg_tpot_seconds}s")
    print(f"Max KV Cache:\t{m.max_kv_cache_usage_perc}%")
    print(f"Prefix Cache Hit Rate:\t{m.prefix_cache_hit_rate_perc}%")
    print()


def main():
    """Main entry point."""
    tests = {
        "1": "1.gen-cis-b-k8s-kyverno",
        "2": "2.gen-cis-b-k8s-kubectl-opa",
        "4": "4.upd-cis-b-k8s-kyverno",
    }
    
    def cleanup(signum, frame):
        print("\n[INFO] Interrupted - exiting...")
        exit(1)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    for test_id, test_name in tests.items():
        try:
            metrics = run_single_test(test_id, test_name)
            save_metrics(metrics, test_name)
            print_summary(metrics)
        except Exception as e:
            print(f"[ERROR] Test {test_name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("[DONE] All tests completed")


if __name__ == "__main__":
    main()
