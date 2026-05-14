# agent-hunter 10/10 Plan

This document replaces broad feature-first thinking with a product-first plan.
The goal is not to make `agent-hunter` bigger.
The goal is to make it feel inevitable.

If this plan is followed well, `agent-hunter` should become a tool that serious Claude Code users install early, trust quickly, and recommend to others.

---

## 1. Product Truth

### Current state

Right now `agent-hunter` is framed as:

`a context-aware skill and MCP discovery tool with security scanning`

That is useful, but it is still a feature bundle.
Feature bundles do not become breakout tools.

### Required shift

`agent-hunter` must become:

`a repo-aware skill package manager for Claude Code`

Or even more sharply:

`the thing that tells you what already exists for your repo before you build it again`

That is the real product.

Users do not want:
- discovery
- catalogs
- trust tiers
- scan pipelines

Users want:
- what should I install right now
- what should I not waste time building
- what is safe

This must become the center of the product, the docs, the demos, and the ranking logic.

---

## 2. Core Promise

The product must reliably do this:

> Given my repo, tell me the top 3 skills or MCPs I should use now, why they fit, and which ones to avoid.

If `agent-hunter` cannot do this extremely well, nothing else matters.

Not rollback.
Not sandboxing depth.
Not more commands.
Not more roadmap breadth.

The quality of this core promise is the product.

---

## 3. The 10/10 User Experience

The target experience is:

1. Install in one command.
2. Run on a real repo in under 20 to 30 seconds.
3. Show only the best 3 results by default.
4. Give one sharp reason for each result.
5. Hide junk and clearly block unsafe results.
6. Make install frictionless from the result screen.
7. Leave the user feeling they saved time immediately.

After first use, the user should think:

- `this understood my repo fast`
- `these results are better than random GitHub search`
- `this saved me from rebuilding something`
- `I trust this enough to use again`
- `I want this in every serious Claude project`

If the user instead thinks:

- `interesting concept`
- `many features`
- `ambitious roadmap`

then the product is not yet good enough.

---

## 4. Non-Negotiable Product Requirements

These are mandatory for a 10/10 version.

### 4.0 New project onboarding must work

`agent-hunter` must work even when the user is starting a brand new project and there is no local project `CLAUDE.md` yet.

This is critical.

If the product only works well after a repo already has custom instructions, then it loses the exact moment where it is most valuable:

- project kickoff
- first tooling decisions
- first “should I build this or does it already exist?”

The onboarding model should be:

- global `~/.claude/CLAUDE.md` for availability and routing
- project `CLAUDE.md` for team-level persistence and sharing

That means the product should be usable immediately after install on any repo, including new repos with no local setup.

### 4.1 One-command install

The install path must be short, obvious, and low-risk.

Requirements:
- one primary install method
- minimal manual copying
- clear post-install success check
- no confusing split between install patterns unless one is clearly preferred

Success condition:
- a new user can install without reading half the README

### 4.2 One-command run

The first meaningful action should be obvious:

```bash
/agent-hunter
```

or

```bash
agent-hunter hunt .
```

There should be no ambiguity about what the first run is supposed to do.

### 4.3 Top 3 by default

The default output must be opinionated.

Requirements:
- show the best 3 recommendations by default
- show more only on explicit request
- avoid result floods
- rank for usefulness, not breadth

### 4.4 Strong “why this for you”

Each result must answer:

- why this repo
- why now
- why this over others

The explanation must be specific, not generic.

Bad:
- `good for Python projects`

Good:
- `ranked high because your repo uses FastAPI, pytest, and Docker, and this skill targets backend test and deployment workflow directly`

### 4.5 Safe / caution / blocked

The tool must communicate trust simply:

- `safe to install`
- `review before installing`
- `blocked`

The user should not need to understand the scanner internals to trust the output.

### 4.6 Speed

Target:
- meaningful results in under 30 seconds

Hard ceiling:
- avoid user perception that this is “slow but smart”

Fast and good beats broad and slow.

### 4.7 Real proof

The product is not launch-ready without:
- one real demo video
- three real repo examples
- at least a few cases where the recommendation is obviously useful

No placeholder media.
No fake polish.

### 4.8 Full credibility

All public-facing material must say the same thing.

That includes:
- README
- `SKILL.md`
- `pyproject.toml`
- version tags
- changelog
- setup messaging

Any contradiction lowers trust instantly.

