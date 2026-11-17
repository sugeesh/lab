<!--
Sync Impact Report
==================
Version change: (unversioned template) → 1.0.0
Bump rationale: Initial ratification; all placeholders replaced with concrete governance.

Modified principles (template slot → new title):
  - PRINCIPLE_1 → I. Test-Driven Development (NON-NEGOTIABLE)
  - PRINCIPLE_2 → II. Clean Code
  - PRINCIPLE_3 → III. Usability First
  - PRINCIPLE_4 → IV. YAGNI (You Aren't Gonna Need It)
  - PRINCIPLE_5 → V. Human-Crafted Interface (No "AI Look")

Added sections:
  - Quality Gates (SECTION_2)
  - Development Workflow (SECTION_3)
  - Governance (filled)

Removed sections: none

Templates requiring updates: none modified (out of scope for this command;
  plan/spec/tasks templates read the constitution at runtime).
  ⚠ Review .specify/templates/plan-template.md "Constitution Check" gates when
    running /speckit-plan to ensure they map to Principles I–V.

Deferred TODOs: none
-->

# URL Shortener Constitution

## Core Principles

### I. Test-Driven Development (NON-NEGOTIABLE)

- Every behavior change MUST begin with a failing automated test that expresses the
  expected behavior (Red), followed by the minimal code to pass it (Green), followed by
  refactoring with all tests still passing (Refactor).
- Production code MUST NOT be committed without a test that would fail if that code were
  removed or broken.
- Bug fixes MUST include a regression test that reproduces the bug before the fix.
- Tests MUST be fast, deterministic, and independent of execution order; flaky tests MUST
  be fixed or removed before merge, never ignored.
- Tests MUST verify observable behavior (inputs/outputs, HTTP responses, rendered UI),
  not private implementation details.

**Rationale**: Writing tests first forces clear requirements, produces a safety net for
refactoring, and keeps the design driven by real usage rather than speculation.

### II. Clean Code

- Names (variables, functions, modules, routes) MUST reveal intent; abbreviations are
  allowed only when they are domain-standard (e.g., `url`, `id`).
- Functions MUST do one thing; a function that needs a comment to explain *what* it does
  MUST be split or renamed instead. Comments are reserved for *why*.
- Duplicated logic MUST be extracted once it appears a third time (Rule of Three).
- Dead code, commented-out code, and unused dependencies MUST NOT be merged.
- Code MUST pass the project's formatter and linter with zero warnings.
- Errors MUST be handled explicitly; silent catch-and-ignore is prohibited.

**Rationale**: Code is read far more often than it is written. Readable, small, honest
code keeps the cost of every future change low.

### III. Usability First

- Core flows (shorten a URL, copy the short link, follow a short link) MUST be completable
  without documentation and in the fewest possible steps.
- Every user action MUST give immediate, visible feedback (success, progress, or a
  specific error message stating what went wrong and how to fix it).
- Error messages MUST be written in plain language; stack traces, codes without
  explanation, and generic "Something went wrong" messages MUST NOT be shown to users.
- Interfaces MUST be keyboard-operable, meet WCAG 2.1 AA contrast, and work at phone
  width (≥ 320px) without horizontal scrolling.
- API responses MUST use consistent, documented shapes and correct HTTP status codes.

**Rationale**: A URL shortener exists to save people time; any friction defeats its
purpose.

### IV. YAGNI (You Aren't Gonna Need It)

- Only features required by an approved spec's user stories MUST be built; speculative
  features, configuration options, and extension points are prohibited.
- Abstractions (interfaces, factories, plugin layers, generic base classes) MUST NOT be
  introduced until at least two concrete use cases exist.
- New dependencies MUST be justified in the plan by a concrete current need that cannot
  be met reasonably with the standard library or existing dependencies.
- The simplest design that passes the tests MUST be chosen; added complexity MUST be
  recorded with its justification in the plan's Complexity Tracking section.

**Rationale**: Unbuilt features cost nothing to maintain. Simplicity keeps the codebase
small enough to understand and change quickly.

### V. Human-Crafted Interface (No "AI Look")

User interfaces MUST look deliberately designed for this product, not like generic
AI-generated output. Specifically:

- UI MUST NOT use the stock "AI aesthetic": purple/blue/pink gradient backgrounds or
  gradient text, glowing borders, glassmorphism, sparkle (✨) or magic-wand iconography,
  or decorative emoji in headings, buttons, or labels.
- Copy MUST be plain, specific, and brief. Marketing filler ("Unleash", "Seamless",
  "Supercharge", "Effortlessly", "Revolutionize") and exclamation-heavy tone are
  prohibited.
- Layout MUST NOT default to the generic template of centered hero + three feature cards
  + rounded shadowed cards everywhere; layout choices MUST follow from the actual task.
- A small, explicit design system (color tokens, type scale, spacing scale) MUST be
  defined once and used consistently; ad-hoc one-off values are not allowed.
- Visual decoration MUST serve function (hierarchy, state, affordance); purely ornamental
  elements MUST be removed.

**Rationale**: Generic AI-styled interfaces feel untrustworthy and interchangeable. A
restrained, purposeful interface builds trust and supports Usability (Principle III).

## Quality Gates

Every change MUST pass these gates before merge:

1. All automated tests pass; new behavior is covered by tests written first (Principle I).
2. Formatter and linter report zero errors or warnings (Principle II).
3. Core user flows verified manually or via end-to-end tests at desktop and phone widths,
   including keyboard-only navigation (Principle III).
4. No unrequested features, unused abstractions, or unjustified dependencies
   (Principle IV).
5. UI changes reviewed against the Principle V checklist; any violation blocks merge.

## Development Workflow

- Work follows the Spec Kit flow: `/speckit-specify` → `/speckit-clarify` (when needed) →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`.
- Each plan MUST include a Constitution Check against Principles I–V before design work
  and again after design.
- Tasks MUST be ordered so that test tasks precede the implementation tasks they cover.
- Commits SHOULD be small and focused, each leaving the test suite green.
- Code review MUST explicitly confirm compliance with this constitution; reviewers MUST
  reject changes that violate a MUST rule unless an amendment has been ratified.

## Governance

- This constitution supersedes all other practices, conventions, and preferences in this
  project. Where guidance conflicts, the constitution wins.
- Amendments MUST be made through `/speckit-constitution`, documented with a Sync Impact
  Report, and recorded with an updated version and amendment date.
- Versioning follows semantic versioning:
  - MAJOR: removal or backward-incompatible redefinition of a principle or governance rule.
  - MINOR: a new principle or section, or materially expanded guidance.
  - PATCH: clarifications, wording, and typo fixes with no semantic change.
- Any deviation from a MUST rule requires a written justification in the relevant plan's
  Complexity Tracking section and reviewer approval.
- Compliance is reviewed at every plan (Constitution Check), every code review, and
  whenever `/speckit-analyze` is run.

**Version**: 1.0.0 | **Ratified**: 2026-11-17 | **Last Amended**: 2026-11-17
