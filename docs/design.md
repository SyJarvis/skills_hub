# skills_hub Design

`skills_hub` is a reusable skill management repository for Codex, OpenCode, and other agent-based development tools.

The goal of this repository is not just to collect prompts. Instead, it is designed as a long-term **agent skill hub** that supports:

* reusable agent workflows
* structured `SKILL.md` files
* fast local installation
* project-level skill sharing
* searchable documentation
* versioned skill maintenance
* compatibility with Codex, OpenCode, and future agent tools

## 1. Design Goal

`skills_hub` should become a personal or team-level capability library.

A normal prompt is temporary.
A skill is reusable.
A skill hub is a structured knowledge and workflow system.

The repository should allow users to:

1. collect useful skills in one place
2. install skills quickly into local agent tools
3. read documentation without opening every skill folder
4. reuse skills across different projects
5. maintain skills with versioning, testing, and metadata
6. support both global and project-scoped installation

## 2. Core Concept

Each skill is an independent folder under `skills/`.

Every skill must contain a `SKILL.md` file.

A skill can also contain optional supporting files:

* `references/` for long-form documentation
* `scripts/` for deterministic helper tools
* `assets/` for templates, images, examples, or static resources
* `tests/` for example prompts and expected behavior

The `SKILL.md` file is the main entry point for agent tools. It describes what the skill does, when it should be used, and how the agent should execute the workflow.

## 3. Repository Structure

Recommended structure:

```text
skills_hub/
├── README.md
├── AGENTS.md
├── LICENSE
├── catalog.json
├── install.sh
├── skills/
│   ├── pr-review/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   └── review-checklist.md
│   │   ├── scripts/
│   │   │   └── collect_diff.py
│   │   ├── assets/
│   │   │   └── pr-template.md
│   │   └── tests/
│   │       ├── sample_prompt.md
│   │       └── expected_behavior.md
│   │
│   ├── repo-analysis/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── tests/
│   │
│   ├── paper-reading/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── tests/
│   │
│   └── markdown-polish/
│       ├── SKILL.md
│       ├── references/
│       └── tests/
│
├── profiles/
│   ├── codex/
│   │   └── README.md
│   ├── opencode/
│   │   └── README.md
│   └── common/
│       └── README.md
│
├── docs/
│   ├── index.md
│   ├── skills/
│   │   ├── pr-review.md
│   │   ├── repo-analysis.md
│   │   ├── paper-reading.md
│   │   └── markdown-polish.md
│   └── guide/
│       ├── install.md
│       ├── write-skill.md
│       ├── naming.md
│       └── compatibility.md
│
└── tools/
    ├── validate_skills.py
    ├── generate_catalog.py
    └── sync_docs.py
```

## 4. Directory Responsibilities

### 4.1 `skills/`

This is the most important directory.

Each subdirectory under `skills/` is a standalone skill package.

Example:

```text
skills/pr-review/
├── SKILL.md
├── references/
├── scripts/
├── assets/
└── tests/
```

A skill should be focused. It should solve one clear workflow.

Good examples:

* `pr-review`
* `repo-analysis`
* `paper-reading`
* `experiment-design`
* `markdown-polish`
* `llm-infra-analysis`

Bad examples:

* `coding`
* `research`
* `everything-agent`
* `my-helper`

A skill should not become a vague prompt collection.

### 4.2 `docs/`

The `docs/` directory is for human-readable documentation.

The documentation should explain:

* what each skill is for
* how to install it
* how to invoke it
* examples of usage
* compatibility notes
* maintenance rules

The documentation should not replace `SKILL.md`.

The relationship should be:

```text
SKILL.md  -> for agents
docs/     -> for humans
```

### 4.3 `catalog.json`

`catalog.json` is the machine-readable index of all skills.

It allows scripts, docs, and agents to quickly understand what skills exist.

Example:

```json
{
  "name": "skills_hub",
  "version": "0.1.0",
  "skills": [
    {
      "name": "pr-review",
      "path": "skills/pr-review",
      "category": "code-review",
      "description": "Review pull requests, inspect diffs, identify bugs, risky changes, missing tests, and produce actionable review comments.",
      "compatibility": ["codex", "opencode"],
      "stability": "stable",
      "tags": ["git", "pr", "review", "test"]
    },
    {
      "name": "paper-reading",
      "path": "skills/paper-reading",
      "category": "research",
      "description": "Read research papers, extract contributions, methods, assumptions, limitations, and implementation ideas.",
      "compatibility": ["codex", "opencode"],
      "stability": "beta",
      "tags": ["paper", "research", "markdown"]
    }
  ]
}
```

