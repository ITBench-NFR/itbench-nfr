# NFR Benchmarking for ITBench SRE and CISO Agents

Basic setup: Follow instructions on (https://github.com/ITBench-NFR/ITBench-SRE-Agent)[SRE], (https://github.com/ITBench-NFR/ITBench-CISO-CAA-Agent)[CISO], and (https://github.com/itbench-hub/ITBench-Scenarios)[Test Scenarios] setup.
  
### CISO Sandbox Evaluation

`ciso_vllm_benchmark.py` contains scripts for running end-to-end sandbox evaluation of CISO agents on a locally hosted vLLM instance.

Add an .env file with
```
# add these only when hosting via vLLM
LLM_BASE_URL="http://localhost:<PORT>/v1"
VLLM_PROMETHEUS_URL = "http://localhost:<PROMETHEUS PORT>"
OPENAI_MODEL_NAME="Qwen/Qwen2.5-14B-Instruct-AWQ" or 

# add these when using google API
GOOGLE_API_KEY= ...
LLM_MODEL_NAME="gemini-pro-latest"

# langfuse tracing info
LANGTRACE_API_KEY = ...
LANGFUSE_SECRET_KEY = ...
LANGFUSE_PUBLIC_KEY = ...
LANGFUSE_BASE_URL = ...
```
