# End-to-End MVP Demo Scenario

1.  **Onboarding:** 
    - Enter objective: "Explore correlation between MPG and Weight in mtcars."
    - Slide humanFirst to 20 (Doing).
    - Select sample dataset: "mtcars".
2.  **AI Proposal:**
    - Chat responds: "I will load the mtcars dataset and generate a summary."
    - Proposes: `data(mtcars); summary(mtcars)`.
3.  **Execution:**
    - User clicks "Run".
    - Code is sent to Control Plane, authenticated, and forwarded to R Runtime.
    - R Runtime restores (null) state, runs code, persists `.RData`, returns stdout.
4.  **UI Update:**
    - "Environment" pane shows `mtcars` dataframe.
    - "Results" console shows summary statistics.
5.  **Plotting:**
    - User asks: "Plot it."
    - AI Proposes: `plot(mtcars$wt, mtcars$mpg)`.
    - User runs code. R Runtime saves `.png` to GCS, Control Plane returns Signed URL.
    - "Plots" tab activates and renders the scatterplot.
6.  **Export:**
    - User clicks "Export Script".
    - Control Plane compiles execution history and serves a `.R` file download.
