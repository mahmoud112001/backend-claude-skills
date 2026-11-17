# Backend Claude Skills Pack

A focused collection of Claude Code skills and agents for backend design, implementation practices, code health, and skill maintenance. The skills are in [`backend-skills-pack/skills/`](backend-skills-pack/skills/); the installer copies them and the accompanying agents into a project's `.claude` directory.

## What is included

The pack has **18 skills** and **8 agents**. Skills can start automatically when a request matches their description, or be invoked by name. Four skills are manual-only: `backend-design-team`, `dead-code-cleaner`, `skill-creator`, and `skill-security-audit`.

### Backend design team

Use `/backend-design-team start <prototype-path>` to design a backend from a prototype, specification, UI, or existing code. The orchestrator coordinates phases 0–8, checks phase outputs, records progress, and can resume with `/backend-design-team resume`.

| Phase | Skill | Purpose |
|---|---|---|
| 0 | [`project-understanding`](backend-skills-pack/skills/project-understanding/SKILL.md) | Reads the prototype and repository; drafts a project profile and requirements brief. Missing facts are recorded rather than guessed. |
| 1 | [`ddd-strategic`](backend-skills-pack/skills/ddd-strategic/SKILL.md) | Defines subdomains, bounded contexts, context relationships, and shared domain language. |
| 2 | [`ddd-tactical`](backend-skills-pack/skills/ddd-tactical/SKILL.md) | Models one context's aggregates, invariants, commands, events, policies, and read models. |
| 3–4 | [`db-design-erd`](backend-skills-pack/skills/db-design-erd/SKILL.md) | Maps the design to storage, constraints, and indexes, then draws the entity-relationship diagram. |
| 5 | [`design-diagrams`](backend-skills-pack/skills/design-diagrams/SKILL.md) | Draws use-case, module, and key-flow diagrams from the design. |
| 6 | [`api-endpoints`](backend-skills-pack/skills/api-endpoints/SKILL.md) | Defines API operations, errors, idempotency, pagination, and contracts. |
| 7 | [`design-review-fix`](backend-skills-pack/skills/design-review-fix/SKILL.md) | Independently reviews the design for concrete bugs, rule violations, and missing requirements. |
| 8 | [`design-docs-organizer`](backend-skills-pack/skills/design-docs-organizer/SKILL.md) | Organizes the design files, fixes links, and creates a reading-order index. |

The orchestrator is [`backend-design-team`](backend-skills-pack/skills/backend-design-team/SKILL.md). Its eight agents—project-reader, strategic-designer, tactical-designer, db-designer, diagram-writer, api-designer, design-reviewer, and doc-librarian—perform the corresponding phases.

### Coding and review practices

| Skill | Purpose |
|---|---|
| [`reuse-first`](backend-skills-pack/skills/reuse-first/SKILL.md) | Checks existing code, standard libraries, installed packages, and a small set of candidate libraries before recommending whether to reuse, add, or write a solution. |
| [`architecture-conformance`](backend-skills-pack/skills/architecture-conformance/SKILL.md) | Checks code against architecture rules found in a file you specify; it does not invent rules. |
| [`dead-code-cleaner`](backend-skills-pack/skills/dead-code-cleaner/SKILL.md) | Reports unused and duplicate code, classifies candidates, and offers a guarded apply workflow for safe deletions. Manual-only. |
| [`test-driven-development`](backend-skills-pack/skills/test-driven-development/SKILL.md) | Guides feature and bug-fix work through a failing test, the smallest implementation, and refactoring. |
| [`verification-before-completion`](backend-skills-pack/skills/verification-before-completion/SKILL.md) | Requires fresh, relevant command output before claiming work or tests are complete. |
| [`dispatching-parallel-agents`](backend-skills-pack/skills/dispatching-parallel-agents/SKILL.md) | Delegates genuinely independent tasks and verifies their combined results. |
| [`model-router`](backend-skills-pack/skills/model-router/SKILL.md) | Recommends a Claude model alias and explains the supported ways to switch models. |

### Pack maintenance

| Skill | Purpose |
|---|---|
| [`skill-creator`](backend-skills-pack/skills/skill-creator/SKILL.md) | Creates or improves a skill and evaluates its triggering behavior. Manual-only. |
| [`skill-security-audit`](backend-skills-pack/skills/skill-security-audit/SKILL.md) | Reviews a third-party skill or plugin without running it and records a verdict with file-and-line evidence. Manual-only. |

## Install

From the repository root, preview the changes first. The installer is a dry run unless you pass the apply option.

**Windows PowerShell:**

```powershell
powershell -ExecutionPolicy Bypass -File backend-skills-pack\scripts\install.ps1 -Project C:\path\to\your\project
powershell -ExecutionPolicy Bypass -File backend-skills-pack\scripts\install.ps1 -Project C:\path\to\your\project -Apply
```

**Bash:**

```bash
bash backend-skills-pack/scripts/install.sh --project /path/to/your/project
bash backend-skills-pack/scripts/install.sh --project /path/to/your/project --apply
```

To install for all projects under your user account, use `-User` (PowerShell) or `--user` (Bash) instead of `-Project` or `--project`. The installer copies skills and agents; it does not install dependencies, download files, or change Claude settings. Differing existing copies are backed up. Start a new Claude Code session, or run `/clear`, after installing.

## Use

Automatic skills are selected when a request matches their description. You can also invoke a skill directly by name. For example:

```text
/backend-design-team start prototype/
/backend-design-team resume
/dead-code-cleaner report src
/skill-security-audit <folder-or-repo-url@sha>
```

The four manual-only skills run only when explicitly invoked. In particular, `dead-code-cleaner` has separate report and apply steps; review its report before applying changes.

## Repository map

- [`backend-skills-pack/README.md`](backend-skills-pack/README.md) — detailed guide, workflows, model policy, security policy, and skill authoring instructions.
- [`backend-skills-pack/skills/`](backend-skills-pack/skills/) — skill definitions and their supporting scripts or references.
- [`backend-skills-pack/agents/`](backend-skills-pack/agents/) — the eight phase agents used by the design team.
- [`backend-skills-pack/MANIFEST.json`](backend-skills-pack/MANIFEST.json) — skill and agent metadata, sources, models, and token estimates.
- [`backend-skills-pack/AUDIT.md`](backend-skills-pack/AUDIT.md) and [`backend-skills-pack/THIRD-PARTY-NOTICES.md`](backend-skills-pack/THIRD-PARTY-NOTICES.md) — audit and licensing information.
- [`backend-skills-pack/TOKEN-REPORT.md`](backend-skills-pack/TOKEN-REPORT.md) — estimated prompt-listing cost and methodology.
- [`backend-skills-pack/VERIFICATION.md`](backend-skills-pack/VERIFICATION.md) — the latest independent verification report and outstanding findings.
- [`backend-skills-pack/scripts/`](backend-skills-pack/scripts/) — installation, validation, scanning, and report-generation tools.

## Verification status

The latest independent report, dated 2026-11-17, records **NO-GO** with 16 failures and 9 open problems. Review [`VERIFICATION.md`](backend-skills-pack/VERIFICATION.md) before relying on or redistributing the pack; this overview does not mean those findings have been resolved.