The catalog can be used to:

* generate README tables
* generate docs index pages
* filter skills by tag or category
* install selected skills
* validate skill metadata
* help agents discover available capabilities

### 4.4 `install.sh`

`install.sh` is used to quickly install skills into global or project-level locations.

It should support:

```bash
./install.sh --all
./install.sh pr-review
./install.sh pr-review --link
./install.sh pr-review --project .
./install.sh pr-review --target opencode
./install.sh --category research
./install.sh --stable-only
```

Recommended default target:

```text
~/.agents/skills/
```

Recommended project target:

```text
./.agents/skills/
```

Optional OpenCode-specific target:

```text
~/.config/opencode/skills/
```

Soft-link installation is strongly recommended during development:

```bash
./install.sh pr-review --link
```

This allows the installed skill to update automatically when the repository is updated.

### 4.5 `AGENTS.md`

`AGENTS.md` tells agent tools how to maintain this repository.

It should contain repository-level rules, not skill-level details.

Recommended content:

````md
# AGENTS.md

This repository is a skill hub for Codex, OpenCode, and compatible agent-based tools.

## Repository rules

- Each skill must live in `skills/<skill-name>/`.
- Each skill must contain a `SKILL.md` file.
- Skill names must use lowercase kebab-case.
- Each skill should solve one focused workflow.
- Do not create broad or vague skills.
- Keep skill descriptions clear and trigger-oriented.
- Add long documentation to `references/`, not directly into `SKILL.md`.
- Add deterministic helper logic to `scripts/`.
- Update `catalog.json` when adding, renaming, or removing skills.
- Update `docs/skills/` when changing user-facing behavior.

## Validation

Before committing, run:

```bash
python tools/validate_skills.py
python tools/generate_catalog.py
python tools/sync_docs.py
````

## Skill quality standard

A good skill must define:

1. what it does
2. when to use it
3. required inputs
4. execution workflow
5. output format
6. constraints
7. examples

````

## 5. Skill Package Standard

Each skill should follow this structure:

```text
skills/<skill-name>/
├── SKILL.md
├── references/
├── scripts/
├── assets/
└── tests/
````

Only `SKILL.md` is required.

Other directories are optional.

### 5.1 `SKILL.md`

`SKILL.md` is the main skill file.

Recommended template:

````md
---
name: pr-review
description: Review pull requests, inspect diffs, identify bugs, risky changes, missing tests, and produce actionable review comments. Use when asked to review a PR, diff, patch, or code change.
license: MIT
compatibility: codex, opencode
metadata:
  version: "0.1.0"
  category: code-review
  stability: stable
  tags:
    - git
    - pr
    - review
    - test
---

# PR Review Skill

## What this skill does

This skill helps the agent review code changes with a focus on correctness, maintainability, tests, and risk.

## When to use

Use this skill when the user asks to:

- review a pull request
- analyze a git diff
- check a patch
- find bugs in recent changes
- suggest missing tests

## Inputs

Expected inputs:

- repository path
- git diff, branch name, or PR URL
- optional review focus

## Workflow

1. Inspect the changed files.
2. Understand the purpose of the change.
3. Check correctness risks.
4. Check test coverage.
5. Check maintainability and API compatibility.
6. Produce review comments grouped by severity.

## Output format

Return:

1. Summary
2. Blocking issues
3. Non-blocking suggestions
4. Missing tests
5. Final recommendation

## Constraints

- Do not rewrite the entire PR unless explicitly asked.
- Prefer precise review comments.
- Always separate blocking issues from suggestions.
- Do not invent files or behavior that were not inspected.

## Examples

User request:

```text
Use the pr-review skill to review the current git diff.
````

Expected behavior:

```text
The agent should inspect the diff, identify correctness risks, check tests, and produce structured review comments.
```

````

### 5.2 `references/`

Use `references/` for longer background documents.

Examples:

```text
references/
├── review-checklist.md
├── architecture-rules.md
└── testing-guidelines.md
````

Do not put very long documents directly into `SKILL.md`.

The skill should reference them only when needed.

### 5.3 `scripts/`

Use `scripts/` for deterministic helper tools.

Examples:

```text
scripts/
├── collect_diff.py
├── summarize_tree.py
└── extract_symbols.py
```

Scripts are useful when the workflow needs repeatable behavior.

For example:

