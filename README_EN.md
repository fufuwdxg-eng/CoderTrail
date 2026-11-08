# CoderTrail — Learn by Building Projects

[简体中文](README.md) | **English**

**Move beyond programming fundamentals with project-based practice, evidence-backed reviews, and line-by-line feedback.**

**CoderTrail** is an AI-agent Skill for designing programming project exercises and reviewing student submissions. It includes Python command-line tools, a nine-dimension quality rubric, JSON templates, and history indexes. Its workflow connects source research, source evaluation, exercise design, implementation validation, homework review, and planning the next round of practice.

The core Skill is named `build-project-training`. Keep that name and the existing directory structure when installing it.

The goal is to help learners progress from understanding syntax to analyzing requirements, organizing modules, checking behavior, explaining design choices, and maintaining projects. Its educational effectiveness still needs to be evaluated through real learning experiences.

**Language status:** This README is available in English. The detailed Skill instructions, reference documents, and default reports are currently primarily in Chinese. Training documents default to Chinese Word files; this English introduction does not mean the entire project has been localized.

## Contents

- [Who it is for](#who-it-is-for)
- [Features](#features)
- [How it runs](#how-it-runs)
- [Getting started](#getting-started)
- [How exercises are created](#how-exercises-are-created)
- [How homework is reviewed](#how-homework-is-reviewed)
- [Repository structure](#repository-structure)
- [Nine-dimension quality rubric](#nine-dimension-quality-rubric)
- [Command-line quick start](#command-line-quick-start)
- [Local checks](#local-checks)
- [Deliverables](#deliverables)
- [Data and limitations](#data-and-limitations)
- [Frequently asked questions](#frequently-asked-questions)
- [Contributing](#contributing)
- [Licensing and third-party sources](#licensing-and-third-party-sources)

## Who it is for

- Learners who know basic syntax, functions, common data structures, file I/O, and error handling in their chosen language.
- Self-directed learners who want practice with debugging, refactoring, changing requirements, testing, and performance analysis.
- Teachers, teaching assistants, and study groups that need clear acceptance criteria, progressive hints, and reference implementations.
- People building or using coding agents who want a structured workflow for project training and homework feedback.

For your first request, describe what you have learned, your target language, your environment, and the time you can spend. Difficulty should match that context. Complicated dependency installation is not a substitute for meaningful programming challenges.

## Features

- **Configurable exercise mix.** A set defaults to 15 exercises: 3 foundational and 12 advanced. Users can specify counts, ratios, or percentages.
- **Research before generation.** Consult existing material and real online source code before designing exercises. Sources must score at least 85/100 and meet the additional admission requirements.
- **Broader practice over time.** Compare against past exercises across languages, application domains, core concepts, deliverable types, and engineering methods.
- **Multiple programming languages.** Adapt the workflow to a single language, multiple implementations, or collaborating components. Validate each actual language and the relevant integration interfaces.
- **Complete training packages.** Deliver a Word document with questions first and all reference code at the end, together with runnable source and grading tools.
- **Line-by-line homework feedback.** Explain each line, assign a teaching score from 0 to 10 when justified, explain correctness and the score, and suggest improvements.
- **Evidence and learning history.** Preserve actual test results, feedback on unsuccessful attempts, and learning records for future practice.

The AI agent performs research, semantic code review, exercise design, and teaching judgments. The Python tools execute acceptance manifests, preserve evidence, calculate weighted scores, check review coverage, and maintain records. The CLI does not independently read arbitrary code and generate its nine quality ratings.

## How it runs

| Component | Responsibility |
| --- | --- |
| Agent with the Skill loaded | Online research, requirements analysis, source review, exercise design, quality ratings, and line-by-line explanations |
| Python tools | Acceptance execution, evidence archives, score calculation, review coverage checks, and index maintenance |
| Target-language toolchain | Actual builds, type checks, behavior tests, and integration checks |
| Agent's document and storage capabilities | Word generation and inspection, source packaging, and saving deliverables |

The chosen agent environment supplies the model service, network access, document processing, and file storage.

Requirements:

- The accompanying tools use **Python 3.10+ and the standard library**.
- Writing question-bank and learning-history records uses Linux/WSL file locking. Windows users can run these maintenance commands in WSL.
- Target projects require their own runtimes, compilers, and test dependencies. The tools do not install them automatically.
- The existing cross-language regression fixtures require Node.js and g++. The Python-only example does not require either.
- The complete exercise-generation workflow requires online source research and actual command execution. An environment without these capabilities must report the verification steps it could not complete.

## Getting started

Download the repository and install the entire [skills/build-project-training](skills/build-project-training) folder using your agent platform's Skill installation method. The entry point is [SKILL.md](skills/build-project-training/SKILL.md). Preserve the relative locations of `scripts`, `references`, `assets`, and `agents`.

Installation differs between platforms; this repository does not assume a universal installer. If your platform supports explicitly loading instruction files, ask an agent with file-reading and execution capabilities to read `SKILL.md` and follow it. Persistence across sessions depends on the platform.

Example training request:

```text
Use build-project-training to create a Python project-development exercise set.
I know basic syntax, functions, lists and dictionaries, file I/O, and exceptions.
My environment is Windows 11 with WSL. Prefer free tools and few dependencies.
Create 15 exercises: 5 foundational and 10 advanced.
First review existing material and real online projects using the nine-dimension
source-quality rubric. Make this set substantially different from my history.
Place all reference code at the end of the document.
Include acceptance criteria, runnable source, grading tools, and validation records.
```

Example homework request:

```text
Here are the original assignment, my environment, and all my handwritten source files.
Provide an overall review using the nine-dimension rubric.
For every line, give the original file and line number, its purpose, a 0–10 score,
the reason for that score, whether it is correct and why, suggested changes,
and the evidence supporting your judgment.
Mark unsupported judgments as pending verification.
Finish with the 1–3 improvements I should prioritize.
Keep my original submission unchanged and save any revised version separately.
```

Include supporting modules, student-written tests, and necessary configuration to reduce judgments caused by missing context.

For a later set, you can request JavaScript, 15 exercises, and a foundational-to-advanced ratio of `2:3`, while asking the agent to use previous history and feedback. That produces 6 foundational and 9 advanced exercises. When a ratio cannot divide the total exactly, apply the documented rounding policy and report the actual counts. Clarify conflicts between a strict ratio and a fixed total.

See [examples/prompts.md](examples/prompts.md) for more requests and [docs/quickstart.md](docs/quickstart.md) for detailed commands. These documents are currently primarily in Chinese.

## How exercises are created

1. **Read history and constraints.** Confirm language, version, platform, prerequisites, exercise mix, learning feedback, and existing coverage.
2. **Research real projects.** Record searches, candidate scopes, and exclusion reasons. Read source, tests, configuration, and licenses at fixed revisions.
3. **Review and validate sources.** Run applicable tests and independent checks, document evidence for all nine dimensions, and determine admission status.
4. **Review the exercise mix.** Compare past and proposed exercises for learning goals, difficulty, diversity, and added value.
5. **Implement and validate reference solutions.** Define acceptance requirements first, then implement, build, test, and re-review. Verify integration for collaborating components.
6. **Deliver and record.** Check document layout, embedded code, and source snapshots. Save and verify the deliverables before recording the batch.

For a default 15-exercise set, the research policy requires at least 45 deduplicated candidate scopes across at least 8 domains or purposes, aims to use at least 8 independent upstream projects, and compares at least 2 independent implementations for each final direction. Research and detailed review proceed in stages; building an admitted source bank requires real research and execution time.

Diversity covers domains, core concepts, deliverable types, and engineering methods. Changing only a language, story, filename, or dataset does not automatically create a new exercise. For a user-constrained domain, explain the constraint and expand the other dimensions where possible.

If network access, source code, a runtime, or evidence is missing, report the actual progress and gaps and retain a pending status. See [SKILL.md](skills/build-project-training/SKILL.md) and [research-diversity.md](skills/build-project-training/references/research-diversity.md).

## How homework is reviewed

Homework review is a separate workflow: read the assignment and original submission, obtain applicable execution evidence, and provide both an overall nine-dimension review and line-by-line feedback. Reviewing one submission does not require repeating the candidate-project research for a whole training set.

| Per-line feedback | What it records |
| --- | --- |
| Original location | Original file, physical line number, code, and line type |
| Purpose | The line's role within its function, module, data flow, or control flow |
| Teaching score | An integer from 0 to 10, with a reason |
| Correctness and explanation | A judgment grounded in the assignment, surrounding code, and actual tests or static reasoning |
| Suggested change | A necessary, minimal improvement that preserves the student's approach where practical; reasonable code can be kept |
| Evidence and confidence | Traceable support, distinguishing confirmed issues, potential issues, and missing information |

Every nonblank physical line is reviewed, including comments, imports, declarations, structural lines, and continuation lines. Blank lines remain visible, with their separation role explained and their score marked **N/A**. Unsupported judgments remain **pending verification** instead of receiving invented scores.

Track a shared root cause once and link its affected lines. Do not repeatedly deduct from the overall score merely because one issue spans many lines. **Line scores are teaching diagnostics; their average is not the overall homework grade.**

Read large submissions by file and in chunks of approximately 100–200 lines while retaining cross-module context. Check coverage and explicitly list unfinished ranges. Save repairs separately and rerun the same acceptance checks before presenting a verified before/after comparison. Label unexecuted suggestions accordingly.

Low-scoring submissions, compilation failures, and incorrect implementations still receive feedback. If the assignment is missing, explain what can be established statically and keep the correctness assessment pending. See [homework-marking.md](skills/build-project-training/references/homework-marking.md).

## Repository structure

| Path | Contents |
| --- | --- |
| [skills/build-project-training/SKILL.md](skills/build-project-training/SKILL.md) | Agent entry point and exercise-design principles |
| [skills/build-project-training/references](skills/build-project-training/references) | Quality rubric, language adaptation, diversity, delivery, and homework-review rules |
| [skills/build-project-training/scripts](skills/build-project-training/scripts) | Execution, score calculation, line coverage, bank maintenance, and regression tests |
| [skills/build-project-training/assets](skills/build-project-training/assets) | JSON templates, historical topic indexes, and runner-validation fixtures |
| [docs/quickstart.md](docs/quickstart.md) | Environment setup, exercise mix, acceptance execution, homework review, and learning records |
| [docs/validation.md](docs/validation.md) | Recorded validation results and their scope |
| [examples/prompts.md](examples/prompts.md) | Example requests |
| [.github/workflows/checks.yml](.github/workflows/checks.yml) | GitHub Actions check configuration |
| [PACKAGE_MANIFEST.json](PACKAGE_MANIFEST.json) | File inventory, SHA-256 digests, and validation results for the packaged distribution |

## Nine-dimension quality rubric

| Dimension | Weight |
| --- | ---: |
| Correctness | 20 |
| Readability & Clarity | 10 |
| Maintainability & Extensibility | 10 |
| Testability | 10 |
| Performance & Efficiency | 10 |
| Architecture & Design | 15 |
| Documentation | 5 |
| Engineering Practices | 10 |
| Reliability & Robustness | 10 |
| **Total** | **100** |

Each dimension receives an integer rating from 0 to 10. Calculate the total as `sum(rating × weight / 10)`. For example, a correctness rating of 9 contributes `9 × 20 / 10 = 18` points.

Unknown ratings use `null` and remain pending. Do not invent full marks, substitute zero, remove a dimension, or renormalize the other weights. See [quality-rubric.md](skills/build-project-training/references/quality-rubric.md).

Sources and reference implementations must satisfy **all** admission requirements:

- Total score of at least **85/100**, correctness of at least **9/10**, and testability and reliability of at least **8/10** each.
- A severe deficiency rated 0–2 in any dimension blocks admission. Scores of 85–88 require a recorded independent review or blind re-rating.
- Fixed source revision and scope, inspection of the relevant implementation and documentation, and passing applicable tests and independent checks through actual execution.
- No unresolved critical defect affecting the adopted scope, clear reuse permission, and fulfillable attribution and notice obligations.
- Traceable evidence for every dimension and a verifiable execution archive.

Review the external source and the adapted reference implementation separately. `eligible` means the requirements are satisfied; `pending` means evidence is incomplete; `rejected` means there is evidence that a requirement is not satisfied.

The 85-point threshold selects adopted sources and reference implementations. It does not prevent feedback on low-scoring student work.

## Command-line quick start

Run these Bash commands from the **repository root** on Linux/WSL. Review the code and acceptance commands before execution.

### Prepare a working directory

```bash
SKILL_DIR="$PWD/skills/build-project-training"
mkdir -p work
python3 --version
python3 -B "$SKILL_DIR/scripts/project_grader.py" --help
```

`work/` holds local research, evidence, and feedback and is ignored by Git. Use a new output directory for each execution and report, outside the project under evaluation.

### Calculate the exercise mix

```bash
python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix \
  --counts 5 10 --basis 'Learner requested 5 foundational and 10 advanced exercises'

python3 -B "$SKILL_DIR/scripts/curate_bank.py" mix \
  --ratio 2:3 --basis 'Learner requested a foundational-to-advanced ratio of 2:3'
```

These commands calculate the configuration; they do not generate exercises or modify the bank. Percentage and rounding rules are documented in [learning-design.md](skills/build-project-training/references/learning-design.md).

### Run the existing Python validation fixture

This example checks the runner and paths using the repository's fixture. The fixture is not a newly generated exercise or an admitted online source.

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" run \
  "$SKILL_DIR/assets/validation-fixtures/manifest-python.json" \
  --project "$SKILL_DIR/assets/validation-fixtures" \
  --out "$PWD/work/demo-evidence-01"

python3 -B "$SKILL_DIR/scripts/project_grader.py" verify \
  "$PWD/work/demo-evidence-01/execution.json"

python3 -B "$SKILL_DIR/scripts/project_grader.py" grade \
  "$PWD/work/demo-evidence-01/execution.json" \
  --purpose learner --out "$PWD/work/demo-feedback-01"
```

The fixture manifest contains 12 cases. After a successful run, inspect `grade.md` and `grade.json` in the feedback directory. Without an accompanying nine-dimension review, the total score remains pending. Keep the entire execution directory so the source snapshot and logs can be checked together.

### Connect execution evidence to line-by-line review

The following assumes that you have inspected and run a real submission, producing `work/submission-evidence-01/execution.json`, and completed `work/scope.json`. Start the scope file from [homework-scope-template.json](skills/build-project-training/assets/homework-scope-template.json), identifying the assignment, student files, and justified exclusions.

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" prepare-homework \
  work/submission-evidence-01/execution.json \
  --scope work/scope.json --out work/homework-review.json
```

The agent must read the full context and complete the draft with the nine-dimension review, line explanations, and shared issues. Then run:

```bash
python3 -B "$SKILL_DIR/scripts/project_grader.py" check-homework \
  work/submission-evidence-01/execution.json --review work/homework-review.json

python3 -B "$SKILL_DIR/scripts/project_grader.py" review-homework \
  work/submission-evidence-01/execution.json --review work/homework-review.json \
  --out work/homework-feedback-01
```

For `check-homework` and `review-homework`, exit code 0 means the review record is complete, 1 means some items remain pending, and 2 means configuration, structure, or evidence is invalid. Code 0 does not mean the score is at least 85 or that every AI judgment is correct.

See [docs/quickstart.md](docs/quickstart.md) and [scoring-program.md](skills/build-project-training/references/scoring-program.md) for history initialization, `record-attempt`, project acceptance manifests, and source packaging.

## Local checks

Run from the repository root:

```bash
python3 -B -m unittest discover \
  -s skills/build-project-training/scripts \
  -p 'test_*.py' -v
```

Python 3.10+ is required. Bank and learning-record writes use Linux/WSL; the complete cross-language regression suite also requires Node.js and g++.

Missing toolchains can cause relevant checks to be skipped. Read the full output before describing the validated scope. The recorded results for this distribution are in [docs/validation.md](docs/validation.md); GitHub Actions status depends on its actual runs after upload.

The repository has 68 regression checks in three groups: 39 admission and planning checks, 19 execution and grading checks, and 10 line-by-line review checks. The documented run on **2026-11-04** recorded 68 passes, 0 failures, and 0 skips. See the validation record for the environment and scope.

Recorded execution coverage includes Python, Node.js JavaScript, g++ C++17, and a Python-to-JavaScript collaboration fixture. Other languages have adaptation guidelines and still require actual verification in their respective environments.

## Deliverables

### Exercise generation

- **Training document:** A Chinese Word document by default, with questions first, source evaluations and reflection guidance afterward, and all reference code at the end.
- **Source package:** Runnable implementations, necessary configuration, tests, execution manifests, and accompanying grading tools.
- **Research and validation archive:** Sources, fixed revisions, licenses, scoring evidence, execution records, and their applicable scope.
- **History index:** A batch record written after the final deliverables have been saved and verified, supporting future deduplication and broader coverage.

The document and source package should come from the same validated snapshot. Document layout checks, extracting embedded source, and rerunning that source are also part of delivery validation. Save to the user's chosen destination and verify that it is accessible.

### Homework review

| File | Contents |
| --- | --- |
| `grade.md` | Overall nine-dimension review, actual acceptance results, shared issues, and next actions |
| `line-review.md` | Complete explanations ordered by original file and line number |
| `grade.json` | Machine-readable review, acceptance results, and coverage statistics |
| `homework-review.json` | Original locations, evidence references, line comments, and shared issue records |

A Word review report requires the agent's document-generation capabilities. Preserve the complete line-by-line content when formatting it.

## Data and limitations

The distribution includes topics and deduplication tags for 30 exercises from two earlier sets, all marked `legacy_unreviewed`. It does not distribute the original Word files or claim that those exercises passed the current nine-dimension review. Personal document locators were removed from the distributed index. The admitted source bank and student-attempt history start empty.

These legacy entries are not fully reviewed exercise texts or admitted sources. Users must supply their own original materials, execution archives, and learning records. A successful temporary command does not by itself establish that records were saved persistently.

Keep research, student code, and feedback in a separate working directory, and preserve the appropriate access boundaries when publishing a repository. The root `.gitignore` excludes `work/`.

The runner provides temporary copies, timeouts, output limits, and path checks. **It is not a sandbox for malicious code.** Inspect external projects, student submissions, and execution commands before running them.

Passing tests, complete evidence fields, and matching digests do not independently establish code quality or correct AI judgments. Digest and log checks can reveal missing data, mismatches, and changes; they are not authenticity signatures and cannot rule out fabrication of an entire archive. Scores are evidence-based training judgments, not third-party certification. Tool tests also do not establish a general improvement in learning outcomes.

## Frequently asked questions

**Do exercises have to use Python?** No. The maintenance tools use Python, but exercises can target other languages. Obtain the appropriate evidence for every language actually used.

**Will a solution be marked wrong for differing from the reference?** Review against the assignment and verifiable behavior. A reasonable alternative implementation should not be rejected merely for using a different approach.

**Can the program objectively grade any project with one command?** It executes commands, calculates scores, and checks consistency. Requirements interpretation, quality review, and teaching explanations still come from the agent or reviewer. Unsupported ratings stay pending.

**What if the network or compiler is unavailable?** Continue with available research or static explanations and report the gaps. Complete the required online research and runtime verification later; static inspection or results from another language cannot substitute for them.

**Can failing or low-scoring homework be reviewed?** Yes. Preserve failures and low scores in the learning history; do not admit them as qualified reference sources.

**How is progress measured on resubmission?** Check whether earlier issues are resolved and whether new issues appear. Calculate changes only under comparable conditions, such as the same assignment, language, acceptance manifest, and rubric version. Do not directly rank unrelated assignments.

## Contributing

Issues and pull requests based on real use are welcome, including verified language adapters, better edge cases, clearer report explanations, and improved beginner documentation.

For bug reports, provide toolchain versions, platform, a minimal reproduction, the acceptance manifest, expected and actual behavior, relevant commands, and redacted logs. Do not publish credentials, access tokens, or student material without authorization.

For behavior changes, run the relevant regression checks and explain added validation. For documentation changes, check commands, relative links, and actual functionality. Synthetic test records and runner fixtures must not be added to the bank as real admitted sources.

## Licensing and third-party sources

The current distribution does not include a `LICENSE` file or specify a project-wide open-source license. The publisher should define the intended permissions for use, modification, and redistribution; the actual repository license file is authoritative. See [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

For third-party projects adopted later, record the author, fixed revision, URL, adopted scope, and license separately, and fulfill applicable attribution and notice requirements. Passing the quality review does not change a source's licensing terms. See [NOTICE.md](NOTICE.md).
