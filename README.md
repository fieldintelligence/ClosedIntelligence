# ClosedIntelligence

ClosedIntelligence is an open-source, logic-only LLM package for field-native chat.

It is built to compete with centralized chat products such as ChatGPT, Claude Chat, Kimi Chat, Z.ai Chat, and Perplexity at the orchestration layer, not by shipping a heavy model. It combines:

- multi-agent ClaudeClaw reasoning,
- Knitweb-style open webs,
- FieldIntelligence field snapshots,
- Lens retrieval over trusted local/open data,
- deterministic answer packets that can be inspected, replayed, and audited.

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
python3 -m pytest
```

## License

Apache License 2.0.
