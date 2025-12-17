# NFR Benchmarking for ITBench SRE and CISO Agents

Basic setup: Follow instructions on [SRE](https://github.com/ITBench-NFR/ITBench-SRE-Agent), [CISO](https://github.com/ITBench-NFR/ITBench-CISO-CAA-Agent), and [ITBench-Scenarios](https://github.com/itbench-hub/ITBench-Scenarios) to install system dependencies, containers and instruction to run agents and scenario injections.

### Prometheus setup for vLLM metric telemetry

Follow [vLLM Prometheus and Grafa](https://docs.vllm.ai/en/v0.7.2/getting_started/examples/prometheus_grafana.html) setup to create a locally running instance of Prometheus to extract time-series data from vLLM.
Upon launching the instance, prometheus will be available at port 9090, and assumes vLLM instance is available at `http://localhost:8000`

### NFR evaluation

1. Create a .env file in the current directory, with
Langfuse tracing info
```
LANGTRACE_API_KEY = ...
LANGFUSE_SECRET_KEY = ...
LANGFUSE_PUBLIC_KEY = ...
LANGFUSE_BASE_URL = ...
```

 When hosting via vLLM,
```
LLM_BASE_URL="http://localhost:8000/v1"
VLLM_PROMETHEUS_URL = "http://localhost:9090"
OPENAI_MODEL_NAME="Qwen/Qwen2.5-14B-Instruct-AWQ"
```

When using LLM API from Google, OpenAI, etc
```
LLM_API_KEY= ...
LLM_MODEL_NAME= ...
```

### CISO Sandbox Evaluation on locally hosted vLLM
`ciso_vllm_benchmark.py` contains scripts for running end-to-end sandbox evaluation of CISO agents on a locally hosted vLLM instance.
Outputs are directed to `../ciso_traces` for each scenario.

### CISO Sandbox Evaluation on Remote LLM
Run each scenario via `bash ciso_scripts/scripts_{scenario_id}.sh`. Outputs are directed to `../ciso_traces` for each scenario.

### SRE Evaluation
To evaluate SRE on all scenarios from [ITBench-Scenarios](https://github.com/itbench-hub/ITBench-Scenarios), run `python sre_benchmark_runner.py`
Results are stored in `../benchmark_results`.

### Calculating NFRs from scenario runs
To calculate NFRs from each of the aforementioned tests, run 
```
python analyze_traces.py <path_to_langfuse_dump>
```
