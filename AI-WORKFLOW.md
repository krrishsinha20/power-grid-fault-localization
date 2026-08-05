# AI-Assisted Engineering Workflow Report

This document details the methodology, human-AI collaboration pattern, percentage contribution estimates, and concrete case studies of AI-generated software flaws identified and corrected during the development of the AI Power Grid Fault Localization System.

---

## Engineering Methodology & Human Role

This repository was constructed using **AI-first pair programming** (using LLM coding agents). 

While AI models generated the initial scaffolding, boilerplate schemas, FastAPI endpoints, and React components, the **human engineer acted as system architect, test director, and quality assurance lead**. 

The primary human contribution was executing **systematic manual edge-case testing** against the assignment's self-check requirements. This testing uncovered critical logical errors that AI models failed to anticipate.

---

## Code Base Contribution Breakdown

```
[ AI-Generated Foundation ] ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 80%
[ Human Architectural Lead ] ▓▓▓▓▓▓ 20%
```

- **~80% AI-Generated Code**: Initial database models, FastAPI router definitions, NetworkX graph utility classes, Pydantic schemas, Vite/React UI scaffolding, and Tailwind/CSS layouts.
- **~20% Human Architectural Direction & Redirection**: Graph localization algorithm design, bug root-cause diagnosis, test scenario definition, environment setup debugging (Docker network host resolution), and prompt redirection when AI generated overly complex or flawed implementations.

---

## "AI Was Wrong" Case Studies

AI models frequently write code that appears syntactically clean and compiles successfully, yet violates core domain logic. Below are 3 concrete case studies where AI-generated implementations were wrong, how they were caught through systematic testing, and how they were corrected.

### Case Study 1: Per-Pole Ticket Creation Across 3 Code Paths

- **AI Failure**: When prompted to implement telemetry fault localization, the AI generated telemetry ingestion routines that processed each dark pole individually. If a conductor snapped affecting 10 downstream poles, the AI logic triggered 10 independent database queries, creating 10 separate incident records and 10 distinct work order tickets.
- **How It Was Caught**: Executed a systematic span fault injection test. The test expectation was "1 span fault = 1 grouped incident". Instead, the UI operator console exploded with 10 separate tickets for the same physical fault.
- **How It Was Fixed**: The human engineer redirected the AI to collapse all boundary alerts into a single shared grouping method in `LocalizationService.py`. The algorithm now traverses downstream subtrees to emit exactly **1 Incident** per boundary span, and merges feeder-wide blackouts into a single `FEEDER_FAULT` incident.

---

### Case Study 2: Transformer-Fault Button Silently Wired to Feeder-Fault Endpoint

- **AI Failure**: During frontend simulator UI component generation, the AI generated a grid of action buttons ("Inject Span Fault", "Inject Transformer Fault", "Inject Feeder Fault"). The AI silently copied the onclick handler from the feeder fault button to the transformer fault button, pointing it to `/simulate/feeder`.
- **How It Was Caught**: Executed the "Transformer Fault vs Feeder Fault" self-check scenario. Clicking "Inject Transformer Fault" turned the entire 11kV feeder dark instead of isolating a single distribution transformer.
- **How It Was Fixed**: Inspected browser network trace logs, identified that `POST /simulate/feeder` was being invoked by the transformer button, and updated `SimulatorPanel.tsx` to explicitly invoke `POST /simulate/transformer?transformer_id=...`.

---

### Case Study 3: Dark Poles Counter Failing to Refresh in Top Stats Bar

- **AI Failure**: The AI wrote a React state hook in `DashboardStats.tsx` that fetched grid summary metrics (`/dashboard`) only when the component initially mounted (`useEffect` with empty dependency array `[]`).
- **How It Was Caught**: Repeatedly injected faults using the simulator panel while observing the top stats bar. The map rendered dark red nodes, but the "Dark Poles" counter remained stuck at `0`.
- **How It Was Fixed**: Updated the state management pipeline to dispatch custom state refresh events upon simulator action completion, ensuring the top stats bar dynamically polls and updates without requiring manual browser refreshes.

---

## Key Lessons Learned in AI Pair-Programming

1. **AI Cannot Perform End-to-End Systemic Verification**: AI models validate code in isolation. They do not naturally execute multi-step integration flows (e.g. verifying how a database write in backend step A impacts state hook rendering in frontend step B).
2. **Deterministic Code Outperforms LLMs for Core Logic**: Using LLMs for graph traversal or localization calculation introduces non-determinism and latency. Keeping localization in pure Python (NetworkX) while reserving AI strictly for on-demand text summaries ("Explain this fault") yielded a robust, fast system.
3. **Structured Testing is Mandatory**: Comprehensive self-check testing suites are the only reliable way to catch AI logic hallucinations before deployment.