---

## 4A. Global And Project CLAUDE.md Strategy

This is not just a setup detail.
It is part of product distribution.

### Global `~/.claude/CLAUDE.md`

This is the required default integration point.

Why:
- it makes `agent-hunter` available from day 1
- it solves the new-project problem
- it lets the tool activate before a local project `CLAUDE.md` exists
- it creates a clean “install once, use everywhere” experience

Requirements:
- `setup` should add a small, explicit, readable block
- the block should explain when `/agent-hunter` should be invoked
- the block must avoid being verbose or intrusive
- the block must not create noisy over-triggering

### Project `CLAUDE.md`

This is the optional second step.

Why:
- it makes behavior persistent for the project
- it gives teammates the same workflow
- it turns a personal tool into a shared team habit

Requirements:
- after a useful first run, offer to add the block to the project `CLAUDE.md`
- do not force this before the user has seen value
- make the project-level block concise and easy to understand

### Product rule

The correct model is:

- install once globally
- use immediately on any repo
- promote to project-level instructions when the user wants team-wide behavior

That should become a core part of the product story.

---

## 4B. Routing Rules And Anti-Noise Constraints

Global routing is useful only if it stays disciplined.

The tool must not feel like it hijacks Claude Code.

### It should activate on sharp moments

Examples:
- user starts a new project
- user asks what they should install
- user asks for skills, tools, agents, or MCPs for a task
- user is about to build something from scratch that likely already exists

### It should not activate aggressively

Avoid:
- hunting on every session start with no context
- repeatedly triggering in the same session
- interrupting unrelated coding flows
- forcing a hunt when the user is already deep in implementation

### Guardrails

Requirements:
- keep the session loop guard strict
- maximum one proactive hunt per session unless the user explicitly asks again
- prefer recommendation moments over background automation
- be easy to ignore when not needed

Success condition:
- the user feels assisted, not nagged

---

## 5. What To Optimize For

### Primary metric

The top 3 recommendation quality.

That means:
- relevance
- usefulness
- installability
- trustworthiness

If the top 3 are strong, the product works.
If the top 3 are weak, the product fails even if the architecture is impressive.

### Secondary metrics

- time to first useful recommendation
- percentage of runs with at least 1 clearly relevant result
- percentage of runs where user installs something
- percentage of unsafe results hidden correctly
- number of real repos where the tool feels better than manual search

### Anti-metrics

Do not optimize for:
- number of commands
- number of scan rules
- number of roadmap bullets
- number of sources queried
- number of results shown

Feature count is not product quality.

---

## 6. What To Cut Or Deprioritize

To make this a breakout tool, the following must be pushed down unless they improve the core promise directly:

- broad feature expansion
- roadmap theater
- over-detailed security marketing
- “self-evolving” positioning
- too many default commands
- too much catalog behavior
- anything that adds complexity but not first-run value

Rule:

If a feature does not improve:
- recommendation quality
- trust
- first-run clarity
- install success

it is not a current priority.

---

## 6A. V1 Cut Line

To avoid scope creep, the first great release needs a hard boundary.

### V1 is in scope if it improves

- top 3 recommendation quality
- first-run clarity
- trust in the output
- smooth install and activation
- usefulness on real repos

### V1 is out of scope if it is mostly breadth

Examples:
- more commands that do not improve the default workflow
- more search sources before ranking quality is strong
- deeper security marketing without better user-facing trust
- speculative automation beyond one disciplined proactive hunt
- advanced ecosystem features that do not improve first-run value

### V1 product definition

V1 is not:
- the biggest discovery tool
- the most feature-rich skill manager
- a full ecosystem control plane

V1 is:

> the best way for a Claude Code user to find the right skills or MCPs for a repo before rebuilding them from scratch

When a decision is unclear, prefer the narrower path that strengthens this outcome.

---

## 7. Product Positioning

### Recommended one-line positioning

`agent-hunter is a repo-aware skill package manager for Claude Code.`

### Stronger functional version

`agent-hunter reads your repo, finds the best skills and MCPs for it, explains why they fit, and blocks the risky ones.`

### What not to lead with

Do not lead with:
- trust tiers
- security pipeline internals
- self-evolving language
- roadmap breadth
- architecture diagrams

Lead with outcome:

`before you build it again, check what already exists`

---

## 8. First-Run Workflow To Perfect

This is the single workflow that must become excellent:

