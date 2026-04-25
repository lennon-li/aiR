# aiR Product Plan and Description

## One-sentence product definition

**aiR helps users move from data and objective to interpretable results in R, then generates a review-ready HTML report of the analysis process, decisions, code, and results.**

It is **not** a web IDE.  
It is **not** a generic coding copilot.  
It is an **analysis coach with live R execution**.

---

## 1. Product definition

### Core idea
A user brings:
- data
- an analysis objective
- optionally an instruction document, protocol, or analysis plan

aiR then:
1. inspects the data
2. helps clarify the objective
3. proposes reasonable analysis options
4. guides the user through decisions
5. generates and runs R code live
6. shows outputs, plots, and intermediate results
7. explains what the results mean
8. produces an HTML report for expert review

### Product promise
**Upload your data, state your goal, and aiR helps you choose, run, and understand the right analysis in R.**

### Positioning
aiR is best described as:

**An R analysis guidance workspace for analysts, learners, and researchers who want help choosing, executing, and interpreting analyses.**

---

## 2. Who it is for

### Primary users
- mid-level analysts who know some R but are not fast or confident
- researchers who need help structuring analysis
- students learning applied statistics in R
- domain experts who can reason about data but are not strong programmers
- junior staff following instructions from a supervisor or statistician

### Not the main target
- expert R users who already prefer local RStudio + CLI agents + scripts
- users who mainly want a browser IDE
- users seeking a full notebook replacement

---

## 3. What problem it solves

Most users do not mainly struggle with typing R syntax.  
They struggle with:

- deciding what analysis to do
- translating an objective into a method
- understanding their data structure
- choosing among reasonable options
- avoiding silly mistakes
- interpreting outputs
- keeping a clear record of what was done
- handing work to an expert for review

aiR solves the workflow:

**question → method choice → code → execution → interpretation → review**

---

## 4. Product identity

### aiR is
- a guided analysis workspace
- data-aware
- objective-aware
- session-aware
- able to execute real R code
- able to explain and interpret results
- able to document the work

### aiR is not
- a browser clone of RStudio
- a generic coding chat app
- a plain web console for R
- a “do everything automatically” black box

---

## 5. Core user flow

### Entry screen
User sees two main options:

#### Option A: Start an analysis
Inputs:
- upload data or choose a sample dataset
- analysis objective
- optional: analysis instructions / protocol / plan

#### Option B: I’m just taking a peek
This skips strict onboarding and lets the user:
- load a sample dataset
- explore the interface
- lightly inspect data
- later refine an objective

---

## 6. Main workflow

### Step 1: Intake
User provides:
- data
- objective
- optional plan/instructions

If objective is vague, aiR asks a short clarifying question.

Examples:
- describe this dataset
- compare two groups
- model an outcome
- predict Y from X
- visualize patterns
- explore missingness
- fit and interpret a regression

### Step 2: Data understanding
aiR inspects:
- rows / columns
- variable types
- missingness
- likely outcomes / predictors
- obvious issues
- candidate analysis paths

### Step 3: Propose options
aiR says:

> Based on your objective and data, here are 2–3 reasonable ways to proceed.

For each option:
- what it does
- why it fits
- what assumptions matter
- what output to expect

It also recommends one path.

### Step 4: User chooses direction
User can:
- accept recommendation
- choose another option
- ask for simpler
- ask for more rigorous
- ask what assumptions matter

### Step 5: Guided execution in R
aiR:
- generates concise R code
- explains briefly what the step is doing
- runs it live
- shows output, plots, tables, and environment changes

### Step 6: Interpretation
aiR explains:
- what the result suggests
- what it does not imply
- what to check next
- what limitations or caveats exist

### Step 7: Continue / branch
aiR offers next actions:
- check assumptions
- refine model
- compare methods
- improve visualization
- summarize findings
- export report

---

## 7. Optional plan-guided mode

Users may optionally upload:
- supervisor instructions
- analysis plan
- protocol
- assignment instructions
- methods document
- internal SOP

aiR should then:

1. read the plan
2. extract requested steps
3. identify ambiguities
4. restate the interpreted plan
5. ask the user to confirm
6. turn the plan into guided executable R steps
7. log the decisions and outputs into the final report

### Important rule
aiR should **not blindly execute** a long plan immediately.

It should first say:
- what it thinks the plan means
- what assumptions it had to make
- what is missing
- what sequence it proposes

Then ask for confirmation.

---

## 8. Product behavior philosophy

### Default mode
The product should default to **coaching**, not full automation.

That means:
- objective first
- options proposed
- decisions guided
- execution available
- interpretation emphasized

### Slider
The learning/doing slider should not be the main identity anymore.

Recommendation:
- remove it from the primary entry flow
- keep it as an advanced setting or session preference later

The default should already feel guided and sensible.

---

## 9. Interface design

### Primary UI emphasis
The main UI should prioritize:
- objective
- dataset
- current recommended next step
- proposed options
- result interpretation
- report-building workflow

### Secondary UI elements
Still available, but not the center:
- console
- raw code
- environment
- history
- plots tab

### Layout recommendation
Three panels still make sense, but product emphasis changes:

#### Left
- objective
- coaching conversation
- proposed next step
- suggested options
- decision log snippets