* collecting git diff
* listing changed files
* generating repository tree
* extracting markdown headings
* validating JSON or YAML
* formatting output files

### 5.4 `assets/`

Use `assets/` for static files.

Examples:

```text
assets/
├── pr-template.md
├── report-template.md
└── diagram-example.png
```

### 5.5 `tests/`

Use `tests/` for example prompts and expected behavior.

Examples:

```text
tests/
├── sample_prompt.md
├── expected_behavior.md
└── fixture_diff.patch
```

This does not need to be complex at the beginning.

The goal is to make skill behavior easier to maintain.

## 6. Naming Convention

Skill names should use lowercase kebab-case.

Good:

```text
pr-review
repo-analysis
paper-reading
experiment-design
markdown-polish
llm-infra-analysis
vla-paper-reading
```

Bad:

```text
PRReview
repo_analysis
Paper Reading
my skill
general-helper
```

Rules:

1. Use lowercase.
2. Use `-` between words.
3. Keep the name short.
4. Avoid vague names.
5. Prefer workflow-based names.

## 7. Skill Categories

Recommended categories:

```text
code-review
repo-analysis
research
writing
llm-infra
robotics
diffusion
training
debugging
documentation
```

Initial skill candidates:

```text
skills/
├── pr-review/
├── repo-analysis/
├── paper-reading/
├── markdown-polish/
├── experiment-design/
├── llm-infra-analysis/
├── training-framework-design/
├── speculative-decoding-analysis/
├── diffusion-model-analysis/
└── vla-paper-reading/
```

For this repository, categories should live in metadata instead of physical nested folders.

Recommended:

```text
skills/pr-review/
skills/paper-reading/
skills/llm-infra-analysis/
```

Not recommended:

```text
skills/code-review/pr-review/
skills/research/paper-reading/
skills/llm-infra/llm-infra-analysis/
```

Flat skill paths are easier to install, link, and maintain.

## 8. Installation Design

### 8.1 Global Installation

Global installation makes skills available across projects.

Target:

```text
~/.agents/skills/
```

Example:

```bash
./install.sh pr-review --link
```

Result:

```text
~/.agents/skills/pr-review -> ~/skills_hub/skills/pr-review
```

### 8.2 Project Installation

Project installation makes skills available only inside a specific repository.

Target:

```text
./.agents/skills/
```

Example:

```bash
./install.sh pr-review --project . --link
```

Result:

```text
./.agents/skills/pr-review -> ~/skills_hub/skills/pr-review
```

This is useful when a project needs its own skill set.

### 8.3 Tool-Specific Installation

OpenCode-specific target:

```text
~/.config/opencode/skills/
```

Example:

```bash
./install.sh pr-review --target opencode --link
```

However, the recommended default should remain:

```text
~/.agents/skills/
```

This keeps the hub more tool-agnostic.

## 9. Suggested `install.sh` Behavior

The installer should support:

```bash
./install.sh <skill-name>
./install.sh <skill-name> --link
./install.sh <skill-name> --copy
./install.sh <skill-name> --project <path>
./install.sh <skill-name> --target codex
./install.sh <skill-name> --target opencode
./install.sh --all
./install.sh --category <category>
./install.sh --tag <tag>
./install.sh --stable-only
```

Default behavior:

```bash
./install.sh pr-review
```

Should copy or link:

```text
skills/pr-review/
```

To:

```text
~/.agents/skills/pr-review/
```

Recommended development behavior:

```bash
./install.sh pr-review --link
```

Recommended team/project behavior:

```bash
./install.sh pr-review --project . --copy
```

## 10. Documentation Design

The `docs/` directory should be designed as a small documentation site.

Recommended structure:

```text
docs/
├── index.md
├── guide/
│   ├── install.md
│   ├── write-skill.md
│   ├── naming.md
│   └── compatibility.md
├── skills/
│   ├── pr-review.md
│   ├── repo-analysis.md
│   ├── paper-reading.md
│   └── markdown-polish.md
└── categories/
    ├── code-review.md
    ├── research.md
    ├── llm-infra.md
    └── robotics.md
```

Each skill documentation page should include:

````md
# pr-review

## Purpose

Briefly explain what this skill is for.

## When to use

List typical use cases.

## Installation

```bash
./install.sh pr-review --link
````

## Example prompts

```text
Use the pr-review skill to review the current git diff.
```

## Output

Explain the expected output format.

## Files

* `skills/pr-review/SKILL.md`
* `skills/pr-review/references/review-checklist.md`

````

Documentation pages should be generated from `catalog.json` where possible.

## 11. README Design

The root `README.md` should be short and practical.

Recommended structure:

```md
# skills_hub

