# Non-Functional Requirements (NFR) Benchmarking for IT Automation Agents


**Members**:
  - Arjun Vaidya (av3315@columbia.edu)
  - Ayush Bhauwala (ab6106@columbia.edu)
  - Gautam Agarwal (ga2726@columbia.edu)
  - Rishabh Jain (rj2790@columbia.edu)
  - Tanmay Agrawal (ta2832@columbia.edu)
---

## 1. Problem Statement
AI agents are increasingly being deployed in IT automation domains such as SRE, CISO operations, and FinOps, yet their evaluation remains dominated by functional success metrics that overlook practical deployment and performance risks. Agentic systems exhibit non-deterministic reasoning, multi-step tool use, compounding errors and brittle recovery mechanisms, and sometimes succeed through unintended paths, revealing a critical gap between benchmark performance and production readiness. We first synthesize findings from software engineering, ML system quality models, and recent agentic frameworks to establish a unified understanding of non-functional requirements (NFRs) for AI agents. We extend ITBench with an NFR-aware evaluation framework, providing a comprehensive insights into NFR characteristics of ITBench SRE and CISO Agents.

---

## 2. Description
The itbench-hub repositories implement two specialized AI agents designed for IT automation: the SRE Agent and the CISO Agent.

### SRE Agent
Repository: [ITBench-NFR/ITBench-SRE-Agent](https://github.com/ITBench-NFR/ITBench-SRE-Agent)

SRE Agent automates incident response in Kubernetes and OpenShift environments. It is designed to diagnose complex system failures, trace root causes, and implement remediation strategies for real-world incidents (e.g., high error rates, service degradation).

Architecture:

1. Framework: Built on CrewAI, enabling a multi-agent orchestration approach.
2. Integration: Connects directly to observability stacks like Prometheus, Jaeger, and Clickhouse to gather logs, metrics, and traces.
3. Execution: Runs in a containerized environment (Docker) to ensure safety and prevent harmful commands from affecting the host system.
4. Tracing: We inject langfuse stubs to extract traces for NFR evaluation

LLM Support: Compatible with WatsonX, Azure OpenAI, and OpenAI models.

### CISO Agents
Repository: [ITBench-NFR/ITBench-CISO-CAA-Agent](https://github.com/ITBench-NFR/ITBench-CISO-CAA-Agent)

CISO Agents automate Compliance Assessment (CAA). It translates natural language goals into technical policies (e.g., Kyverno, OPA Rego), deploys them to clusters, collects evidence, and verifies compliance posture. It can also integrate with GitOps workflows.

Architecture:

1. Framework: Built using a combination of CrewAI and LangGraph for agent orchestration and state management.
2. Workflow: Takes a natural language "goal text" and a workspace (kubeconfig/inventory) as input to autonomously generate and apply policies.
3. Execution: Containerized (Docker/Podman) for portable and isolated execution.
4. Tracing: We inject langfuse stubs to extract traces for NFR evaluation

LLM Support: Works with any OpenAI-compatible LLM service (tested with WatsonX, OpenAI, Azure). Support was added for Google Gemini and locally hosted vLLM models for this work.

---

## 3. Reproducibility Instructions

### A. Requirements

1. Basic setup: Follow instructions on [ITBench-NFR/ITBench-SRE-Agent](https://github.com/ITBench-NFR/ITBench-SRE-Agent), [ITBench-NFR/ITBench-CISO-CAA-Agent](https://github.com/ITBench-NFR/ITBench-CISO-CAA-Agent), and [itbench-hub/ITBench-Scenarios](https://github.com/itbench-hub/ITBench-Scenarios) to install system dependencies, containers and instruction to run agents and scenario injections. 

    NOTE: These repositories are forks from [ITBench](https://github.com/itbench-hub). Ensure installation of our modified versions [ITBench-NFR](https://github.com/ITBench-NFR) linked above.

2. Prometheus setup for vLLM metric telemetry

    Follow [vLLM Prometheus and Grafa](https://docs.vllm.ai/en/v0.7.2/getting_started/examples/prometheus_grafana.html) setup to create a locally running instance of Prometheus to extract time-series data from vLLM.
    Upon launching the instance, prometheus will be available at port 9090, and assumes vLLM instance is available at `http://localhost:8000`

3. 
    Create a .env file in the current directory, with
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

---

<!-- B. Wandb Dashboard

View training and evaluation metrics here: Wandb Dashboard Link
(Replace with actual link)

--- -->

### B. Benchmarking Agents

### CISO
#### 1. CISO Sandbox Evaluation on locally hosted vLLM
`ciso_vllm_benchmark.py` contains scripts for running end-to-end sandbox evaluation of CISO agents on a locally hosted vLLM instance.
Langfuse traces are directed to `../ciso_traces/<scenario_name>/observations_dump.json`, and vllm metrics are exported to `../ciso_traces/<scenario_name>/vllm_metrics_<timestamp>.json` for each scenario.

#### 2. CISO Sandbox Evaluation on Remote LLM
Run each scenario via `bash ciso_scripts/scripts_{scenario_id}.sh`. Langfuse traces are directed to `../ciso_traces/<scenario_name>/observations_dump.json` for the executed scenario.

#### 3. CISO Sandbox Evaluation for Streaming APIs
Run each scenario via `bash ciso_scripts/scripts_{scenario_id}_streaming.sh`. Langfuse traces are directed to `../ciso_traces/<scenario_name>_streaming/observations_dump.json` for the executed scenario and the streaming metrics are directed to `../streaming_metrics.json`.

#### 4. NFR evaluation for CISO
Run `bash ciso_analyze_all_traces.sh` to process all exported traces in `../ciso_traces`. NFRs are obtained in `../ciso_traces/<scenario_name>/analysis.json`.

### SRE Evaluation
1. Place .env file in `ITBench-SRE-Agent`.
2. To evaluate SRE on all scenarios from [ITBench-Scenarios](https://github.com/itbench-hub/ITBench-Scenarios), run `python sre_benchmark_runner.py`
Results are stored in `../benchmark_results`.

#### Calculating NFRs from scenario runs
To calculate NFRs from each of the aforementioned tests, run 
```
python analyze_traces.py <path_to_langfuse_dump>
```

---

## 5. Notes
- Benchmarking outputs are obtained in `../ciso_traces`.
