# Task Execution Example Candidates

This document lists candidate tasks from the three benchmark evaluation runs
(`level1_20260427`, `level2_20260427`, `level3_20260428`) that demonstrate a
**planned reevaluation step** and finished with a result (correct or wrong).

---

## Candidate 1 — Find Removed Wikipedia Dragon Joke

**GAIA task:** Level 2  
**llimit task:** `1288d2a4-679f-40b9-80ad-49e8dc848091`  
**Result:** ❌ Wrong — predicted `Dragons are not real They are only found in fiction video games and occasionally on February 29th`, expected `Here be dragons`

**Question:**
> On a leap day before the year 2008, a joke was removed from the Wikipedia page for "Dragon". What was the phrase that was removed? Give the phrase as it appeared on the page, but without punctuation.

**Reevaluation pattern:** Conditional branch — the reevaluation step checks whether the search succeeded and either moves to formatting (success path) or triggers a new search strategy (fallback path).

### Execution flow

| Step | Type | Model | Description |
|------|------|-------|-------------|
| Planning | — | `google/gemini-3.1-pro-preview` | Plans: search for the edit → reevaluate |
| Step 1 | normal, `native_web_search` + `reasoning` | `google/gemini-2.5-flash` | Searches for the deleted joke on February 29, 2004 |
| Step 2 | **reevaluate** | `google/gemini-3.1-pro-preview` | Reads result; since a phrase was (apparently) found, generates a single formatting step |
| Step 3 | normal | `google/gemini-2.5-pro-preview` | Strips punctuation from the found phrase and outputs `Final Answer` |

**Why reevaluation was planned:** The planner noted that finding a specific Wikipedia edit from 2004 might require multiple attempts. The reevaluation was set up to branch: *if found → format; if not found → search revision history directly*. Step 1 returned a confident-looking result, so the success branch was taken.

**Why the result is wrong:** Step 1 hallucinated a plausible joke phrase. The actual deleted text ("Here be dragons") was never retrieved. The reevaluation faithfully processed the hallucinated result.

---

## Candidate 2 — Find Author's First Paper

**GAIA task:** Level 1  
**llimit task:** `42e6d957-5158-429e-a989-6004c17319eb`  
**Result:** ❌ Wrong — predicted `Interactive Visualization of Graphs and Trees`, expected `Mapping Human Oriented Information to Software Agents for Online Systems Usage`

**Question:**
> Of the authors (First M. Last) that worked on the paper "Pie Menus or Linear Menus, Which Is Better?" in 2015, what was the title of the first paper authored by the one that had authored prior papers?

**Reevaluation pattern:** Prerequisite-gating — the authors of the paper are not known at planning time, so no author-specific steps can be generated until step 1 identifies them.

### Execution flow

| Step | Type | Model | Description |
|------|------|-------|-------------|
| Planning | — | `google/gemini-3.1-pro-preview` | Plans: find authors → reevaluate |
| Step 1 | normal, `native_web_search` | `google/gemini-2.5-flash-lite` | Finds the 2015 paper and identifies authors: Per Ola Krüger, Eva Blomquist, Andreas Kerren |
| Step 2 | **reevaluate** | `google/gemini-3.1-pro-preview` | Receives the author list; generates two new steps to check publication histories and format the answer |
| Step 3 | normal, `native_web_search` + `reasoning` | `google/gemini-2.5-flash` | Searches each author's publication history; identifies Andreas Kerren as having the earliest paper (2000) |
| Step 4 | normal, `reasoning` | `google/gemini-2.5-pro-preview` | Formats final answer |

**Why reevaluation was planned:** The correct follow-up steps (e.g., "search publication history of X, Y, Z") could only be written once the authors were known. The reevaluation received the author list and immediately produced targeted steps.

**Why the result is wrong:** The model searched Andreas Kerren's history and found a 2000 paper, but Eva Blomquist apparently had an even earlier paper with the expected title. The model either missed it or chose the wrong candidate.

---

## Candidate 3 — Washington County Seats Population Difference

**GAIA task:** Level 2  
**llimit task:** `218c22c2-d3ae-4dba-a9e4-08c897e41ed5`  
**Result:** ❌ Wrong — predicted `735622`, expected `736455`

**Question:**
> As of the 2020 census, what was the population difference between the largest county seat and smallest county seat, by land area of the county seat, in Washington state? For population figures, please use the official data from data.census.gov. Please report the integer difference.

**Reevaluation pattern:** Prerequisite-gating — the specific city names cannot be known at planning time, so step 2 can only be planned once step 1 identifies them.

### Execution flow

| Step | Type | Model | Description |
|------|------|-------|-------------|
| Planning | — | `google/gemini-3.1-pro-preview` | Plans: find largest/smallest county seat by area → reevaluate |
| Step 1 | normal, `native_web_search` + `reasoning` | `google/gemini-2.5-flash-lite` | Searches land areas of all 39 Washington county seats; identifies Seattle (largest) and Pomeroy (smallest) |
| Step 2 | **reevaluate** | `google/gemini-3.1-pro-preview` | Receives Seattle + Pomeroy; generates two targeted steps: fetch census populations, then compute difference |
| Step 3 | normal, `native_web_search` | `google/gemini-2.5-flash` | Fetches 2020 census populations: Seattle 737,015 · Pomeroy 1,393 |
| Step 4 | normal, `reasoning` | `deepseek/deepseek-r1-0528` | Computes 737,015 − 1,393 = 735,622 and formats the answer |

**Why reevaluation was planned:** The planner explained: *"the specific county seats must be identified first before their populations can be accurately queried from the Census Bureau."* The reevaluation then created city-specific census lookup steps.

**Why the result is wrong:** The population figures retrieved in step 3 were slightly off (expected difference is 736,455). The city identification (Seattle/Pomeroy) was correct; the error is in the census data retrieval.

---

## Dismissed Candidates

### Carl Nebel Citation Image Date
**llimit task:** `d9715443-f795-4f5d-a017-16223b93e043`  
**Dismissed because:** The model hallucinated the citation URL — the FindAGrave link it "found" does not appear in the actual Wikipedia article, making the execution process unreliable as an example.

---

## Summary

| # | Task | Level | Result | Reevaluation pattern |
|---|------|-------|--------|----------------------|
| 1 | Wikipedia Dragon joke | 2 | ❌ (hallucinated) | Conditional branch |
| 2 | Author's first paper | 1 | ❌ (wrong author) | Prerequisite-gating |
| 3 | WA county seat populations | 2 | ❌ (off-by-~800) | Prerequisite-gating |
