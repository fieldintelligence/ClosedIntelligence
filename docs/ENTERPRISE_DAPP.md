# Enterprise DApp

ClosedIntelligence can run as an internal company dapp for employee-to-employee intelligence.

It is designed for companies that do not want every operational question, incident note, customer handoff, or internal decision to pass through a centralized external chat product.

## Business Value

ClosedIntelligence adds value by turning internal knowledge work into a local field:

- employees publish signed knowledge records,
- teams open proposals and vote,
- managers assign tasks with context,
- decisions keep their rationale,
- peer bundles can move over approved internal channels,
- Lens answers cite internal field records instead of hallucinating from a hidden context.

## Why P2P Inside A Company

Internal P2P is useful when:

- teams work across offices or devices,
- employees need local-first continuity,
- a central SaaS account is not acceptable for sensitive data,
- the company wants audit trails without sending everything to a model vendor,
- departments need selective sync rather than one global knowledge silo.

## Default Runtime

The default runtime is conservative:

```text
local state file
  -> signed append-only event log
  -> export bundle
  -> import bundle on another employee machine
```

This can run without a server. The browser dapp is a local stdlib HTTP server over the same state file.

## Event Types

Current events:

- `employee.joined`
- `knowledge.posted`
- `proposal.opened`
- `proposal.voted`
- `task.assigned`
- `decision.recorded`
- `peer.trusted`

## Security Model

The bootstrap implementation uses a shared HMAC mesh key for a permissioned company field. That is enough for a local-first MVP and deterministic tests, but production deployments should add an Ed25519 or hardware-backed signing adapter for per-employee public verification.

Private state is not published automatically. Export is an explicit operator action.

## Running The DApp

```sh
closedai dapp init --company "Acme"
closedai dapp serve --port 8787
```

Open:

```text
http://127.0.0.1:8787/
```

## Syncing Employees

On employee A:

```sh
closedai dapp export acme-bundle.json
```

On employee B:

```sh
closedai dapp import acme-bundle.json
```

The merge path verifies event signatures and rejects tampered events.

## Lens Answers

The live company field can be queried:

```sh
closedai dapp answer "Which customer needs risk review?" --pretty
```

The answer packet includes cited record IDs and agent notes from the ClaudeClaw loop.
