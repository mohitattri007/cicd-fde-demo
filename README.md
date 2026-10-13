# CI/CD FDE Demo — Support Agent API

A small, teachable end-to-end CI/CD example for an FDE interview. It uses **FastAPI + pytest + Docker + GitHub Actions + GHCR + Kubernetes + Argo CD (GitOps)**.

> **Scope:** the app is deliberately tiny. The goal is to demonstrate delivery mechanics, quality gates, immutable artifacts, deployment reconciliation, validation, and rollback—not to build an actual AI agent.

## What the pipeline does

1. A developer pushes a feature branch and opens a PR.
2. `ci.yml` runs tests and builds the Docker image (but does not publish it).
3. After code is merged to `main`, `release.yml` reruns tests, builds and publishes an image tagged with the commit SHA to GitHub Container Registry (GHCR).
4. The release workflow updates the image reference in a **separate deployment-config repository**.
5. Argo CD watches that config repository and reconciles Kubernetes to the desired state.
6. Kubernetes rolls out the new version. A smoke test validates `/health` and `/version`.
7. To roll back, revert the image-reference commit in the deployment-config repository and let Argo CD reconcile it.

```text
Feature branch → PR → CI (tests + Docker build) → merge to main
                                               ↓
                            release CI → image build/publish → GHCR (SHA tag)
                                               ↓
                            update deployment-config Git repository
                                               ↓
                            Argo CD → Kubernetes rolling update
                                               ↓
                            smoke tests → monitor / rollback by Git revert
```

## Repository layout

```text
cicd-fde-demo/
├── app/
│   └── main.py                   # FastAPI endpoints: /, /health, /version
├── tests/
│   └── test_main.py              # API tests
├── .github/workflows/
│   ├── ci.yml                    # PR and main CI; never publishes from PRs
│   └── release.yml               # Main-branch image publish + GitOps config update
├── k8s/
│   ├── deployment.yaml           # Kubernetes Deployment template
│   └── service.yaml              # ClusterIP Service
├── argocd/
│   └── application.yaml           # Argo CD Application template
├── scripts/
│   ├── smoke_test.sh              # Checks /health and /version
│   └── update_image.py            # Safely replaces a manifest image reference
├── Dockerfile
├── .dockerignore
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── docker-compose.yml             # Simple local demo
└── README.md
```

## Prerequisites

For local work: Python 3.12+, Docker Desktop or Docker Engine, Git.

For the full cloud demo: a GitHub repository, GHCR access, a Kubernetes cluster, and Argo CD already installed and connected. **Do not attempt to create a cluster during the 30-minute teaching session.**

## 1. Run locally without Docker

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/`, `http://localhost:8000/health`, and `http://localhost:8000/version`.

## 2. Run with Docker

```bash
docker build -t support-agent-api:local .
docker run --rm -p 8000:8000 support-agent-api:local
```

Or use Compose:

```bash
docker compose up --build
# In another terminal:
curl http://localhost:8000/health
curl http://localhost:8000/version
docker compose down
```

## 3. Set up GitHub CI (PR checks)

1. Create a GitHub repository and push this project.
2. Open `.github/workflows/ci.yml` and check that it triggers on `pull_request` targeting `main` and pushes to `main`.
3. Open a feature branch, change the app version, push it, and create a PR.
4. In **Settings → Rules → Rulesets** (or branch protection), require the CI status check before merge.

CI runs on a GitHub-hosted runner. The code is in the remote repository on the feature branch; `actions/checkout` fetches the PR's proposed code to the runner. A PR check does not need the change to be merged first.

## 4. Set up image publishing to GHCR

The included `release.yml` publishes only on pushes to `main` (typically after merge) and uses `GITHUB_TOKEN` with package-write permissions. Image scanning is listed as a production-hardening step rather than wired into this minimal demo. Review the workflow and the repository's organization policies before using it.

1. Push the repository to GitHub.
2. In repository **Settings → Actions → General**, ensure workflows have the required read/write package permission, or use the explicit `packages: write` permission in the workflow.
3. Merge a change to `main`.
4. Open **Actions** and inspect the `release` run. The image is tagged with the full Git commit SHA, e.g. `ghcr.io/OWNER/REPO:<40-char-sha>`.
5. Verify the package in the repository's **Packages** page. If the package is private, Kubernetes must have registry pull access.

The workflow uses the repository name as the image name. If your organization restricts package creation or token permissions, adjust repository/org settings. Never place registry passwords in source code.

## 5. Configure the GitOps deployment repository

Use **two repositories** for a clean separation of concerns:

- **Application repo:** this project; builds/tests/publishes the container image.
- **Deployment-config repo:** stores the Kubernetes manifests watched by Argo CD.

In the deployment-config repo, copy `k8s/deployment.yaml` and `k8s/service.yaml` into a directory such as `apps/support-agent-api/`. Update the image to the GHCR image and ensure the namespace, ports, probes, and pull-secret requirements fit your cluster. Keep the Service manifest beside the Deployment.

In the application repo, configure these repository Actions variables/secrets:

