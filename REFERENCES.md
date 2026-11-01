# References and acknowledgements

This document accompanies [DrVinay/ai-agents-adas-validation](https://github.com/DrVinay/ai-agents-adas-validation), an educational project exploring AI agents for advanced driver-assistance systems (ADAS) validation workflows.

References are grouped by their relationship to the project: technologies used in the implementation, conceptually relevant research and further reading, and automotive/physical AI verification and validation (V&V) context. Inclusion does **not** mean that every publication or documentation page was consulted during development. In particular, the research and standards below are contextual references, not a record of implementation provenance.

## 1. Directly used technologies

The following technologies are part of the project's implementation stack. The links identify their official documentation; they do not assert use of every capability described there. Documentation evolves, so consult the repository's dependency declarations and code for the versions and behavior used by a particular revision.

- **OpenAI Responses API and function calling** — [Responses API reference](https://developers.openai.com/api/reference/responses/overview) · [Function calling guide](https://developers.openai.com/api/docs/guides/function-calling). Interfaces for large language model (LLM) responses and structured tool requests. The application executes the requested functions and returns their results to the model.
- **OpenAI Agents SDK for Python** — [Official documentation](https://openai.github.io/openai-agents-python/). Agent orchestration primitives for connecting models, instructions, and tools.
- **Human-in-the-loop (HITL), human review, and `RunState`** — [Agents SDK HITL documentation](https://openai.github.io/openai-agents-python/human_in_the_loop/). Approval interruptions and run-state handling support pausing a workflow, obtaining a human decision, and resuming execution. Human approval is an oversight mechanism, not proof that an output is correct or safe.
- **Tracing and observability** — [Agents SDK tracing documentation](https://openai.github.io/openai-agents-python/tracing/). Execution traces help inspect model calls, tool activity, and workflow behavior for debugging and review. Observability supports investigation; it does not independently establish correctness or causality.
- **Python** — [Official Python documentation](https://docs.python.org/3/). Language and standard-library reference for the implementation.
- **SQLite** — [Official SQLite documentation](https://www.sqlite.org/docs.html). Embedded relational database reference for SQL-based storage and querying.
- **ChromaDB (Chroma)** — [Official Chroma documentation](https://docs.trychroma.com/docs/overview/introduction). Reference for storing embeddings, documents, and metadata and retrieving relevant information through similarity search and filtering.

## 2. Conceptually relevant research and further reading

These sources help explain the design space. They are not claimed as direct development inputs or as methods reproduced in full by this repository. The Anthropic publications are related reading; their inclusion does not imply use of Anthropic models or tooling.

- **Yao et al. — _ReAct: Synergizing Reasoning and Acting in Language Models_ (2022 preprint; revised 2023).** [Original paper](https://arxiv.org/abs/2210.03629). Introduces interleaving reasoning and actions so that observations can inform subsequent steps. The project's architecture is best described as **ReAct-inspired**, not an exact implementation or reproduction of the paper's prompting, experiments, or results.
- **Anthropic — _Building effective agents_ (2024).** [Original article](https://www.anthropic.com/research/building-effective-agents). Discusses workflows versus agents, simple composable patterns, and tool design. Useful context for explaining orchestration choices; not claimed to have been directly used during development.
- **Anthropic — _Trustworthy agents in practice_ (2026).** [Original article](https://www.anthropic.com/research/trustworthy-agents). Discusses human control, permissions, transparency, and layered safeguards for agent systems. Relevant to guardrails and human review; not claimed to have been directly used during development.
- **OpenAI — _A practical guide to building agents_.** [Original guide (PDF)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf). Practical guidance on selecting agent use cases, orchestration, guardrails, and human intervention. Included as further reading rather than evidence that all recommended practices are implemented.

## 3. Automotive and physical AI V&V: standards and context

These references place the demonstration in a broader engineering context. Citing them does **not** establish standards compliance, certification, scenario-format conformance, or a complete safety case. This section does not claim that the full standards were consulted or implemented during development.

- **ISO 34502:2022 — _Road vehicles — Test scenarios for automated driving systems — Scenario based safety evaluation framework_.** [Official ISO catalogue entry](https://www.iso.org/standard/78951.html). Provides context for scenario-based safety evaluation of automated driving systems. The linked public entry identifies the standard; the full normative text may require purchase or licensed access.
- **ASAM OpenSCENARIO DSL.** [Official standard overview](https://www.asam.net/standards/detail/openscenario-dsl/). A domain-specific language for describing driving scenarios and their behavior, relevant to scenario specification and test generation. This reference does not claim that the project's scenarios are valid OpenSCENARIO DSL artifacts or that the project implements a conforming toolchain.
- **NIST — _AI Risk Management Framework (AI RMF)_.** [Official framework resource](https://www.nist.gov/itl/ai-risk-management-framework). Voluntary guidance for managing AI risks and considering trustworthiness throughout the AI lifecycle. Useful context for documenting limitations, oversight, and evaluation; it is not an automotive certification standard.

## Educational scope and simulated-data disclaimer

This project is an **educational demonstration using simulated data**. Its scenarios, measurements, and generated findings must not be presented as real vehicle test evidence or as evidence of production ADAS/automated-driving performance.

LLM-generated explanations, retrieved material, and agent outputs require human review. Guardrails, HITL approvals, and execution traces support controlled workflows but do not guarantee safety, correctness, or completeness. An observed association or a plausible explanation is not proof of causality.

The project is not a substitute for validated simulation, physical testing, qualified engineering judgment, or a formal safety assurance process. No claim of ISO, ASAM, or NIST compliance, certification, or endorsement is made.

## How to cite this project

Use the repository link when referring to this work:

> DrVinay. _ai-agents-adas-validation_ [Software repository]. GitHub. https://github.com/DrVinay/ai-agents-adas-validation

For reproducibility, include the release tag or full commit SHA you used and your access date. A link to the exact commit is preferable when discussing implementation behavior or results. Cite the original sources separately when drawing on their methods or guidance; citing this repository does not replace attribution to those sources.

---

Source URLs checked: **2026-11-01**. Links point to original publishers or official project documentation. Their inclusion does not imply affiliation or endorsement.
