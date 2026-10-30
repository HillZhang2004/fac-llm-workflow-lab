# fac LLM Workflow Lab

A hands-on project exploring LLM workflow orchestration, dynamic dependencies, structured outputs, and incremental rebuilding using the `fac` framework.

## What This Project Demonstrates

- Generate a structured essay outline with an LLM.
- Validate the output against a JSON Schema.
- Dynamically create four section-writing tasks from the outline.
- Execute independent LLM tasks concurrently.
- Assemble the generated sections into a final document.
- Reuse existing outputs when inputs have not changed.
- Rebuild dependent outputs when upstream instructions change.

## Project Files

- `fac.yaml` — Workflow configuration and dependencies.
- `style_guide.md` — Instructions for the generated sections.
- `outline.json` — LLM-generated structured outline.
- `sections/` — Dynamically generated essay sections.
- `final.md` — Assembled essay.

## Experiments

The workflow was tested using Groq-hosted LLM inference.

In a repeat execution with unchanged inputs, all targets were reused without new LLM generation.

After modifying the style guide, the four sections were regenerated and the final essay was rebuilt, while the existing outline was reused.

These experiments demonstrate workflow behavior in this example; they are not a comprehensive reliability evaluation.

## Standalone examples

- [Client requirement change impact](examples/client-requirement-change/): an offline, deterministic experiment using pinned `fac` to compare explicit dependencies, complete supplied context, and a deliberately missing dependency. Includes executable tests, generated artifacts, an impact report, and a three-minute demo script.

The standalone example has its own `fac.yaml` and setup instructions; the essay tutorial above continues to run from the repository root.

## Limitations

The generated historical essay is illustrative and has not been fact-checked. Successful execution and structural validation do not guarantee factual correctness.

## Acknowledgments

This project uses [`fac`](https://github.com/mikeizbicki/fac), a workflow orchestration framework developed by Professor Michael Izbicki.

Credit for the underlying framework belongs to Professor Izbicki. This repository contains my own tutorial configuration, generated artifacts, experiments, and observations.
