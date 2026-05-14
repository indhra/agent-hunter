## Summary

  Create a new document named GLOBAL_SPEC.md that sits above
  PLAN.md, SPEC.md, and ROADMAP.md.

  Its role is not code behavior and not sprint planning. It is the
  repo-level doctrine for making agent-hunter a category-defining
  product and trustworthy open-source project. It should explain
  what agent-hunter is trying to become, who it is for, what
  standards govern it, how trust and verification work, how quality
  is evaluated, how maintainers operate, and what must be true
  before public push.

  Use this document as the source of truth for:

  - category and product identity
  - audience and positioning
  - support and compatibility stance
  - benchmark and evaluation policy
  - verified index governance
  - security response expectations
  - contribution and maintainer operating model
  - release discipline
  - proof, launch, and feedback model

  Keep the existing PLAN.md unchanged as the execution plan.
  Keep SPEC.md for implementation behavior.
  Keep ROADMAP.md for versioned rollout.

  ## Implementation Changes

  ### 1. Create GLOBAL_SPEC.md with a maintainer-first tone

  The document should read like a strategic operating spec for
  maintainers and future core contributors. It can still be public,
  but it should optimize for internal decision clarity, not
  marketing.

  Opening section should define:

  - what this document is
  - how it differs from PLAN.md, SPEC.md, and ROADMAP.md
  - that this is the doctrine for category, trust, quality,
    governance, and launch discipline

  ### 2. Include these sections in GLOBAL_SPEC.md

  Use concise prose and crisp bullets. Avoid implementation details
  unless they affect repo policy.

  #### A. Product Identity

  Define:

  - product category: repo-aware skill package manager for Claude
    Code
  - core job: tell users what already exists for their repo before
    they rebuild it
  - primary promise: top 3 install-worthy recommendations with trust
    context
  - what agent-hunter is not: generic search engine, noisy
    marketplace, feature bundle

  #### B. Intended Audience

  Lock:

  - primary user: serious Claude Code user starting or evolving real
    repos
  - secondary user: small teams wanting repeatable project-level
    tool discovery
  - non-primary audiences: casual catalog browsers, enterprise fleet
    management, broad IDE plugin shoppers

  #### C. Product Principles

  State non-negotiables:

  - repo-first, not catalog-first
  - opinionated, not exhaustive
  - trust before breadth
  - first-run value over feature count
  - install once globally, use everywhere
  - project-level instructions only after value is proven

  #### D. New Project / Global Activation Model

  Define the doctrine clearly:

  - global ~/.claude/CLAUDE.md is the default activation surface
  - project CLAUDE.md is optional promotion for team persistence
  - proactive routing is allowed only on sharp moments
  - anti-noise constraints are mandatory
  - maximum one proactive hunt per session unless explicitly
    requested

  #### E. Support And Compatibility Policy

  Define official support boundaries:

  - supported Claude Code environment
  - supported Python range
  - supported operating systems or “best effort” environments
  - whether GitHub token is optional, and for what
  - what counts as supported vs experimental behavior

  Do not invent deep matrix detail; specify policy shape and
  required documentation.

  #### F. Recommendation Quality Standard

  Define what “good” means:

  - top 3 default output
  - at least 1 clearly useful recommendation on most real repos
  - explanations must reference repo signals
  - noise is considered a product failure
  - unsafe results must be blocked before recommendation

  #### G. Benchmark / Evaluation Harness Policy

  Define a repeatable evaluation program:

  - a canonical set of real repo archetypes
  - a standard run-and-score process
  - tracked metrics: useful result rate, install-worthy top result
    rate, noise rate, blocked-result correctness
  - benchmark results should guide ranking work before feature work
  - benchmark artifacts belong in a separate future doc such as
    BENCHMARKS.md, but this doc defines the policy

  #### H. Trust And Verified Index Governance

  Define:

  - what the verified index is for
  - entry criteria at policy level
  - review expectations
  - signer expectations
  - removal/revocation path
  - handling of repo ownership change, abandonment, or newly
    discovered risk
  - difference between verified, community, and raw results from a
    governance perspective

  Keep this policy-level, not code-level.

  #### I. Security Response Policy

  Define:

  - vulnerability reporting path
  - public vs private disclosure preference
  - target response expectations
  - emergency block/revocation path for malicious or compromised
    verified entries
  - what kinds of issues are considered critical
  - expectation that trust beats convenience

  #### J. Contribution And Maintainer Model

  Define:

  - contributor paths: code, benchmarks, verified index submissions,
    docs, security patterns
  - maintainer responsibilities
  - reviewer expectations
  - who can approve what
  - how new maintainers are added
  - what standards apply before merge for high-trust changes

  #### K. Release Discipline

  Define:

  - what alpha, beta, and stable mean
  - what blocks release
  - what “production-ready” means for this repo
  - no overclaiming rule
  - docs, demo, tests, and recommendation quality must align before
    launch pressure

  #### L. Proof Assets And Launch Readiness

  Define what public proof must exist:

  - one real demo
  - three canonical repo examples
  - screenshots of good outputs
  - before/after examples or comparison moments
  - no placeholder media when claiming launch readiness

  #### M. Feedback Loop Without Telemetry

  Define how feedback is collected while preserving the no-telemetry
  stance:

  - benchmark submissions
  - issue templates for bad recommendations and false positives
  - structured bug reports for trust failures
  - launch feedback from real users
  - feedback should be actionable and tied to repo archetypes when
    possible

  #### N. Category And Distribution Strategy

  Define:

  - the phrase/category the project wants to own
  - how it should be introduced publicly
  - what not to emphasize in first-contact messaging
  - launch surfaces: README, demo, example repos, developer
    communities, GitHub
  - success signals in first 30 days after public push

  #### O. V1 Boundary And Future Discipline

  Define:

  - what v1 is
  - what v1 is explicitly not
  - future expansion should not dilute the core product identity
  - breadth is subordinate to trust and top-3 quality

  ### 3. Add a short “Document Relationships” section near the top

  Include explicit references:

  - PLAN.md: execution plan for making the product great
  - SPEC.md: implementation and behavior contract
  - ROADMAP.md: versioned delivery plan
  - GLOBAL_SPEC.md: repo-level product doctrine and governance

  This prevents overlap confusion.

  ### 4. Style constraints for the new document

  Use:

  - short sections
  - strong section headers
  - policy language
  - decision-complete wording
  - no code implementation detail
  - no speculative fluff such as “global phenomenon” phrasing inside
    the doc itself; translate that ambition into standards, gates,
    and governance

  The tone should be serious, durable, and maintainable.

  ## Test Plan

  Validate the new document by checking:
    maintainers, release discipline, proof, feedback, launch
  - it is usable by another maintainer without needing verbal
    context from this chat
  - its guidance is consistent with the current global-first
    onboarding model and trust-first product positioning

  Recommended review pass:

  - read GLOBAL_SPEC.md top to bottom and ask:
      - can a maintainer explain what agent-hunter is in one
        sentence?
      - can they explain how verified trust is governed?
      - can they decide what is in or out of v1?
      - can they decide whether the repo is ready for public push?

  If any of those answers are unclear, the document is not complete.

  ## Assumptions

  - New file name: GLOBAL_SPEC.md
  - Audience: maintainers first, public-readable second
  - Existing PLAN.md stays unchanged
  - Existing SPEC.md and ROADMAP.md stay in place and are only
    referenced, not merged
  - This new document is strategic/spec-oriented, not
    implementation-oriented
