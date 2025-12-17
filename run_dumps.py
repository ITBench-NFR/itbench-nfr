import os
import analyze_traces

def run_dumps():
    incidents = [1, 16, 23, 30, 102]
    
    # Map from directory name to output prefix
    sources = {
        "benchmark_results_planexec_sre": "planexec_sre",
        "benchmark_results_react_sre": "react_sre"
    }
    
    # Base directory is one level up from itbench-nfr
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for subdir, prefix in sources.items():
        source_dir = os.path.join(base_dir, subdir)
        
        if not os.path.exists(source_dir):
            print(f"Warning: Directory not found: {source_dir}")
            continue
            
        for incident_id in incidents:
            input_filename = f"observations_incident_{incident_id}.json"
            input_path = os.path.join(source_dir, input_filename)
            
            output_filename = f"{prefix}_incident_{incident_id}.json"
            output_path = output_filename # Save in current directory (itbench-nfr)
            
            print(f"\nProcessing Incident {incident_id} from {subdir}...")
            
            if os.path.exists(input_path):
                analyze_traces.load_and_print_observations(input_path, output_path)
            else:
                print(f"  Input file not found: {input_path}")

if __name__ == "__main__":
    run_dumps()
