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

## 3. Results

## a. SRE: React vs Plan&Execute

### NFR Metrics for Select SRE Scenarios using Gemini 2.5 Pro

### Incident 1

| Metric              | SRE (Plan&Execute) | SRE (ReAct) | Mini-SWE |
|:--------------------|-------------------:|------------:|---------:|
| Planning Overhead   | 80.71%            | 92.83%     | 90.40%  |
| E2E Latency (s)     | 1135              | 13126      | 218     |
| P/C Ratio           | 42.80             | 9.11       | 37.00   |
| LLM Calls           | 11                | 21         | 10      |

### Incident 16

| Metric              | SRE (Plan&Execute) | SRE (ReAct) | Mini-SWE |
|:--------------------|-------------------:|------------:|---------:|
| Planning Overhead   | 85.45%            | 82.75%     | 82.20%  |
| E2E Latency (s)     | 362               | 401        | 161     |
| P/C Ratio           | 9.775             | 0.96       | 4.31    |
| LLM Calls           | 21                | 16         | 10      |

### Incident 23

| Metric              | SRE (Plan&Execute) | SRE (ReAct) | Mini-SWE |
|:--------------------|-------------------:|------------:|---------:|
| Planning Overhead   | 83.33%            | 86.48%     | 69.31%  |
| E2E Latency (s)     | 255               | 49         | 136     |
| P/C Ratio           | 15.28             | 15.04      | 3.53    |
| LLM Calls           | 11                | 6          | 4       |

### Incident 30

| Metric              | SRE (Plan&Execute) | SRE (ReAct) | Mini-SWE |
|:--------------------|-------------------:|------------:|---------:|
| Planning Overhead   | 80.74%            | 87.95%     | 91.82%  |
| E2E Latency (s)     | 304               | 793        | 283     |
| P/C Ratio           | 6.14              | 2.19       | 81.46   |
| LLM Calls           | 16                | 37         | 10      |

### Incident 102

| Metric              | SRE (Plan&Execute) | SRE (ReAct) | Mini-SWE |
|:--------------------|-------------------:|------------:|---------:|
| Planning Overhead   | 81.92%            | 81.69%     | 67.69%  |
| E2E Latency (s)     | 136               | 358        | 296     |
| P/C Ratio           | 75.53             | 4.68       | 2.62    |
| LLM Calls           | 3                 | 14         | 7       |

**Note:** P/C Ratio = Prompt Completion Ratio

### b. CISO: React vs Plan&Execute

#### Gemini-2.5-Pro

| Metric                | 1.gen-kyverno |       | 2.gen-kubectlopa |       | 4.upd-kyverno |       |
|:----------------------|--------------:|------:|-----------------:|------:|-------------:|------:|
|                       | **R**         | **P** | **R**            | **P** | **R**        | **P** |
| E2E Latency (s)       | 71.8          | 65.5  | 61.3             | 75.2  | 243.0        | 256.9 |
| LLM Calls             | 8             | 9     | 7                | 8     | 28           | 28    |
| Input Tok (K)         | 13.1          | 19.2  | 13.2             | 19.2  | 181.4        | 134.9 |
| Output Tok (K)        | 6.5           | 5.3   | 5.2              | 7.4   | 9.3          | 18.5  |
| Reasoning Tok (K)     | 3.2           | 2.0   | 2.1              | 4.2   | 0.6          | 6.0   |
| Plan Overhead (%)     | 49.1          | 38.3  | 40.8             | 56.9  | 6.0          | 32.4  |
| P/C Ratio             | 2.02          | 3.65  | 2.56             | 2.61  | 19.51        | 7.29  |
| Tool Usages           | 3             | 5     | 3                | 3     | 18           | 13    |
| Tool Err (%)          | 0             | 0     | 0                | 25    | 10           | 0     |
| Throughput (t/s)      | 90.0          | 80.2  | 84.2             | 98.0  | 38.3         | 72.0  |
| Avg LLM time (s)      | 8.9           | 7.2   | 8.7              | 9.3   | 8.6          | 9.0   |
| Avg TRTT (s)          | 4.1           | 4.0   | 5.8              | 2.9   | 6.8          | 6.1   |

#### Qwen2.5-14B-Instruct-AWQ

| Metric                      | 1.gen-kyverno |       | 2.gen-kubectlopa |       | 4.upd-kyverno |       |
|:----------------------------|--------------:|------:|-----------------:|------:|-------------:|------:|
|                             | **R**         | **P** | **R**            | **P** | **R**        | **P** |
| E2E Latency (s)             | 193.2         | 208.3 | 26.5             | 71.6  | 81.6         | 75.5  |
| LLM Calls                   | 34            | 34    | 7                | 10    | 11           | 7     |
| Input Tok (K)               | 111.1         | 115.5 | 10.5             | 18.3  | 15.8         | 9.4   |
| Output Tok (K)              | 4.8           | 5.2   | 0.6              | 1.8   | 2.1          | 1.9   |
| Reasoning Tok (K)         | 0             | 0     | 0                | 0     | 0            | 0     |
| Plan Overhead (%)         | 0             | 0     | 0                | 0     | 0            | 0     |
| P/C Ratio                   | 22.90         | 22.04 | 16.27            | 10.17 | 7.53         | 4.88  |
| Tool Usages                 | 20            | 20    | 6                | 9     | 6            | 3     |
| Tool Err (%)                | 0             | 0     | 25               | 40    | 0            | 0     |
| Throughput (t/s)            | 25.1          | 25.2  | 24.4             | 25.1  | 25.7         | 25.5  |
| Avg LLM time (s)            | 5.6           | 6.1   | 3.7              | 7.1   | 7.4          | 10.7  |
| Avg TRTT (s)                | 4.9           | 4.5   | 0.9              | 1.0   | 5.9          | 7.9   |
| KV-Cache Util %            | 19.76         | 19.57 | 4.2              | 5.25  | 8.21         | 6.6   |
| Prefix-Cache Hit %         | 91.47         | 90.32 | 62.96            | 65.18 | 68.76        | 41.92 |

**Notes:**  
- R = ReAct, P = Plan&Execute 
---

## 4. Reproducibility Instructions

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

#### 5. NFR evaluation for CISO
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

## 6. Notes
- Benchmarking outputs are obtained in `../ciso_traces`.
