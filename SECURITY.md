# Security Policy

ClosedIntelligence is designed to run on local/open field snapshots without hidden model calls.

## Defaults

- The CLI reads local JSON snapshots.
- No remote inference is performed by default.
- No P2P sync is performed by default.
- No private field export is performed by default.
- DApp state is written under `.closedintelligence/` by default and is gitignored.

## Sensitive Inputs

Treat private prompts, field records, peer metadata, credentials, and unpublished webs as sensitive.

Do not wire ClosedIntelligence to publish private field data to an open web without a separate human-reviewed policy.

## DApp Mesh Key

The bootstrap dapp uses a shared HMAC mesh key for a permissioned internal field. Keep the state file and mesh key private. For production, prefer a per-employee public-key signer and a managed key store.

## Reporting

Use GitHub private vulnerability reporting if enabled for the repository, or contact the FieldIntelligence maintainers through the organization.