A reusable skills hub for Codex, OpenCode, and agent-based workflows.

## Quick install

```bash
git clone https://github.com/<your-name>/skills_hub.git ~/.skills_hub
cd ~/.skills_hub
./install.sh pr-review --link
````

## Install all skills

```bash
./install.sh --all --link
```

## Use with Codex

Install skills to:

```text
~/.agents/skills/
```

Then use:

```text
Use the pr-review skill to review this diff.
```

## Use with OpenCode

Install skills to:

```text
~/.agents/skills/
```

Or:

```text
~/.config/opencode/skills/
```

Then use:

```text
Use the repo-analysis skill to analyze this codebase.
```

## Skill list

| Skill         | Category      | Stability | Description                      |
| ------------- | ------------- | --------- | -------------------------------- |
| pr-review     | code-review   | stable    | Review pull requests and diffs   |
| repo-analysis | repo-analysis | beta      | Analyze repository architecture  |
| paper-reading | research      | stable    | Read and analyze research papers |

## Authoring guide

See `docs/guide/write-skill.md`.

````

## 12. Versioning Strategy

The repository should have its own version:

```text
skills_hub version: v0.1.0
````

Each skill should also have its own version in metadata:

```yaml
metadata:
  version: "0.1.0"
  stability: beta
```

Recommended stability levels:

```text
stable        reliable and frequently used
beta          usable but still being improved
experimental  early idea, not guaranteed to work well
deprecated    kept for compatibility, not recommended
```

Versioning rules:

1. Update skill version when behavior changes.
2. Update repository version when many skills are added or changed.
3. Mark unstable skills as `beta` or `experimental`.
4. Do not delete old skills immediately; mark them as `deprecated` first.

## 13. Validation Rules

A validation script should check:

1. Every skill has `SKILL.md`.
2. Every skill name is lowercase kebab-case.
3. Every `SKILL.md` has frontmatter.
4. Every skill has `name`.
5. Every skill has `description`.
6. The skill folder name matches the metadata name.
7. `catalog.json` contains all skills.
8. No missing paths exist in `catalog.json`.
9. No duplicate skill names exist.
10. Stability value is valid.

Example command:

```bash
python tools/validate_skills.py
```

## 14. Catalog Generation

`tools/generate_catalog.py` should scan all skills and generate `catalog.json`.

Expected behavior:

1. Scan `skills/*/SKILL.md`.
2. Parse YAML frontmatter.
3. Extract name, description, compatibility, category, stability, tags, and version.
4. Generate `catalog.json`.
5. Sort skills by name.

Example:

```bash
python tools/generate_catalog.py
```

## 15. Docs Sync

`tools/sync_docs.py` can generate documentation pages from skill metadata.

Expected behavior:

1. Read `catalog.json`.
2. Generate or update `docs/index.md`.
3. Generate skill list tables.
4. Optionally create missing `docs/skills/<skill-name>.md`.
5. Do not overwrite manually written sections unless explicitly requested.

Example:

```bash
python tools/sync_docs.py
```

## 16. Security Considerations

Skills are operational instructions for agents.

Therefore, they should be treated as executable workflow definitions, not harmless text.

Security recommendations:

1. Do not install untrusted third-party skills blindly.
2. Review `SKILL.md` before installing.
3. Review scripts before running.
4. Prefer read-only installation for stable shared skills.
5. Avoid hidden network operations in scripts.
6. Avoid secrets in skill files.
7. Do not store API keys in `SKILL.md`.
8. Keep external dependencies explicit.
9. Use project-scoped skills for experimental workflows.
10. Use global skills only for trusted workflows.

Recommended security metadata:

```yaml
metadata:
  security:
    requires_network: false
    modifies_files: false
    runs_scripts: false
    requires_secrets: false
```

For skills that run scripts:

```yaml
metadata:
  security:
    requires_network: false
    modifies_files: true
    runs_scripts: true
    requires_secrets: false
```

## 17. First Version Roadmap

### Phase 1: Minimal usable repository

Create:

```text
skills_hub/
├── README.md
├── AGENTS.md
├── catalog.json
├── install.sh
├── skills/
│   ├── pr-review/
│   │   └── SKILL.md
│   ├── repo-analysis/
│   │   └── SKILL.md
│   └── paper-reading/
│       └── SKILL.md
└── docs/
    ├── index.md
    └── guide/
        └── write-skill.md
```

