# docker build ./ITBench-CISO-CAA-Agent -t ciso-agent:latest
# docker build ./ITBench-Scenarios/ciso/ -t ciso-task-scenarios:latest

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ./dir/scene_dir:/tmp/scenario \
    -v ./dir/agentdir:/tmp/agent \
    -v ./dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 2.gen-cis-b-k8s-kubectl-opa\
    deploy_bundle

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ./dir/scene_dir:/tmp/scenario \
    -v ./dir/agentdir:/tmp/agent\
    -v ./dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 2.gen-cis-b-k8s-kubectl-opa\
    inject_fault

# docker run --rm -ti --name ciso-task-scenario \
#     -v ./dir/scene_dir:/tmp/scenario \
#     -v ./dir/agentdir:/tmp/agent\
#     -v ./dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
#     ciso-task-scenarios:latest \
#     sh -c \
#     "make -s -C 2.gen-cis-b-k8s-kubectl-opa \
#     get \
#     2>/dev/null | jq -r .goal_template"

docker run --rm -ti --name ciso-agent \
    --network host \
    -v ./dir/agentdir:/tmp/agent \
    -v ./.env:/etc/ciso-agent/.env \
    --mount type=bind,source=./ciso_traces,target=/tmp/agent/ciso_traces \
    ciso-agent:latest \
    python src/ciso_agent/main.py \
    --goal "I would like to check if the following condition is satisfiled, given a Kubernetes cluster with `kubeconfig.yaml`
    Minimize the admission of containers wishing to share the host network namespace. 

To check the condition, do the following steps. 
- get related resource(s) on the cluster by kubectl command
- chcek if the conditions are satisfied by OPA Rego policy

for those steps, you need to create an OPA Rego policy `policy.rego`. 
Also, save the kubectl command as `script.sh` with the following design. 
- The script should output the collected related resources to a file named `collected_data.json` in the current working directory.
- Please remove any kubeconfig configuration (e.g. --kubeconfig args) from the script, as users will configure the kubeconfig using environment variables or other methods.

If running the policy failed and if you can fix the issue, you will do it and try running again.

Once you get a final answer, you can quit the work.

The cluster's kubeconfig is at '/tmp/agent/kubeconfig.yaml'.
You can use '/tmp/agent' as your workdir." \
    --auto-approve

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ./dir/scene_dir:/tmp/scenario \
    -v ./dir/agentdir:/tmp/agent\
    -v ./dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 2.gen-cis-b-k8s-kubectl-opa \
    evaluate > ./ciso_traces/eval_2.log

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ./dir/scene_dir:/tmp/scenario \
    -v ./dir/agentdir:/tmp/agent\
    -v ./dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 2.gen-cis-b-k8s-kubectl-opa \
    revert
