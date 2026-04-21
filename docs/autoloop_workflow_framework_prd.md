# PRD: Generic Workflow Runner + Autoloop Workflow Refactor

- **Status:** Draft for handoff
- **Date:** April 21, 2026
- **Audience:** Autoloop maintainers and workflow/runtime contributors

## 1) Vision

Build a generic workflow runner where Autoloop is implemented as a first-class workflow.

The refactor target is:

- preserve user-visible functional outcomes of legacy Autoloop
- allow implementation improvements (for example, structured JSON outputs)
- keep Autoloop workflow code focused on workflow-specific logic
- centralize reusable capabilities in framework modules without overfitting
- ship a fully migrated final codebase with no transitional compatibility/shim code remaining

## 2) Product Objectives

### O1. Generic CLI Surface

CLI should represent stable runtime concepts, not Autoloop internals.

- Keep task/run/workflow orchestration generic.
- Rename `--intent` to `--message`.
- Provide workflow-specific parameter passthrough for options like pairs/phase.

### O2. Functional Equivalence (Not Bit-for-Bit)

Core Autoloop outcomes should remain equivalent for common workflows:

- planning and execution cadence
- artifact generation and progression behavior
- resumability and run continuity

Internal mechanisms may differ when improvements are justified.

### O3. Workflow-Centric Autoloop Implementation

Autoloop workflow script(s) should mostly encode workflow policy:

- criteria flow
- gating behavior
- progression rules
- workflow-level defaults

### O4. Shared Logic in Framework

Framework should own reusable concerns:

- task/run models
- provider abstraction and call execution
- git tracking and commit helpers
- artifact declaration/validation helpers
- optional reusable pair helpers (plan/implement/test patterns as helpers, not hard-coded workflow behavior)

### O5. Complete Migration End State (No Transitional Code)

The delivered result must be fully migrated and complete:

- no temporary shim layers
- no legacy-path fallback branches kept solely for transition
- no dual-architecture runtime paths that preserve old internals
- no TODO-marked migration scaffolding left in production code

If backward compatibility is required, it must exist as intentional product behavior in the final architecture, not as temporary migration code.

## 3) User-Facing CLI Model (Target)

> Specific subcommand names can evolve; semantics should remain.

### Core commands

- `workflow list|describe`
- `task create|list|show`
- `run start|resume|status|logs`

### Core flags (examples)

- `--workspace`
- `--provider`
- `--model`
- `--model-effort`
- `--git/--no-git`
- `--full-auto`

### Task creation/update naming

- Use `--message` (required rename).

### Workflow-specific parameters

Surface workflow knobs via pass-through key/value flags, for example:

- `--wf pairs=plan,implement,test`
- `--wf phase=phase-1`
- `--wf phase_mode=single`

The generic CLI transports these values; workflow validates and interprets them.

## 4) Functional Requirements

### FR1. Boundary Compliance

- Framework modules must not hardcode Autoloop-specific semantics.
- Autoloop workflow modules must consume framework interfaces, not reimplement shared mechanics.

### FR2. Explicit Artifact Contracts

Workflows must declare required artifacts explicitly:

- artifact identifiers
- expected lifecycle (created/updated/validated)
- validation/check rules

Framework should provide shared artifact registry/validation helpers.

### FR3. Control Contract Modernization

Use structured machine-readable control contracts (prefer JSON/object schemas). XML-style control parsing should not be the target control strategy in the migrated architecture.

### FR4. Reusable Pair Helpers

Plan/implement/test pairing can be provided as shared helper primitives, but workflow must choose how to compose them.

### FR5. Run Continuity

Resume and run-state continuity must remain reliable in the final architecture.

### FR6. Architecture Decision Method

For every meaningful design decision (API shape, persistence model, workflow contract, provider abstraction, artifact strategy, etc.), the implementation process must:

1. produce at least **three viable candidate solutions**;
2. evaluate each candidate with explicit criteria (complexity, correctness, extensibility, operability, migration risk, and testability);
3. select the superior candidate for this project and document the rationale.

Decisions must be recorded so reviewers can audit why a choice was made.

## 5) Non-Goals

- lock a specific folder/path layout in this PRD
- enforce byte-for-byte behavioral parity
- prohibit workflow evolution where outcomes stay functionally equivalent

## 6) Quality and Acceptance Criteria

### AC1. CLI

- `--message` is used instead of `--intent` in supported user flows.
- workflow parameters are discoverable and pass-through capable.

### AC2. Separation of Concerns

- Autoloop workflow files are predominantly workflow policy logic.
- shared/runtime logic sits in framework modules and is reusable.

### AC3. Artifact Explicitness

- required artifacts are explicit and validated.

### AC4. Functional Equivalence

For representative tasks, migrated Autoloop produces equivalent operational outcomes to legacy behavior (allowing different internal representations and control formats).

### AC5. Testability

- framework interfaces and workflow behavior have independent test coverage.
- compatibility tests cover key legacy-to-new flow outcomes.

### AC6. No Transitional Runtime Code

- the final codebase contains no migration-only shims/fallback paths/scaffolding.
- all retained compatibility behaviors are intentional first-class features, not temporary bridges.

### AC7. Decision Quality Evidence

- each major design decision includes at least three candidates, weighted evaluation, and explicit final selection rationale.

## 7) Delivery Constraints

- The implementation may be delivered in iterative PRs, but the accepted end state must be a fully migrated architecture with no transitional code remaining.
- Before final acceptance, remove all migration scaffolding and verify only final architecture paths are active.
- Path/folder structure remains intentionally flexible as long as the boundary and quality requirements above are satisfied.
