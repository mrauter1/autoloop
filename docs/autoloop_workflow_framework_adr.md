# ADR: Workflow-First Architecture with a Reusable Runner Framework

- **Status:** Proposed
- **Date:** April 21, 2026
- **Decision Scope:** Architectural direction (not final package layout)

## Context

Autoloop has proven workflow value, but current implementation concentrates framework behavior and workflow behavior in overlapping areas. This makes it harder to:

1. Keep `main.py` as a true generic CLI entrypoint.
2. Reuse shared runtime capabilities across workflows.
3. Evolve Autoloop-specific behavior without touching core runtime internals.

The objective is not bit-for-bit parity with legacy Autoloop. The objective is **functional equivalence**, with room for better implementations (for example, structured JSON control outputs instead of XML tag parsing).

## Decision

Adopt a **workflow-first plugin model over a generic runner framework**:

- The **framework** owns reusable runtime primitives.
- The **workflow** owns business logic and policy.
- The **CLI** is generic and routes to the selected workflow.

Path and folder structure are intentionally not fixed in this ADR. Teams may choose the concrete layout that best fits maintainability and testability, as long as boundary contracts are preserved.

## Architectural Boundaries

### 1) Generic framework responsibilities

The framework should provide only broadly reusable capabilities:

- task + run lifecycle primitives
- provider abstraction and provider call execution
- git tracking/commit helpers
- event/state persistence
- artifact declaration and validation utilities
- optional reusable pair/orchestration helpers

The framework should avoid direct knowledge of Autoloop semantics.

### 2) Workflow responsibilities (Autoloop)

Autoloop workflow should contain mostly workflow-specific logic:

- workflow policy and flow control
- Autoloop criteria, gating, and progression decisions
- interpretation of workflow-level control signals
- workflow-specific defaults and prompts/templates

### 3) CLI responsibilities

CLI should stay generic and stable:

- workflow discovery/selection
- task and run commands
- core runtime options
- workflow-specific parameter pass-through

CLI naming update: use `--message` (not `--intent`) for task creation and run bootstrap commands.

### 4) Session model

Session behavior is workflow-defined policy unless explicitly promoted into framework contracts later. CLI should not expose session commands at this stage.

## Design Direction (Non-prescriptive)

The following are directionally preferred but not mandatory implementation details:

1. Use structured outputs (JSON schemas / typed payloads) for control contracts where possible.
2. Keep plan/implement/test pair concepts reusable as helpers when useful.
3. Generalize concepts like `phase_plan` into shared abstractions when they represent reusable ideas (for example: workboard, criteria board, checkpoint list).
4. Keep required artifacts explicit and machine-checkable at workflow boundaries.

## Consequences

### Positive

- clearer separation of concerns
- easier onboarding for new workflows
- more reliable long-term maintainability
- better testability at framework vs workflow layers

### Trade-offs

- migration requires temporary compatibility layers
- some existing code paths will be reorganized and retested
- teams must define and enforce interface contracts carefully

## Non-goals

- enforcing a specific folder/path tree in this decision
- mandating parity of every internal mechanism with legacy code
- freezing protocol format to legacy XML controls

## Acceptance Signals

This ADR is considered successfully implemented when:

1. `main.py` is mostly CLI/router logic.
2. Autoloop workflow file(s) are mostly workflow policy logic.
3. Shared capabilities are implemented in framework modules without overfitting to Autoloop internals.
4. Required artifacts are explicit, declared, and validated.
5. Functional outcomes are equivalent to legacy Autoloop for core use cases, even if internal representations differ.
