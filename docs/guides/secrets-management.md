# DWMS Secrets Management Guide

## 1. Purpose and status

This guide describes the current repository checks and the proposed approach
to managing application secrets in DWMS. It distinguishes implemented
repository safeguards from deployment functionality that has not been built
or selected.

### Implemented

- The CI workflow rejects ordinary Kubernetes `Secret` resources in repository
  YAML and runs Python tests for that validator.
- The validator accepts `SealedSecret` resources, rejects `Secret` resources,
  and fails the check when YAML cannot be read or parsed.
- Local `.env` files are ignored by Git; `.env.example` is the safe template
  for documenting variable names.

These are repository-level safeguards. They do not provision, distribute,
rotate, or retrieve runtime credentials.

### Proposed or pending

- Sealed Secrets is the proposed way to keep Kubernetes secret manifests
  encrypted in Git. A controller, encryption key, and cluster deployment have
  not been configured by this repository.
- A managed secrets service and its provider are **pending a project decision**.
  No provider, service integration, workload identity, or runtime retrieval
  flow is implemented.
- Production deployment targets and ownership of secret creation, access, and
  rotation still need to be agreed.

The CI checks and the proposed Sealed Secrets workflow do **not** by themselves
fulfil the full CI+MS requirement. In particular, the managed-service decision
and its integration remain open. See the [draft ADR](../adr/ADR-006-secrets-management.md).

## 2. Secret handling rules

- Never commit plaintext production credentials, private keys, tokens, or
  populated local environment files.
- Never commit a Sealed Secrets controller private key or other decryption
  key material.
- Do not put credentials in frontend/public build variables, logs, examples,
  test fixtures, or command-line arguments.
- Keep `.env.example` limited to variable names and clearly fake placeholders.
- Grant workloads and operators only the access needed for their role; do not
  share production credentials with local development.
- Do not install controllers, create cloud resources, or deploy credentials
  to a real account without project/instructor approval.

## 3. Local development

Use an ignored `.env` file for local-only configuration. Copy the variable
names from `.env.example`, then populate the values through an approved local
development process. Confirm that Git still ignores the file before working
with real credentials:

```sh
git check-ignore .env
```

Do not use production credentials for local development. If a local value is
accidentally committed or exposed, treat it as compromised: revoke or rotate
it at its source, then remove it from the affected history through the
project's approved process.

Kubernetes is optional for local development. The proposed Kubernetes
workflow below is not required to run the local application.

## 4. Proposed Kubernetes workflow: Sealed Secrets

Use this only after the project has approved a Kubernetes target and installed
the Sealed Secrets controller for that target.

1. Create a Kubernetes Secret manifest locally from approved secret input.
   Do not commit or otherwise publish the plaintext manifest.
2. Seal it with `kubeseal` using the certificate for the intended cluster.
   For example, with a narrowly scoped, ignored `.env.secrets` input file and
   an approved `sealed-secrets-cert.pem`:

   ```sh
   kubectl create secret generic dwms-runtime \
     --namespace dwms \
     --from-env-file=.env.secrets \
     --dry-run=client -o yaml |
     kubeseal --format yaml --cert sealed-secrets-cert.pem \
     > dwms-runtime-sealed.yaml
   ```

   Sealed Secrets are associated with their namespace and name; use the
   intended values before encryption. Never store the certificate's private
   key in the repository.
3. Review the output to confirm it is a `SealedSecret` and contains encrypted
   data rather than plaintext values.
4. Commit only the encrypted `SealedSecret` manifest. The CI validator rejects
   ordinary `kind: Secret` resources in YAML.
5. Apply the manifest through the approved deployment process. The in-cluster
   controller decrypts it into a Kubernetes Secret for the workload.
6. Verify the workload uses the expected secret without printing its value.

The controller's private key is a critical recovery asset and must be
protected and backed up according to an approved operational procedure. Losing
it can make existing sealed manifests undecryptable. Key backup, access, and
recovery procedures must be decided before relying on this approach in
production.

## 5. Rotation and incident response

Rotation is not automated by the current validator or repository workflow.
For an approved deployment:

1. Create a replacement credential at its source.
2. Update the sealed value or managed-service value through the approved
   process.
3. Deploy and verify the replacement without exposing it in logs.
4. Revoke the old credential only after the replacement is confirmed working.
5. Record the rotation without recording the credential itself.

If exposure is suspected, revoke/rotate the credential promptly, assess
affected systems, and follow the project's incident process. Removing a value
from the current tree does not invalidate an exposed credential or remove it
from Git history.

## 6. Managed secrets service: provider decision pending

The team has not selected a managed secrets provider. Candidate services may
include a cloud provider's secrets manager or an approved self-hosted service,
but this list is not a recommendation or commitment. Selection requires
agreement on:

- deployment/cloud target and data residency;
- workload identity and least-privilege access;
- local-development and CI access patterns;
- audit logging, availability, cost, and quota requirements;
- rotation, recovery, and incident ownership; and
- how the choice will be tested without exposing secret values.

Once selected, document the provider and integration in a follow-up ADR and
implement/test the workload and CI access paths. Until then, treat provider
integration as unimplemented.

## 7. CI scope and limitations

The current CI validator scans repository YAML and reports ordinary
Kubernetes `Secret` resources or YAML files it cannot inspect. It does not
scan application code for every possible embedded credential, validate secret
values, provision a managed service, perform secret delivery, or rotate
credentials. Continue to use the project's approved secret-scanning and
deployment controls as they become available.
