# ClosedIntelligence Architecture

ClosedIntelligence is a control-plane package for field-native intelligence.

It avoids shipping a heavy model in the core package. Instead, it makes the reasoning loop inspectable:

```text
Open web or field snapshot
  -> Lens retrieval
  -> ClaudeClaw multi-agent logic
  -> AnswerPacket
  -> optional model, browser, P2P, or UI adapter
```

## Lens

The Lens is read-only. It can consume OpenChem, ChemField, Knitweb, or other web/field snapshots and turn them into candidate records.

The default implementation accepts two shapes:

- `records[]`, a direct FieldIntelligence record list,
- `nodes{}`, a Knitweb-style content-addressed web snapshot.

## ClaudeClaw

ClaudeClaw is the default role loop:

- `scout` retrieves records,
- `weaver` connects records,
- `skeptic` checks missing terms and overclaims,
- `steward` enforces field/privacy boundaries,
- `speaker` emits the answer.

This is intentionally logic-only. Hosted or local LLM adapters can be added later without changing the field contract.

## Field Boundary

ClosedIntelligence may read open fields and local fields. It must not publish private field state unless an explicit adapter and human policy allow it.

The default CLI only reads JSON snapshots and writes answer packets to stdout.

## Enterprise DApp Layer

The dapp layer adds an internal company field:

```text
employee action
  -> SignedEvent
  -> CompanyField event DAG
  -> P2P bundle
  -> peer merge
  -> Lens records
  -> ClaudeClaw answer
```

This layer deliberately starts as local-first P2P bundle exchange rather than a mandatory always-on server. Companies can run it over VPN, shared drives, internal chat, or a future peer transport adapter.

## Signed Events

`CompanyField` stores signed events for:

- employee joins,
- knowledge posts,
- proposals,
- votes,
- tasks,
- decisions,
- trusted peers.

The default signer uses an HMAC mesh key so the MVP works with Python's standard library. The event shape is designed so an Ed25519 signer can replace HMAC in production without changing the dapp API.
