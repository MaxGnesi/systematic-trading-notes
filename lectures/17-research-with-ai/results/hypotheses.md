# Lecture 17: research with AI — plan fixed before any result

Proposed 2026-11-16, before any count or test of this lecture was run. To be agreed with the user; every later change is dated below with its reason. The lecture practises what it teaches: its own scope is locked here first (Lecture 1 §5.5, guardrail 1).

## The question (one sentence)

**What does an AI assistant change in quantitative research, where does it fail without a sound, and which habits catch those failures, judged on this course's own record?**

## Why it belongs here

Lectures 1-16 were built with an AI assistant (README, "How these notes were made"). Not saying so would be neither transparent nor useful: using AI well is now a core research skill. Lecture 17 closes the base layer with the method behind it, before Part V goes below the daily bar. It is a practical guide, not an essay on AI.

## Scope: what the lecture will and will not do

**Will:**
1. Show where the time goes in an AI-assisted project and what stays with the researcher (the delegate/keep table of Lecture 1 §5.5, expanded with examples).
2. Teach the brief: goal, what is ruled out, constraints, the plan fixed in advance; one bad and one good brief from this course.
3. Teach the lock (scope, search budget, tests, held-back data, change rules) and adaptation with discipline (cost against benefit, robustness, counted as a try).
4. Audit the course's own record: every error and correction logged in the plan files and the git history, classified, with how and when it was found.
5. Give the workflow to copy, as one checklist.

**Will not:** compare AI products or models; claim productivity numbers we did not measure; claim the course is error-free; teach prompt tricks that date in months.

## The empirical part: an audit of our own record

The one question our data can answer: **which kinds of error did AI-assisted research produce here, and which habit caught each one?**

- **Source, fixed now:** the dated plan files (`lectures/*/results/hypotheses.md`, "Correction" and "Data correction" entries) and the git history (commit messages naming a fix or correction), Lectures 1-16 only. Part V's record is out of scope.
- **Unit:** one error that reached a results entry, a figure or the lecture text (typos and layout fixes excluded).
- **Classified by, fixed now:**
  - *type:* data (missing or wrong series), method (a construction choice that was wrong), comparison (unlike samples or periods), claim (text stronger than or different from the evidence), reference (a detail of a paper);
  - *found by:* the user's review, a hand check in a notebook, redrawing a figure, a verification agent, a rerun on new data;
  - *when:* before any result, after results but before merging, after merging;
  - *silent or loud:* did the code still run and give plausible numbers?
- **Case studies, chosen now from errors already known:** VUSTX missing from a saved file (data, silent, found after merging); the monthly-against-daily Sharpe ratio claim (comparison, a start-date effect); value measured on total-return series (method, found before any return); reference details (initials, a paper's wording; found by a verification agent); the bet count in Lecture 11 and the excess-return correction in Lecture 12 (method).

## Three expectations

1. **Silent errors dominate the costly ones:** most errors found after merging are ones where the code ran and the numbers looked plausible (data and comparison errors), not ones that crashed.
2. **Human review and redrawing catch most method and claim errors;** automated checks (hand checks, verification agents) catch most data and reference errors.
3. **Errors caught before any result was computed cost the least:** they changed no verdict; those caught after merging needed reruns of several lectures.

## Measures

- Count of errors by type × found by, and by stage (one simple bar chart, one small table).
- For each error after merging: lectures rerun, numbers changed, verdicts changed.
- No significance tests: the counts are small and the classification is ours; the audit is descriptive and labelled as such.

## Verdict

Descriptive, read by the reader: the chart and the case studies, with a short labelled reading. Limits stated: one project, one assistant, one researcher; the classification is our judgment; errors never found are missing by definition.

## Outline (to confirm)

1. Key chart: the audit (errors by type, coloured by who caught them).
2. What changes with an assistant: speed, cheap tries, and why cheap tries make overfitting cheap.
3. The brief.
4. The lock and adaptation with discipline.
5. Verification habits: provenance, hand checks, redraw figures from data, references at the source, a second reader.
6. The audit and the case studies.
7. The workflow to copy (checklist) and transparency (how to disclose AI use).
8. Summary.

## Kept for later / exercises

- Exercise: lock a scope for your own variant of a Lecture 15 rule, run it with an assistant, and log every try and correction in the same format.
- Exercise: audit one of your own past projects with the same classification.
