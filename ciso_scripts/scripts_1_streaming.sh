docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent \
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 1.gen-cis-b-k8s-kyverno\
    deploy_bundle

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent\
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 1.gen-cis-b-k8s-kyverno\
    inject_fault

mkdir -p ../ciso_traces/1.gen-cis-b-k8s-kyverno-streaming

docker run --rm -ti --name ciso-agent \
    --network host \
    -v ../dir/agentdir:/tmp/agent \
    -v ./.env:/etc/ciso-agent/.env \
    --mount type=bind,source=../ciso_traces/1.gen-cis-b-k8s-kyverno-streaming,target=/tmp/agent/ciso_traces \
    ciso-agent:latest \
    python src/ciso_agent/main.py \
    --goal "streaming I would like to check if the following condition is satisfiled, given a Kubernetes cluster with `kubeconfig.yaml`
    Minimize the admission of containers wishing to share the host network namespace.

To check the condition, do the following steps.
- deploy a Kyverno policy to the cluster
- chcek if the policy is correctly deployed.

If deploying the policy failed and if you can fix the issue, you will do it and try deploying again.
Once you get a final answer, you can quit the work.

The cluster's kubeconfig is at '/tmp/agent/kubeconfig.yaml'.
You can use '/tmp/agent' as your workdir." \
    --auto-approve

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent\
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 1.gen-cis-b-k8s-kyverno \
    evaluate > ../ciso_traces/1.gen-cis-b-k8s-kyverno-streaming/evaluate.log

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent\
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 1.gen-cis-b-k8s-kyverno \
    revert

###########################################