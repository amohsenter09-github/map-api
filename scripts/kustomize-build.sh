#!/usr/bin/env bash
# Sanity check: run kustomize build on all overlays.
# Exits with 1 if any build fails.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

OVERLAYS=(
  "k8s/overlays/local"
  "k8s/overlays/cnpe-dev"
  "k8s/overlays/cnpe-prod"
)

FAILED=0
for overlay in "${OVERLAYS[@]}"; do
  echo "Building $overlay ..."
  if output=$(kustomize build "$overlay" 2>&1); then
    echo "  OK $overlay"
  else
    echo "  FAILED $overlay"
    echo "$output" | head -50
    FAILED=1
  fi
done

if [ $FAILED -eq 1 ]; then
  echo ""
  echo "One or more overlays failed to build."
  exit 1
fi

echo ""
echo "All overlays built successfully."
