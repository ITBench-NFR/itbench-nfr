
import os
import re
import subprocess
import time
import shutil
import glob

# Configuration
INCIDENTS_MD_PATH = "../ITBench-Scenarios/sre/docs/incidents.md"
AGENTS_DIR = "../ITBench-SRE-Agent"
SCENARIOS_DIR = "../ITBench-Scenarios/sre"
RESULTS_DIR = "../benchmark_results"

def get_incidents():
    """Parses incidents.md to find all incident IDs."""
    incidents = []
    with open(INCIDENTS_MD_PATH, "r") as f:
        content = f.read()
        # Look for headers like ### [Incident 1]
        matches = re.findall(r"### \[Incident (\d+)\]", content)
        incidents = [int(m) for m in matches]
    return sorted(list(set(incidents)))

def run_command(command, cwd=None, env=None, background=False, quiet=False):
    """Runs a shell command."""
    print(f"Running: {command}")
    
    stdout = subprocess.DEVNULL if quiet else None
    stderr = subprocess.DEVNULL if quiet else None

    if background:
        return subprocess.Popen(command, shell=True, cwd=cwd, env=env, stdout=stdout, stderr=stderr)
    
    result = subprocess.run(command, shell=True, cwd=cwd, env=env, stdout=stdout, stderr=stderr)
    if result.returncode != 0:
        print(f"Error running command: {command}")
        return False
    return True

def main():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    incidents = get_incidents()
    print(f"Found {len(incidents)} incidents: {incidents}")

    # Ensure we are in the root directory
    root_dir = os.getcwd()
    root_dir = os.path.dirname(root_dir)

    for inc_id in incidents:
        print(f"\n{'='*50}")
        print(f"Starting Incident {inc_id}")
        print(f"{'='*50}")

        # 1. Start Incident
        env = os.environ.copy()
        env["INCIDENT_NUMBER"] = str(inc_id)
        
        # We wrap the make command in 'conda run -n sre' to ensure the 'sre' environment 
        # (containing ansible-playbook) is used.
        # Note: This assumes 'conda' is in the PATH.
        start_cmd = f"conda run -n sre make start_incident"
        
        if not run_command(start_cmd, cwd=SCENARIOS_DIR, env=env):
            print(f"Failed to start incident {inc_id}. Skipping.")
            continue

        # Wait a bit for things to settle
        print("Waiting 30s for incident stack to stabilize...")
        time.sleep(30)

        # 2. Port Forwarding
        # Cleanup any existing port forward on 8080
        run_command("fuser -k 8080/tcp", quiet=True)
        
        # Wait for ingress controller to be ready
        print("Waiting for ingress-nginx-controller deployment...")
        run_command("kubectl wait --namespace ingress-nginx --for=condition=available deployment/ingress-nginx-controller --timeout=300s", quiet=True)
        
        # kubectl port-forward svc/ingress-nginx-controller -n ingress-nginx 8080:80 &
        print("Starting port forwarding...")
        pf_log = open(f"pf_incident_{inc_id}.log", "w")
        pf_process = subprocess.Popen(
            "kubectl port-forward svc/ingress-nginx-controller -n ingress-nginx 8080:80",
            shell=True,
            stdout=pf_log,
            stderr=pf_log
        )
        
        # Wait for port 8080 to be listening
        print("Waiting for port 8080 to be ready...")
        import socket
        port_ready = False
        for _ in range(60): # Wait up to 60 seconds
            try:
                with socket.create_connection(("localhost", 8080), timeout=1):
                    port_ready = True
                    break
            except (ConnectionRefusedError, OSError):
                time.sleep(1)
        
        if not port_ready:
            print("timeout waiting for port 8080. Checking logs...")
            pf_process.terminate()
            pf_log.close()
            with open(f"pf_incident_{inc_id}.log", "r") as f:
                print(f.read())
            continue # Skip this incident if port forward fails

        # 3. Run Agent
        # We execute 'python -c ... run()' to start the agent automatically without user interaction.
        # We pass EXP_NAME because the agent code uses it for output path generation.
        
        # Use absolute path for mount to avoid ambiguity
        agents_abs_path = os.path.abspath(AGENTS_DIR)
        
        agent_cmd = (
            f"docker run --rm --network=host "
            f"--mount type=bind,src=\"{agents_abs_path}\",target=/app/lumyn "
            f"-e KUBECONFIG=/app/lumyn/config "
            f"-e INCIDENT_NUMBER={inc_id} "
            f"-e EXP_NAME=benchmark_run "
            f"-e PYTHONPATH=$PYTHONPATH:/app/lumyn/src "
            f"itbench-sre-agent "
            f"sudo -E uv run python -c 'from lumyn.main import run; run()'"
        )

        run_command(agent_cmd, cwd=root_dir)

        # 4. Cleanup Port Forward
        if pf_process:
            pf_process.terminate()
            pf_process.wait()
            pf_log.close()
            # Verify killed
            run_command("fuser -k 8080/tcp", quiet=True)

        # 5. Collect Traces
        # The agent should have produced 'observations_dump.json' in the AGENTS_DIR (mapped to /app/lumyn)
        dump_file = os.path.join(AGENTS_DIR, "observations_dump.json")
        if os.path.exists(dump_file):
            dest_file = os.path.join(RESULTS_DIR, f"observations_incident_{inc_id}.json")
            shutil.move(dump_file, dest_file)
            print(f"Saved traces to {dest_file}")
        else:
            print(f"Warning: No observations_dump.json found for incident {inc_id}")

        # 6. Stop Incident
        stop_cmd = f"conda run -n sre make stop_incident"
        run_command(stop_cmd, cwd=SCENARIOS_DIR, env=env)
        
        # Wait for cleanup
        time.sleep(10)

if __name__ == "__main__":
    main()