Goal:

* make the repository usable immediately
* support manual installation
* support basic documentation
* keep structure simple

### Phase 2: Add automation

Add:

```text
tools/
├── validate_skills.py
├── generate_catalog.py
└── sync_docs.py
```

Goal:

* validate skill structure
* generate catalog automatically
* reduce manual maintenance

### Phase 3: Add documentation site

Add MkDocs or another lightweight static documentation tool.

Goal:

* browse skills by category
* search skill docs
* publish docs with GitHub Pages

### Phase 4: Add testing and quality control

Add skill test cases.

Goal:

* record example prompts
* define expected behavior
* prevent skill quality from drifting

## 18. Recommended Initial Skills

For this repository, the first set of skills should match real daily workflows.

Recommended initial skills:

```text
pr-review
repo-analysis
paper-reading
markdown-polish
experiment-design
llm-infra-analysis
training-framework-design
speculative-decoding-analysis
diffusion-model-analysis
vla-paper-reading
```

Suggested priority:

1. `paper-reading`
2. `repo-analysis`
3. `pr-review`
4. `markdown-polish`
5. `llm-infra-analysis`
6. `experiment-design`

These are high-value because they can be reused across research, coding, and project design tasks.

## 19. Example Skill: `paper-reading`

```text
skills/paper-reading/
├── SKILL.md
├── references/
│   └── paper-analysis-framework.md
└── tests/
    └── sample_prompt.md
```

Purpose:

```text
Read research papers and extract contributions, methods, assumptions, limitations, experiments, and implementation ideas.
```

Use cases:

```text
- summarize a paper
- compare methods
- extract training details
- analyze limitations
- generate implementation notes
```

Output format:

```text
1. Paper metadata
2. Core problem
3. Main contribution
4. Method
5. Training data
6. Experiments
7. Limitations
8. Implementation ideas
9. Relationship to existing work
```

## 20. Example Skill: `repo-analysis`

```text
skills/repo-analysis/
├── SKILL.md
├── references/
│   └── architecture-analysis.md
├── scripts/
│   └── summarize_tree.py
└── tests/
    └── sample_prompt.md
```

Purpose:

```text
Analyze a repository's architecture, modules, data flow, dependencies, and extension points.
```

Use cases:

```text
- understand a new repo
- prepare for refactoring
- locate key modules
- generate architecture documentation
- identify technical debt
```

Output format:

```text
1. Repository overview
2. Main modules
3. Execution entry points
4. Data flow
5. Dependency structure
6. Extension points
7. Risks and unclear areas
8. Suggested next steps
```

## 21. Example Skill: `llm-infra-analysis`

```text
skills/llm-infra-analysis/
├── SKILL.md
├── references/
│   ├── inference-analysis.md
│   ├── training-analysis.md
│   └── serving-analysis.md
└── tests/
    └── sample_prompt.md
```

Purpose:

```text
Analyze LLM infrastructure topics such as inference optimization, serving architecture, training systems, speculative decoding, KV cache, batching, and distributed execution.
```

Use cases:

```text
- analyze an inference optimization paper
- evaluate a serving system design
- explain KV cache behavior
- compare speculative decoding methods
- design training infrastructure
```

Output format:

```text
1. Problem definition
2. System components
3. Execution flow
4. Performance bottlenecks
5. Optimization mechanism
6. Trade-offs
7. Implementation considerations
8. Risks and open questions
```

## 22. Recommended GitHub Description

Short GitHub description:

```text
A reusable skills hub for Codex, OpenCode, and agent-based workflows.
```

Longer README tagline:

```text
A reusable skills hub for Codex, OpenCode, and agent-based development workflows, designed for fast installation, documentation, and long-term skill management.
```

## 23. Final Design Summary

The final design can be summarized as:

```text
SKILL.md      -> agent-readable workflow
references/   -> long-form supporting knowledge
scripts/      -> deterministic helper tools
assets/       -> templates and static resources
tests/        -> examples and expected behavior
docs/         -> human-readable documentation
catalog.json  -> machine-readable skill index
install.sh    -> fast local/project installation
AGENTS.md     -> repository maintenance rules
```

The key idea is:

```text
skills_hub should not be a prompt collection.
It should be a reusable agent workflow library.
```

A well-designed skill hub allows the user to accumulate reusable thinking patterns, project workflows, research methods, and coding procedures over time.

The long-term value is not only faster prompting.
The real value is turning repeated work into durable, installable, documented agent capabilities.