| Name | Type | Example / purpose |
|---|---|---|
| `DEPLOY_REPO` | Actions variable | `your-org/platform-deployments` |
| `DEPLOY_FILE` | Actions variable | `apps/support-agent-api/deployment.yaml` |
| `DEPLOY_BRANCH` | Actions variable | `main` |
| `DEPLOY_TOKEN` | Actions secret | Fine-grained PAT or GitHub App token with **contents: write** only on the deployment-config repo |

The `release.yml` workflow updates only the image reference in the deployment manifest and commits the change. For a production system, prefer a GitHub App with narrowly scoped permissions and consider required reviews or a promotion PR rather than granting broad write access.

If you want to rehearse without a second repository, comment out the `update-gitops-config` job in `release.yml`; CI and image publishing will still work. Do not claim Argo CD deployment happened unless you actually connected it.

## 6. Configure Argo CD

1. Install Argo CD in the target cluster before the demo.
2. Ensure it can read the deployment-config repository.
3. Edit `argocd/application.yaml`: replace the repo URL, path, revision, namespace, and destination cluster as appropriate.
4. Apply it from a machine with `kubectl` access:

```bash
kubectl apply -f argocd/application.yaml
argocd app get support-agent-api
argocd app sync support-agent-api
argocd app wait support-agent-api --health --timeout 120
```

The sample Application uses automated sync, pruning, and self-heal as an illustration. Decide on those settings deliberately for your environment. Automated sync does not mean your CI tests are unnecessary. The manifest path must contain valid Kubernetes YAML. Make sure the Deployment's image reference is the one updated by the release workflow.

### Private GHCR image note

If the GHCR package is private, configure an `imagePullSecret` in the target namespace using a least-privilege read-only package credential, and reference it in the Pod spec. Do not commit the secret or its token to Git. For a public demo image, private registry credentials may not be needed.

## 7. Demonstration runbook (7 minutes)

1. Show the healthy baseline: `/health` and `/version` return `1.0.0`.
2. Change `APP_VERSION` in `app/main.py` to `1.1.0`, add a test if time permits, commit to a feature branch, and push.
3. Open a PR. Show the CI job passing before merge.
4. Merge the PR. Show the release workflow running on `main`.
5. Show the SHA-tagged image in GHCR.
6. Show the deployment-config commit changing the image tag; show Argo CD syncing and Kubernetes rolling out.
7. Run `scripts/smoke_test.sh <base-url>` or call the endpoints in a browser.
8. For rollback, revert the deployment-config image-reference commit, then watch Argo CD restore the prior version. Verify `/version` returns the previous version.

**Keep the environment pre-provisioned.** Do not rely on setting up Kubernetes, Argo CD, registry permissions, or network access live.

## 8. Failure troubleshooting

| Symptom | First checks |
|---|---|
| PR check fails | GitHub Actions log, pytest failure, branch diff |
| Docker build fails | Dockerfile, dependency versions, build context, `.dockerignore` |
| GHCR push denied | `packages: write`, repository/org token policy, package permissions |
| GitOps update fails | `DEPLOY_REPO`, token scope, branch and manifest path |
| Argo CD `OutOfSync` | Git revision/path, manifest diff; OutOfSync means drift, not necessarily outage |
| Pod `ImagePullBackOff` | Image tag exists, registry URL, `imagePullSecret` and namespace |
| Pod `CrashLoopBackOff` | `kubectl logs`, `kubectl logs --previous`, `kubectl describe pod` |
| Readiness fails | Probe path/port, app startup time, container logs |
| HTTP 500 after sync | App logs, dependencies, environment configuration, traces; syncing is not functional validation |

Useful commands:

```bash
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> --previous -n <namespace>
kubectl rollout status deployment/support-agent-api -n <namespace>
kubectl rollout history deployment/support-agent-api -n <namespace>
```

## 9. Design decisions to explain to the panel

- **GitHub Actions:** native repository integration and workflow-as-code; Jenkins/GitLab CI are valid alternatives.
- **PR CI:** catch defects before merge; required status checks enforce the gate.
- **Main release workflow:** test the integrated code, publish an artifact only from a trusted branch.
- **Docker + GHCR:** package runtime/dependencies and keep versioned images centrally.
- **Commit SHA tag:** traceable image version; use image digests for stronger immutability guarantees. Never depend on `latest` for production promotion.
- **Separate deployment repository:** app code and environment desired state have separate ownership/review and reduce CI/CD coupling.
- **Argo CD:** continuously reconciles Git-defined desired state; a manual cluster change can be overwritten if self-heal is enabled.
- **Rolling deployment:** simple default; not a zero-downtime guarantee. Readiness, capacity, backward-compatible changes, and monitoring matter.
- **Rollback:** revert desired state in Git so the action is auditable and Argo CD converges on the previous image. Database migrations and external side effects need separate compatibility/recovery planning.
- **Security:** least privilege, protected branches, secret management, dependency/image scans, non-root containers, and no secrets in logs/images.

## 10. Limitations / production hardening

This is an interview demo, not a complete production platform. Before production, add action SHA pinning, SBOM and provenance, image signing/verification, automated vulnerability policy, environment approvals, resource/security contexts, liveness/startup probes, monitoring/alerting, rate-limited progressive delivery if needed, and backward-compatible database migration procedures. The sample smoke test runs against a supplied URL; wire it into your deployment process only after the environment and network access are configured.
