# ClosedIntelligence

ClosedIntelligence is an open-source, logic-only LLM package and enterprise dapp for field-native chat.

It is built to compete with centralized chat products such as ChatGPT, Claude Chat, Kimi Chat, Z.ai Chat, and Perplexity at the orchestration layer, not by shipping a heavy model. It combines:

- multi-agent ClaudeClaw reasoning,
- Knitweb-style open webs,
- FieldIntelligence field snapshots,
- Lens retrieval over trusted local/open data,
- deterministic answer packets that can be inspected, replayed, and audited.
- internal employee P2P bundles for company knowledge, proposals, tasks, and decisions.

## Core Idea

Most chat products hide the reasoning substrate behind one model endpoint.

ClosedIntelligence treats intelligence as a field operation:

```text
question
  -> lens retrieval over open webs and fields
  -> multi-agent ClaudeClaw passes
  -> evidence-ranked answer packet
  -> optional downstream model/tool adapter
```

The default package uses no heavy model. It gives you the logic layer: roles, retrieval, critique, synthesis, field boundaries, and explainable provenance.

## What It Is

- A small Python package.
- A CLI for local field-native Q&A.
- A Lens abstraction for Knitweb/OpenChem/ChemField-style web snapshots.
- A multi-agent reasoning loop that can run without remote inference.
- A base for later adapters to local models, hosted APIs, browsers, P2P nodes, and domain fields.

## What It Is Not

- Not a model-weight repository.
- Not a private clone of OpenAI, Anthropic, Moonshot, Z.ai, or Perplexity services.
- Not a source of hidden training data.
- Not a claim that deterministic logic alone replaces frontier model quality.

ClosedIntelligence competes by making the control plane open: memory, roles, lenses, fields, provenance, and agent debate are inspectable.

## Quickstart

```sh
python3 -m pip install -e .
closedai answer "What is ClosedIntelligence?" --field examples/open-field.json
```

Output is an answer packet with:

- selected field records,
- agent notes,
- critiques,
- confidence,
- cited record IDs.

## Enterprise DApp

ClosedIntelligence also ships a local-first business dapp for internal P2P use between employees.

It supports:

- employee identities,
- signed knowledge posts,
- proposals and votes,
- task assignments,
- decision records,
- internal P2P bundle export/import,
- Lens answers over the live company field,
- browser dashboard without Node, npm, or external Python web dependencies.

Run it locally:

```sh
closedai dapp init --company "Acme"
closedai dapp serve --port 8787
```

Then open:

```text
http://127.0.0.1:8787/
```

CLI example:

```sh
closedai dapp join alice "Alice Ops" --department ops
closedai dapp state
closedai dapp post <alice-public-id> "Customer handoff" "Customer Alpha needs a risk review." --tag customer --tag risk
closedai dapp answer "What needs risk review?" --pretty
closedai dapp export acme-field-bundle.json
```

The CLI stores bundle files under `.closedintelligence/bundles/` and accepts a filename, not an arbitrary server path. Employees can exchange exported bundles over VPN, shared drives, internal chat, or other approved company channels. Importing a bundle merges signed events into the local field:

```sh
closedai dapp import acme-field-bundle.json
```

The default dapp stores state in `.closedintelligence/company-field.json`, which is gitignored because it contains local mesh material.

## Repository Contract

ClosedIntelligence is open source. It may consume public/open fields from Knitweb, OpenChem, ChemField, and other field repositories.

Closed or permissioned data must be imported explicitly through a local operator policy. The package should never assume it may publish private field data back to an open web.

## Architecture

```text
Field Snapshot
  -> Lens
  -> CandidateSet
  -> ClaudeClaw agents
  -> AnswerPacket
```

DApp flow:

```text
Employee event
  -> signed company field log
  -> optional P2P bundle
  -> peer merge
  -> Lens
  -> ClaudeClaw answer packet
```

Agents in the default ClaudeClaw loop:

- `scout`: finds relevant field records,
- `weaver`: connects records into a candidate answer,
- `skeptic`: identifies gaps and overclaims,
- `steward`: enforces field and privacy boundaries,
- `speaker`: emits the final answer packet.

## Field Snapshot Format

The default Lens accepts either:

```json
{
  "records": [
    {
      "id": "field:example",
      "title": "Example",
      "body": "A field-native record.",
      "tags": ["example"]
    }
  ]
}
```

or a Knitweb-style mapping:

```json
{
  "nodes": {
    "cid:1": {
      "kind": "claim",
      "body": "A woven claim.",
      "tags": ["knitweb"]
    }
  }
}
```

## Development

```sh
python3 -m pip install -e .
PYTHONPATH=src python3 -m unittest discover -s tests
```

## License

Apache License 2.0.
