import json
import os
import sys
import math
import pandas as pd
from collections import defaultdict
from datetime import datetime
import re

# Context window size for Gemini 2.5 Pro
CONTEXT_WINDOW_SIZE = 1000000


def load_and_print_observations(json_path):
    """
    Loads observations from a JSON file and prints them in a readable format using pandas.
    """
    if not os.path.exists(json_path):
        print(f"Error: File not found at {json_path}")
        return

    print(f"Loading observations from: {json_path}")
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    if not data:
        print("No data found in JSON file.")
        return

    observations = {observation['id']: observation for observation in data}
    repeated_tool_calls = defaultdict(dict)

    total_output = 0
    total_reasoning = 0
    total_llm_calls = 0
    total_tool_usages = 0
    repeated_tool_usages = 0
    
    # Track per-LLM-call metrics for context window utilization and throughput
    context_window_utilizations = []
    total_llm_latency_ms = 0
    
    # Track per-tool usages for individual reuse rates
    per_tool_usages = defaultdict(int)
    per_tool_repeated = defaultdict(int)

    for obs_id, observation in observations.items():
        # Count tool usages
        if observation.get('type') == 'TOOL':
            total_tool_usages += 1
            # Extract tool name from the observation
            tool_name = observation.get('name', '').replace('._use', '')
            if not tool_name:
                metadata = observation.get('metadata', {})
                attributes = metadata.get('attributes', {})
                tool_name = attributes.get('tool.name', 'Unknown')
            per_tool_usages[tool_name] += 1
        
        if observation['name'] == 'Tool Repeated Usage':
            repeated_tool_usages += 1
            repeated_tool_name = observation['metadata']['attributes']['tool_name']
            per_tool_repeated[repeated_tool_name] += 1
            parent_observation = observations[observation['parent_observation_id']]
            command = parent_observation['input']['calling']
            tool_stats = repeated_tool_calls[observation['metadata']
                                             ['attributes']['tool_name']]
            tool_stats[command] = tool_stats.get(command, 0) + 1

        usage = observation.get("usage_details", {})
        if usage:
            total_output += usage.get("output", 0)
            total_reasoning += usage.get("completion_details.reasoning", 0)
        
        # Check if this is an LLM call (has model field)
        if observation.get("model"):
            total_llm_calls += 1
            
            # Get token counts for this call
            call_input = usage.get("input", 0) if usage else 0
            call_output = usage.get("output", 0) if usage else 0
            call_total = call_input + call_output
            
            # Calculate context window utilization for this call
            if call_total > 0:
                utilization = call_total / CONTEXT_WINDOW_SIZE
                context_window_utilizations.append(utilization)
            
            # Track total LLM latency for throughput calculation
            latency_ms = observation.get("latency", 0)
            if latency_ms and latency_ms > 0:
                total_llm_latency_ms += latency_ms

    if total_output > 0:
        ratio = (total_reasoning / total_output) * 100
        print(
            f"Planning Overhead (Reasoning/Output): {ratio:.1f}% ({total_reasoning}/{total_output})")

    for tool_name, tool_stats in repeated_tool_calls.items():
        print(f"Tool: {tool_name}")
        for command, count in tool_stats.items():
            argument = command[command.find('arguments='):]
            print('\targuments:', argument, '\n\tcount:', count)

    # 1. Global Latency (End-to-End)
    # Try to find the root span (usually the one with no parent or named 'crewai-index-trace')
    root_span = next(
        (o for o in data if not o.get("parent_observation_id")), None)
    root_span_patterns = [
        r'^(Crew_[A-Za-z0-9]+(-[A-Za-z0-9]+)*\.kickoff)$',
        r'^crewai-index-trace$'
    ]
    if not root_span:
        # Fallback: check for specific name
        for pattern in root_span_patterns:
            root_span = next(
                (o for o in data if re.fullmatch(pattern, o.get("name"))), None)
            if root_span:
                break

    if root_span:
        latency_sec = 0.0
        if root_span.get("latency"):
            latency_sec = root_span.get("latency")
        elif root_span.get("end_time") and root_span.get("start_time"):
            # Parse iso strings if needed
            start = root_span.get("start_time")
            end = root_span.get("end_time")
            if isinstance(start, str):
                try:
                    start = datetime.fromisoformat(start)
                except ValueError:
                    pass
            if isinstance(end, str):
                try:
                    end = datetime.fromisoformat(end)
                except ValueError:
                    pass

            if isinstance(start, datetime) and isinstance(end, datetime):
                latency_sec = (end - start).total_seconds()

        print(f"{'End to End Latency':<25} {latency_sec:.2f} ms")

    task_map = {}  # map observation_id -> task_id
    for obs in data:
        # Check metadata for task_id
        t_id = None
        metadata = obs.get("metadata", {})
        if metadata and isinstance(metadata, dict):
            attributes = metadata.get("attributes", {})
            if attributes and isinstance(attributes, dict):
                for k, v in attributes.items():
                    if "task_id" in k.lower():
                        t_id = v
                        break

        if t_id:
            task_map[obs.get("id")] = t_id

    # Now aggregate usage for each task_id
    task_usages = {}  # task_id -> list of total_tokens

    for obs in data:
        parent_id = obs.get("parent_observation_id")
        if parent_id and parent_id in task_map:
            # This observation is a child of a task
            usage = obs.get("usage_details", {})
            total = usage.get("total", 0)
            if total > 0:
                t_id = task_map[parent_id]
                if t_id not in task_usages:
                    task_usages[t_id] = []
                task_usages[t_id].append(total)
    total_usage = 0
    if task_usages:
        for task_id, usages in task_usages.items():
            print("\nTask ID", task_id)
            total_usage = sum(usages) if usages else 0
            print( f"{'Total token usage:':<25} {total_usage}\n" )
    else:
        print("No token usage associated with tasks.")

    print("Total LLM Calls:", total_llm_calls)
    print("\nTokens Breakdown:")
    print("Total Reasoning Tokens:", total_reasoning)
    print("Total Output Tokens:", total_output)
    print("Planning Overhead:", (total_reasoning / total_output) * 100, "%")
    print("Total Usage:", total_usage)
    
    # Tool Reuse Rate
    print("\n--- Tool Reuse Rate ---")
    print(f"Total Tool Usages: {total_tool_usages}")
    print(f"Repeated Tool Usages: {repeated_tool_usages}")
    if total_tool_usages > 0:
        reuse_rate = (repeated_tool_usages / total_tool_usages) * 100
        print(f"Overall Tool Reuse Rate: {reuse_rate:.2f}%")
    else:
        print("Overall Tool Reuse Rate: N/A (no tool usages)")
    
    # Per-tool reuse rates
    print("\nPer-Tool Reuse Rates:")
    all_tools = set(per_tool_usages.keys())
    for tool in sorted(all_tools):
        usages = per_tool_usages[tool]
        repeated = per_tool_repeated.get(tool, 0)
        if usages > 0:
            rate = (repeated / usages) * 100
            print(f"  {tool}: {rate:.2f}% ({repeated}/{usages})")
        else:
            print(f"  {tool}: N/A")
    
    # Calculate and print new metrics
    print("\n--- Context Window Utilization ---")
    if context_window_utilizations:
        # Geometric mean: exp(mean(log(x))) - more robust for products
        log_sum = sum(math.log(u) for u in context_window_utilizations)
        geometric_mean = math.exp(log_sum / len(context_window_utilizations))
        max_utilization = max(context_window_utilizations)
        print(f"Context Window Size: {CONTEXT_WINDOW_SIZE:,} tokens")
        print(f"Number of LLM Calls: {len(context_window_utilizations)}")
        print(f"Context Window Utilization (Geometric Mean): {geometric_mean:.6%}")
        print(f"Context Window Utilization (Max): {max_utilization:.6%}")
    else:
        print("No LLM calls found with token usage data.")
    
    print("\n--- Token Throughput ---")
    if total_llm_latency_ms > 0 and total_output > 0:
        total_llm_time_sec = total_llm_latency_ms / 1000.0
        avg_throughput = total_output / total_llm_time_sec
        print(f"Total LLM Time: {total_llm_time_sec:.2f} sec")
        print(f"Average Per-Call Token Throughput: {avg_throughput:.2f} tokens/sec")
    else:
        print("No throughput data available.")
    
    # Ultimate token throughput: total output tokens / end-to-end latency
    if root_span and latency_sec and latency_sec > 0 and total_output > 0:
        # latency_sec is already in milliseconds from the root span, convert to seconds
        e2e_latency_sec = latency_sec / 1000.0
        ultimate_throughput = total_output / e2e_latency_sec
        print(f"Ultimate Token Throughput (Total Output / E2E Latency): {ultimate_throughput:.2f} tokens/sec")
    else:
        print("Unable to calculate ultimate token throughput (missing E2E latency or output tokens).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        possible_paths = [
            # "../observations_dump.json",
            "../observations_incident_1.json",
        ]
        json_file = None
        for p in possible_paths:
            if os.path.exists(p):
                json_file = p
                break

        if not json_file:
            print("Usage: python analyze_traces.py <path_to_observations_dump.json>")
            print(
                "Could not find default 'observations_dump.json' in common locations."
            )
            sys.exit(1)

    load_and_print_observations(json_file)