#### Center
- R console / code execution
- concise code blocks
- run/send to console
- output

#### Right
- plots
- environment
- history
- report/export status

---

## 10. Memory and context model

aiR should not rely on vague model memory.  
It should assemble structured session context each turn.

### Always keep
- session objective
- selected dataset
- current step in analysis
- current recommended option
- last known environment summary

### Recent context
- last 4 user turns
- last 4 assistant turns
- last 3 assistant code blocks
- last 5 executed commands
- last error only

### Environment summary
Always include:
- object names
- classes
- dimensions
- dataframe columns
- likely active dataframe(s)

### Expanded mode
You proposed a trial default and a VIP unlock. That can stay as an implementation detail:
- trial = compact context
- AIRVIP = expanded context budget

But product-wise, users should experience this as:
- normal mode
- enhanced context mode

Not as a gimmick.

---

## 11. Live R execution

aiR should execute real R code in a live session.

### Requirements
- code runs live
- outputs return cleanly
- plots render correctly
- console history works
- session context is preserved
- environment updates are visible

### Important behavior
When the user asks for code:
- aiR should produce **concise executable R**
- not generic teaching prose
- not irrelevant fallback documentation
- not placeholders like `your_data_frame` if `df` exists

If user clicks “Send to Console,” it should:
- preserve multiline code
- run it exactly
- show results cleanly

---

## 12. Interpretation layer

This is one of the most important differentiators.

aiR should not stop at code execution.

It should explain:
- what the result means
- what is noteworthy
- what assumptions still matter
- what next decision the user should make
- what an expert reviewer would want checked

This makes aiR more than a code generator.

---

## 13. HTML report generation

This should be a core feature.

### Report purpose
The report is for:
- the user’s own record
- supervisor review
- statistician review
- expert validation
- assignment/project documentation

### Report contents

#### 1. Analysis objective
- original user objective
- any refined objective

#### 2. Dataset overview
- file/dataset name
- dimensions
- variable summary
- missingness summary
- important variables used

#### 3. Proposed options
- the options aiR suggested
- which one was chosen
- why it was chosen

#### 4. Decision log
A compact record of key choices:
- what method was selected
- what variables were used
- what assumptions were discussed
- any ambiguities resolved

#### 5. R code executed
- only the meaningful code
- deduplicated
- grouped by step

#### 6. Results
- key outputs
- tables
- plots
- model summaries

#### 7. Interpretation
- summary of findings
- caveats
- limitations
- what remains uncertain

#### 8. Expert review notes / next steps
- diagnostics still needed
- alternative methods worth considering
- areas needing expert confirmation

### Report style
Do **not** dump the full chat transcript.  
It should be a **structured analysis summary**, not a chat log.

---

## 14. Key product features

### Must-have
- upload data
- sample dataset option
- objective-first flow
- optional “just taking a peek”
- data inspection
- analysis option proposal
- user decision guidance
- live R execution
- plots / environment / history
- interpretation
- HTML report export

### Important but secondary
- optional instruction/plan ingestion
- concise code suggestion cards
- send to console
- command history
- session-aware object reuse

### Later
- advanced retrieval grounding
- broader package/library support
- collaboration / sharing
- expert review comments
- alternative report templates

---

## 15. What to avoid

To preserve aiR’s value, avoid becoming:
- a generic web IDE
- browser RStudio clone
- plain code chatbot
- generic data-science notebook clone

Also avoid:
- too many knobs
- too much infrastructure exposed to the user
- overemphasis on agent cleverness
- automatic execution without clarity

The surface should feel focused and intentional.

---

## 16. What makes aiR defensible

Not:
- “it can run R in the browser”

That is weak.

The real defensible value is:
- objective-aware guidance
- data-aware method choice
- session-aware code generation
- interpretation of results
- decision logging
- review-ready reporting

That combination is much stronger.

---

## 17. MVP definition

### MVP promise
A user can:
1. upload data or choose a sample dataset
2. state an objective
3. get 2–3 reasonable analysis options
4. choose a path
5. run guided R analysis
6. see outputs and plots
7. get interpretation
8. export an HTML report for expert review

### MVP does not need
- full IDE features
- enterprise doc ingestion
- complex multi-user collaboration
- complete package universe
- giant retrieval stack at launch

---

## 18. Product summary paragraph

**aiR is a guided R analysis workspace for analysts, learners, and researchers. Users bring data and an objective, and optionally an analysis plan. aiR inspects the data, proposes reasonable analysis options, helps the user choose a path, generates and runs R code live, explains the results, and creates a review-ready HTML report documenting the decisions, code, outputs, and interpretations. The product is designed to coach users through analysis rather than simply act as a browser-based IDE or generic coding copilot.**

---

## 19. One-sentence pitch options

### Option 1
**Upload your data, state your goal, and aiR guides you to interpretable results in R.**

### Option 2
**aiR helps users turn data, objectives, and optional analysis plans into guided, executable R analysis and review-ready reports.**

### Option 3
**aiR is an R analysis coach that helps users choose, run, and understand the right analysis using their own data.**

---

## 20. Recommendation

Build around this version:
- coaching first
- doing as support
- objective + data as the entry point
- option proposal as the core differentiator
- interpretation + HTML report as the output value

That gives aiR a real identity.