### Workflow

1. User installs `agent-hunter`.
2. User opens a real repo.
3. User runs `/agent-hunter`.
4. `agent-hunter` reads repo signals.
5. It returns top 3 recommendations.
6. Each recommendation has:
 - name
 - trust state
 - install command
 - one precise reason
7. Unsafe results are blocked quietly and clearly counted.
8. User installs one result immediately.

### Required emotional outcome

The user feels:
- understood
- guided
- protected
- faster

This exact workflow is the launch surface.

### New-project version of the workflow

There must also be a first-day workflow for a repo with no local `CLAUDE.md`:

1. User installs `agent-hunter`.
2. `setup` updates global `~/.claude/CLAUDE.md` with a concise routing block.
3. User opens a new or early-stage repo.
4. User asks Claude what tools, skills, or MCPs they should use.
5. `/agent-hunter` is available immediately through the global instructions.
6. `agent-hunter` returns top recommendations.
7. After the user sees value, it offers to add project-level instructions for team reuse.

This flow is important because the product is often most useful at the start of a project, not after the project is already heavily configured.

---

## 9. Codebase Priorities

The codebase already has solid breadth.
Now it needs product discipline and reliability.

### 9.1 Make paths injectable

Current hard-coded writes to user home directories reduce testability and create fragility.

Requirements:
- configurable registry path
- configurable skills directory
- configurable backups path
- configurable install log path
- clear default paths for normal users
- easy override for tests and sandboxed execution

Outcome:
- tests become deterministic
- CLI becomes safer
- local development becomes easier

### 9.2 Tighten truth between docs and code

Requirements:
- one version truth
- one scoring truth
- one install story
- one trust story
- no stale examples

Outcome:
- trust goes up immediately

### 9.3 Reduce partial-feature drift

Any shipped feature should be:
- complete
- clearly marked partial
- or removed from the pitch

Do not market placeholders as finished product.

### 9.4 Improve ranking before adding more sources

The next step is not more search.
The next step is better judgment.

Ranking work should focus on:
- project fit
- actionability
- trust
- surprise value

Goal:
- top 3 should feel curated, not computed.

---

## 10. Output Quality Standard

The recommendation screen should feel like advice from a strong engineer, not a search result page.

### Desired output style

- few results
- sharp reasons
- clear trust
- clear action
- quiet confidence

### Bad output style

- long ranked lists
- generic “good for X”
- too many metadata points
- security jargon overload
- unclear next step

### The recommendation format should answer

For each result:
- what is it
- should I trust it
- why is it right for this repo
- what do I do next

---

## 11. Launch Readiness Criteria

Do not push for attention until the following are true:

### Product criteria

- install is smooth
- first run is obvious
- top 3 quality is strong
- one command gets the user to value
- output is opinionated

### Trust criteria

- docs and code agree
- no placeholder demo
- no inflated promises
- no obvious contradictions
- security claims match reality

### Engineering criteria

- tests pass cleanly
- path/config issues are solved
- critical workflows are covered
- failure states are understandable

### Proof criteria

- real demo recorded
- three polished repo examples
- at least a few external users can reproduce the value

---

## 12. What Makes People Share It

Users will not share this because it has many features.

They will share it when:
- it finds one unexpectedly useful skill or MCP
- it saves real time immediately
- it feels smarter than manual search
- it feels safe enough to trust
- the output is screenshot-worthy

The shareable moment is:

> `I ran this on my repo and it found exactly the thing I was about to build myself.`

That is the star engine.

---

## 13. Execution Order

The order matters.

### Phase 1: sharpen the truth

Goals:
- define the one-sentence positioning
- align product promise
- remove fluff and overclaiming

Deliverables:
- new homepage message
- updated README direction
- clear “top 3 for your repo” framing

### Phase 2: perfect the first-run experience

Goals:
- make install simple
- make first run obvious
- reduce friction in output and install flow

Deliverables:
- one preferred install method
- one preferred first-run command
- improved default result presentation

### Phase 3: improve recommendation quality

Goals:
- make the top 3 consistently useful
- test against real repos, not toy cases

Deliverables:
- ranking review on real projects
- bad-case list
- tuned heuristics

### Phase 4: restore credibility

Goals:
- make the repository trustworthy
- remove contradictions and stale material

Deliverables:
- aligned versions
- aligned docs
- no placeholder claims
- no outdated examples

