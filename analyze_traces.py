import json
import os
import sys
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
    total_llm_calls = 0

    for obs_id, observation in observations.items():
        if observation['name'] == 'Tool Repeated Usage':
            parent_observation = observations[observation['parent_observation_id']]
            command = parent_observation['input']['calling']
            tool_stats = repeated_tool_calls[observation['metadata']
                                             ['attributes']['tool_name']]
            tool_stats[command] = tool_stats.get(command, 0) + 1

        usage = observation.get("usage_details", {})
        if usage:
            total_output += usage.get("output", 0)
            total_reasoning += usage.get("completion_details.reasoning", 0)
        if observation.get("model"):
            total_llm_calls += 1

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
