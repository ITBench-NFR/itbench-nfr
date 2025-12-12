
import json
import os
import sys
import pandas as pd
from datetime import datetime

def load_and_print_observations(json_path):
    """
    Loads observations from a JSON file and prints them in a readable format using pandas.
    """
    if not os.path.exists(json_path):
        print(f"Error: File not found at {json_path}")
        return

    print(f"Loading observations from: {json_path}")
    try:
        with open(json_path, 'r') as f:
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

    # Normalize data for DataFrame
    # We want to extract key fields for the summary table
    
    rows = []
    for obs in data:
        row = {
            "ID": obs.get("id"),
            "Name": obs.get("name"),
            "Type": obs.get("type", "UNKNOWN"),
            "Start Time": obs.get("start_time"),
            "Latency (s)": obs.get("latency", 0.0),
            "Model": obs.get("model"),
            "Total Cost ($)": obs.get("calculated_total_cost") or 0.0,
            "Task ID": obs.get("task_id"), # extracted in the python script
            "Time to First Token": obs.get("time_to_first_token")
        }
        
        # Usage details
        usage = obs.get("usage_details", {})
        row["Input Tokens"] = usage.get("input", 0)
        row["Output Tokens"] = usage.get("output", 0) or usage.get("completion", 0)
        row["Total Tokens"] = usage.get("total", 0)
        
        # Reasoning tokens (might have been manually calculated in the script or usage)
        # The script calculates it but doesn't explicitly save it as a top-level field in obs_dict yet?
        # Actually in the modified script:
        #   row["Reasoning Tokens"] = r_tokens was NOT added to obs_dict key in loop.
        #   The modified script just prints r_tokens in the summary loop. 
        #   Let's check if usage_details has it.
        #   The logic in tracing.py: obs_dict = obs.dict() etc.
        #   If 'reasoning' is in usage_details, we get it.
        
        r_tokens = usage.get("reasoning", 0)
        if not r_tokens:
             for k, v in usage.items():
                 if "reasoning" in k.lower() and isinstance(v, (int, float)):
                      r_tokens += v
        row["Reasoning Tokens"] = r_tokens
        
        rows.append(row)

    df = pd.DataFrame(rows)
    
    # Sort by start time if available
    if "Start Time" in df.columns:
        df["Start Time"] = pd.to_datetime(df["Start Time"])
        df.sort_values(by="Start Time", inplace=True)

    # Reorder columns
    cols_order = [
         "Task ID", "Name", "Type", "Model", "Latency (s)", 
         "Input Tokens", "Reasoning Tokens", "Output Tokens", "Total Tokens", "Total Cost ($)"
    ]
    final_cols = [c for c in cols_order if c in df.columns]
    
    # Display options
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print("\n" + "="*80)
    print("OBSERVATIONS SUMMARY")
    print("="*80)
    print(df[final_cols].to_string(index=False))

    # Aggregates
    print("\n" + "="*80)
    print("AGGREGATE METRICS")
    print("="*80)
    
    print(f"Total Observations: {len(df)}")
    print(f"Total Cost: ${df['Total Cost ($)'].sum():.4f}")
    if 'Total Tokens' in df.columns:
        print(f"Total Tokens: {df['Total Tokens'].sum()}")
        
    # Reasoning ratio
    total_reasoning = df["Reasoning Tokens"].sum()
    total_output = df["Output Tokens"].sum()
    if total_output > 0:
        ratio = (total_reasoning / total_output) * 100
        print(f"Planning Overhead (Reasoning/Output): {ratio:.1f}% ({total_reasoning}/{total_output})")

    # Global Latency (End-to-End)
    # Try to find the root span (usually the one with no parent or named 'crewai-index-trace')
    root_span = next((o for o in data if not o.get("parent_observation_id")), None)
    if not root_span:
         # Fallback: check for specific name
         root_span = next((o for o in data if o.get("name") == 'crewai-index-trace'), None)
    
    if root_span:
        latency_sec = 0.0
        if root_span.get('latency'):
            latency_sec = root_span.get('latency')
        elif root_span.get('end_time') and root_span.get('start_time'):
            # Parse iso strings if needed
            start = root_span.get('start_time')
            end = root_span.get('end_time')
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
                 
        print(f"End-to-End Latency: {latency_sec:.2f} ms")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Default to the one generated by tracing.py in current working dir?
        # Or in ITBench-SRE-Agent root?
        # Let's try to look in typical places
        possible_paths = [
            "observations_dump.json",
            "../ITBench-SRE-Agent/observations_dump.json",
        ]
        json_file = None
        for p in possible_paths:
            if os.path.exists(p):
                json_file = p
                break
        
        if not json_file:
             print("Usage: python analyze_traces.py <path_to_observations_dump.json>")
             print("Could not find default 'observations_dump.json' in common locations.")
             sys.exit(1)

    load_and_print_observations(json_file)
