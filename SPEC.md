# Service Spec

## Public API

- `GET /health`
- `POST /v1/support/message`

## Supported routes

- `knowledge_qa`
- `status_diagnosis`
- `kyb_review`
- `handoff`

## Runtime guarantees

- Live adapters are preferred for status diagnosis.
- Missing adapters must degrade to documentation-backed guidance.
- Document-review outputs must include evidence references.
- Recommendations are for human review only and do not write final approval decisions.
- Repeated clarification loops escalate to human handoff.

## Platform package requirements

Each package must include:

- `platform.yaml`
- `knowledge/`
- `rules/`
- `schemas/`
- `prompts/`
- `examples/`
- optional `adapters/`

## Acceptance shape

- OpenClaw can install and call the service directly.
- Replacing the platform package changes the active platform behavior.
- Knowledge QA, status diagnosis, and KYB review all run through the same ingress contract.
