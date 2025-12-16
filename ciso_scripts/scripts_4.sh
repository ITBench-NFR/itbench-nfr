# docker build ./ITBench-CISO-CAA-Agent -t ciso-agent:latest
# docker build ./ITBench-Scenarios/ciso/ -t ciso-task-scenarios:latest

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent \
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 4.upd-cis-b-k8s-kyverno\
    deploy_bundle

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent\
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 4.upd-cis-b-k8s-kyverno\
    inject_fault

mkdir -p ../ciso_traces/4.upd-cis-b-k8s-kyverno

# docker run --rm -ti --name ciso-task-scenario \
#     -v ./dir/scene_dir:/tmp/scenario \
#     -v ./dir/agentdir:/tmp/agent\
#     -v ./dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
#     ciso-task-scenarios:latest \
#     sh -c \
#     "make -s -C 4.upd-cis-b-k8s-kyverno \
#     get \
#     2>/dev/null | jq -r .goal_template"

docker run --rm -ti --name ciso-agent \
    --network host \
    -v ../dir/agentdir:/tmp/agent \
    -v ./.env:/etc/ciso-agent/.env \
    --mount type=bind,source=../ciso_traces/4.upd-cis-b-k8s-kyverno,target=/tmp/agent/ciso_traces \
    ciso-agent:latest \
    python src/ciso_agent/main.py \
    --goal "Currently, the following Kyverno policies are deployed in the Kubernetes cluster. Review these existing policies and edit them to meet additional security requirements. Please avoid creating new policy resources; instead, make the necessary changes directly to the existing resources.

    Prohibit the use of the default service account
    Prohibit privilege escalation

However, the new internal security policy now requires the following additional conditions:

    Prohibit running as the root user
    Only allow signed images from a trusted registry (trusted-registry.com)

Your task is to review the existing Kyverno policies and directly edit the existing policies to meet these new requirements. Do not change the resource names. Once you have completed the edits, update the existing resources in the Kubernetes cluster.
Steps

    Review and Edit Kyverno Policies
    Directly modify the existing policy resources to meet the new requirements. Ensure that you do not change the names of the resources. 

The cluster's kubeconfig is at '/tmp/agent/kubeconfig.yaml'.
You can use '/tmp/agent' as your workdir." \
    --auto-approve

docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent\
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 4.upd-cis-b-k8s-kyverno \
    evaluate > ../ciso_traces/4.upd-cis-b-k8s-kyverno/evaluate.log


docker run --rm -ti --name ciso-task-scenario \
    --network host \
    -v ../dir/scene_dir:/tmp/scenario \
    -v ../dir/agentdir:/tmp/agent\
    -v ../dir/agentdir/kubeconfig.yaml:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 4.upd-cis-b-k8s-kyverno \
    revert
