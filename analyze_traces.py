import json
import os
import sys
import pandas as pd
from collections import defaultdict
from datetime import datetime
import re


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

    for obs_id, observation in observations.items():
        if observation['name'] == 'Tool Repeated Usage':
            parent_observation = observations[observation['parent_observation_id']]
            command = parent_observation['input']['calling']
            tool_stats = repeated_tool_calls[observation['metadata']['attributes']['tool_name']]
            tool_stats[command] = tool_stats.get(command, 0) + 1
        
        usage = observation.get("usage_details", {})
        if usage:
            total_output += usage.get( "output", 0 )
            total_reasoning += usage.get( "completion_details.reasoning", 0 )

    if total_output > 0:
            ratio = (total_reasoning / total_output) * 100
            print(f"Planning Overhead (Reasoning/Output): {ratio:.1f}% ({total_reasoning}/{total_output})")

    for tool_name, tool_stats in repeated_tool_calls.items():
        print(f"Tool: {tool_name}")
        for command, count in tool_stats.items():
            argument = command[command.find('arguments='):]
            print('\targuments:', argument, '\n\tcount:', count)

    # 1. Global Latency (End-to-End)
    # Try to find the root span (usually the one with no parent or named 'crewai-index-trace')
    root_span = next((o for o in data if not o.get("parent_observation_id")), None)
    root_span_patterns = [
        r'^(Crew_[A-Za-z0-9]+(-[A-Za-z0-9]+)*\.kickoff)$',
        r'^crewai-index-trace$'
    ]
    if not root_span:
        # Fallback: check for specific name
        for pattern in root_span_patterns:
            root_span = next((o for o in data if re.fullmatch(pattern, o.get("name"))), None)
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

        print(f"{'End to End Latency':<25} {latency_sec:.2f} seconds")

    # 2. Total Cost
    print(f"{'Total Cost':<25} ${df['Total Cost ($)'].sum():.4f}")

    # 3. Total LLM Calls
    llm_calls = df[df["Model"].notna()].shape[0]
    print(f"{'Total LLM Calls':<25} {llm_calls}")

    # 4. Planning Overhead (Reasoning Ratio)
    total_reasoning = df["Reasoning Tokens"].sum()
    total_output = df["Output Tokens"].sum()
    if total_output > 0:
        ratio = (total_reasoning / total_output) * 100
        print(
            f"{'Planning Overhead':<25} {ratio:.1f}% ({total_reasoning}/{total_output} tokens)"
        )

    # 5. Tokens Breakdown (Average per Task)
    print("\nTokens Breakdown:")

    # Re-implement logic from kubernetes_kyverno.py:
    # 1. Find all spans that are Tasks (have a task_id)
    # 2. For each task span, find its children (LLM calls usually)
    # 3. Sum/Average usage from children

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

    if task_usages:
        for task_id, usages in task_usages.items():
            if usages:
                avg_tokens = sum(usages) / len(usages)
                print(
                    f"\nAverage token usage for Task ID {task_id}: {avg_tokens:.2f} tokens"
                )
            else:
                print(f"\nAverage token usage for Task ID {task_id}: 0.00 tokens")
    else:
        print("No Task IDs found or no token usage associated with tasks.")

    print(f"\n{'='*80}")
    print(f"Total Observations: {len(df)}")
    print(f"{'='*80}\n")

    # 6. Tool Call Latencies
    print("Tool Call Latencies:")
    tool_calls = df[df["Type"] == "TOOL"]
    for _, row in tool_calls.iterrows():
        print(f"  {row['Name']}: {row['Latency (s)']} s")

    # 7. Reasoning Token Usages
    print("\nReasoning Token Usages:")
    reasoning_rows = df[df["Reasoning Tokens"] > 0]
    for _, row in reasoning_rows.iterrows():
        print(f"  {row['Name']} - reasoning: {row['Reasoning Tokens']} tokens")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Default to the one generated by tracing.py in current working dir?
        # Or in ITBench-SRE-Agent root?
        # Let's try to look in typical places
        possible_paths = [
            "../observations_dump.json",
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
