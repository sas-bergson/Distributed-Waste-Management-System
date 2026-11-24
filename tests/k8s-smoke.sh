#!/usr/bin/env bash
# Feature 3 TEST (k8s-smoke): the Kubernetes manifests must bring up every
# service, and the gateway must answer.
# Needs: kubectl and a running cluster (kind, minikube or Docker Desktop Kubernetes).
# Run:   bash tests/k8s-smoke.sh        (KEEP=1 leaves the stack running afterwards)
set -uo pipefail
cd "$(dirname "$0")/.."

NS=dwms
MANIFESTS=infrastructure/k8s

if [ ! -f "$MANIFESTS/kustomization.yaml" ]; then
  echo "FAIL: $MANIFESTS/kustomization.yaml not found in $(pwd)"
  exit 1
fi
command -v kubectl >/dev/null 2>&1 || { echo "FAIL: kubectl is not installed"; exit 1; }
kubectl cluster-info >/dev/null 2>&1 || { echo "FAIL: no reachable Kubernetes cluster (start kind, minikube or Docker Desktop Kubernetes)"; exit 1; }

PF_PID=""
cleanup() {
  [ -n "$PF_PID" ] && kill "$PF_PID" 2>/dev/null
  if [ "${KEEP:-0}" != "1" ]; then
    kubectl delete -k "$MANIFESTS" --ignore-not-found --wait=false >/dev/null 2>&1
  fi
}
trap cleanup EXIT

echo "--- applying manifests ---"
kubectl apply -k "$MANIFESTS" || { echo "FAIL: kubectl apply failed"; exit 1; }

fail=0

echo "--- waiting for rollouts ---"
for d in redis mosquitto locations map requests realtime notifications gateway; do
  kubectl -n "$NS" rollout status "deployment/$d" --timeout=180s || { echo "FAIL: deployment/$d is not ready"; fail=1; }
done
kubectl -n "$NS" rollout status statefulset/postgis --timeout=240s || { echo "FAIL: statefulset/postgis is not ready"; fail=1; }

echo "--- pod status ---"
kubectl -n "$NS" get pods

not_ready=$(kubectl -n "$NS" get pods --no-headers | awk '{split($2,a,"/"); if ($3!="Running" || a[1]!=a[2]) print $1}')
if [ -n "$not_ready" ]; then
  echo "FAIL: pods not Running and Ready:"
  echo "$not_ready"
  fail=1
fi

echo "--- replica check (stateless services need at least 2) ---"
for d in gateway locations map requests realtime notifications; do
  ready=$(kubectl -n "$NS" get deployment "$d" -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
  if [ "${ready:-0}" -lt 2 ]; then
    echo "FAIL: $d has ${ready:-0} ready replicas (need 2)"
    fail=1
  fi
done

echo "--- gateway check ---"
kubectl -n "$NS" port-forward svc/gateway 18080:80 >/dev/null 2>&1 &
PF_PID=$!
sleep 3
if curl -fsS --max-time 10 http://127.0.0.1:18080/ >/dev/null; then
  echo "gateway answers on port 80"
else
  echo "FAIL: gateway did not answer"
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "FAIL: Kubernetes smoke test failed"
  exit 1
fi
echo "PASS: all services Running and Ready, gateway answers"