### Phase 5: ship proof

Goals:
- make the value visible fast

Deliverables:
- demo video
- example runs
- polished screenshots

### Phase 6: ask for attention

Goals:
- get real user feedback
- generate word of mouth

Deliverables:
- launch-ready README
- demo post
- example repos

Do not reverse this order.

---

## 14. 30-Day Execution Plan

## Week 1: reset the story

Objectives:
- lock the product truth
- simplify positioning
- remove noise

Tasks:
- rewrite positioning around repo-aware recommendations
- reduce README sprawl
- remove placeholder demo elements
- remove outdated sample outputs
- align version references across docs and metadata
- define the default “top 3” report behavior

Success criteria:
- a new visitor understands the product in under 10 seconds
- no visible contradiction across public docs

## Week 2: improve the recommendation engine

Objectives:
- make output feel high-signal

Tasks:
- test on 10 to 20 real repos
- collect weak recommendation cases
- tune ranking rules
- improve “why this for you”
- reduce generic matches
- prefer actionability over raw popularity

Success criteria:
- most real runs yield at least 1 strong recommendation
- the top 3 look deliberate, not noisy

## Week 3: harden UX and reliability

Objectives:
- make the tool dependable

Tasks:
- remove hard-coded path fragility
- improve config injection
- fix test failures related to home-directory writes
- simplify install flow
- tighten CLI output and next-step guidance

Success criteria:
- tests pass cleanly
- local runs and test runs behave predictably
- install and audit flows do not feel fragile

## Week 4: prepare for public traction

Objectives:
- create proof and polish

Tasks:
- record a real demo
- prepare 3 real repo walkthroughs
- capture screenshots
- tighten README for launch
- ask a small set of users to try it on their repos
- collect quotes, failures, and surprises

Success criteria:
- the demo makes the product obvious
- at least a few real users report saved time or useful finds

---

## 14A. Validation Loop

This plan only works if the product is tested against real repos continuously.

### Weekly validation cycle

Every week:

1. run `agent-hunter` on a set of real repos
2. record the top 3 recommendations
3. note which ones were strong, weak, noisy, or unsafe
4. capture false positives and obvious misses
5. improve ranking and UX before adding more breadth

### Minimum validation standard

Use a mix such as:
- backend repo
- frontend repo
- ML/data repo
- CLI/tooling repo
- repo with almost no setup
- repo with mature setup

### What to log

For each run:
- repo type
- whether at least 1 recommendation was clearly useful
- whether the top result was install-worthy
- whether explanations felt specific
- whether output was noisy
- whether unsafe results were handled correctly

### Priority rule

If validation shows weak recommendation quality, fix that before building more features.

The ranking and first-run experience should be refined through repeated real-repo testing, not assumed from architecture.

---

## 14B. Launch Gate

Do not push hard for public attention until this gate is passed.

### Product gate

- install works cleanly
- global `CLAUDE.md` activation works
- new-project flow works with no local `CLAUDE.md`
- top 3 output feels high-signal
- next step is obvious from the result screen

### Quality gate

- README matches reality
- `SKILL.md`, setup, versioning, and docs are aligned
- no placeholder media or stale examples
- no inflated feature claims

### Engineering gate

- tests are green
- critical workflows are covered
- path/config behavior is reliable
- obvious failure states are understandable

### Proof gate

- real demo recorded
- 3 strong repo examples prepared
- top 3 quality proven on repeated real runs
- at least 3 external users have tried it
- at least some users report clear saved time or strong recommendation quality

### Rule

If this gate is not passed, keep improving the product.
Do not compensate with more marketing.

---

## 15. Decision Rules

Use these rules for future product decisions.

### Build it if

- it improves top 3 recommendation quality
- it improves trust
- it improves first-run clarity
- it improves install success
- it improves speed meaningfully

### Delay it if

- it adds complexity without obvious user value
- it expands scope before quality is high
- it is mostly infrastructure vanity
- it is hard to explain in one sentence

### Cut it if

- it weakens the product story
- it adds maintenance burden but no user pull
- it creates more claims than proof

---

## 16. The Standard

`agent-hunter` becomes a 10/10 tool when serious Claude Code users feel:

> `I should run this before building anything non-trivial.`

That is the bar.

Not:
- `interesting`
- `ambitious`
- `feature-rich`

But:
- `use this first`

If the product earns that response, it becomes great.
