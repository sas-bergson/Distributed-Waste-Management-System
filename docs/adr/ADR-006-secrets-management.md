# ADR-006: Secrets Management Boundaries and Provider Selection

- **Status:** Proposed; managed provider decision pending
- **Date:** 2026-11-25
- **Feature:** 6 — Secrets management

## Context

Feature 6 is classified as CI+MS, so its scope is broader than preventing
plaintext Kubernetes Secret manifests from entering Git. DWMS has a CI
validator and tests for ordinary Kubernetes Secret resources. The repository
also has a guide describing local `.env` use and a proposed Kubernetes
Sealed Secrets workflow.

No managed secrets provider, deployment target, workload identity, controller
installation, or runtime secret-retrieval integration is currently selected
or implemented. The project must not treat a repository check and encrypted
Kubernetes manifests as a complete managed-secrets solution.

## Decision

1. Keep the CI check as a repository safeguard: reject `kind: Secret` in YAML,
   allow `SealedSecret`, and fail safely on unreadable or invalid YAML.
2. Treat Sealed Secrets as a **proposed Kubernetes-specific** mechanism for
   encrypted manifests, subject to approval of a Kubernetes target and
   operational key handling.
3. Leave the managed secrets provider **undecided**. Do not add a provider
   dependency or claim provider-backed secret delivery until the project
   selects one and approves the integration.
4. Track provider selection, workload/CI access, rotation, and recovery as
   remaining Feature 6 work. The current CI and proposed Sealed Secrets
   approach do not satisfy the entire CI+MS requirement.

## Scope and implementation status

| Capability | Status |
|---|---|
| Detect ordinary Kubernetes `Secret` resources in repository YAML | Implemented in CI |
| Accept `SealedSecret` resources; fail on invalid/unreadable YAML | Implemented in validator and tests |
| Ignore local `.env` files while keeping `.env.example` available | Implemented in `.gitignore` |
| Deploy a Sealed Secrets controller or manage its private key | Not implemented; proposed for an approved Kubernetes target |
| Select a managed secrets provider | Pending decision |
| Integrate workloads and CI with a managed provider | Not implemented |
| Automate rotation, recovery, and operational auditing | Not implemented |

## Consequences

- The current check reduces the risk of committing a basic Kubernetes Secret
  manifest but is not a general-purpose secret scanner or secret-delivery
  system.
- Sealed Secrets can support Git-managed Kubernetes deployment manifests, but
  it is Kubernetes-specific and depends on secure handling and recovery of
  the controller's private key.
- No cloud provider or self-hosted service is implied by this proposal.
- Feature 6 remains incomplete until the team records the provider decision,
  implements the approved integration, and verifies access, rotation, and
  failure/recovery behavior.

## Alternatives considered

- **Plain Kubernetes Secrets in Git:** rejected because manifests may contain
  plaintext credentials.
- **Select a cloud secrets provider now:** deferred because the deployment
  target, identity model, and provider constraints have not been agreed.
- **Use Sealed Secrets as the entire solution:** rejected because it does not
  provide a managed secrets service or cover non-Kubernetes workloads by
  itself.

## Follow-up

The project maintainers should select the deployment target and provider,
define workload and CI identities, and document operational ownership for
access, audit, rotation, backup, and recovery. Record that decision in a
superseding or follow-up ADR before adding provider-specific integration.

See the [Secrets Management Guide](../guides/secrets-management.md).
