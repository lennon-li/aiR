# r-service/plumber.R
library(plumber)
library(jsonlite)
library(googleAuthR)
library(googleCloudStorageR)
library(ragg)
library(tidyverse)

#* @get /health
function() {
  list(status = "alive")
}

#* @filter cors
function(res) {
  res$setHeader("Access-Control-Allow-Origin", "*")
  res$setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
  res$setHeader("Access-Control-Allow-Headers", "Content-Type")
  plumber::forward()
}

#* @post /execute
#* @serializer unboxedJSON
function(session_id = "anonymous", code = "", persist_bucket = "air-mvp-lennon-li-2026-storage") {
  # Handle missing or null inputs from JSON
  if (is.null(session_id) || session_id == "") session_id <- "anonymous"
  if (is.null(persist_bucket) || persist_bucket == "") persist_bucket <- "air-mvp-lennon-li-2026-storage"
  if (is.null(code)) code <- ""

  # Authenticate and set region
  if (!googleAuthR::gar_has_token()) {
    googleAuthR::gar_gce_auth()
  }
  Sys.setenv(GCS_DEFAULT_REGION = "us-central1")

  initial_search_path <- search()
  target_env <- new.env()
  gcs_state_path <- paste0("sessions/", session_id, "/snapshots/state.RData")
  local_state_path <- tempfile(fileext = ".RData")
  
  # Restore State from GCS
  has_state <- FALSE
  tryCatch({
    gcs_get_object(gcs_state_path, bucket = persist_bucket, saveToDisk = local_state_path, overwrite = TRUE)
    if (file.exists(local_state_path)) {
        load(local_state_path, envir = target_env)
        has_state <- TRUE
    }
  }, error = function(e) { })

  if (!exists(".air_plot_history", envir = target_env)) {
      assign(".air_plot_history", list(), envir = target_env)
  }
  plot_history <- get(".air_plot_history", envir = target_env)
  initial_objs <- ls(all.names = TRUE, envir = target_env)

  summarize_object <- function(name, env) {
    value <- get(name, envir = env)
    obj_type <- class(value)[1]
    details <- ""

    if (inherits(value, "data.frame")) {
      details <- paste0(nrow(value), " obs. of ", ncol(value), " variables")
    } else if (is.atomic(value) || is.list(value)) {
      details <- paste(length(value), ifelse(length(value) == 1, "element", "elements"))
    }

    list(name = name, type = obj_type, details = details)
  }
  
  tmp_plot <- tempfile(fileext = ".png")
  ragg::agg_png(tmp_plot, width = 800, height = 600, res = 72)
  
  stdout <- capture.output({
    result <- tryCatch({
      if (nchar(trimws(code)) > 0) {
        exprs <- parse(text = code)
        for (i in seq_along(exprs)) {
          visible_res <- withVisible(eval(exprs[i], envir = target_env))
          if (visible_res$visible) print(visible_res$value)
        }
      }
      "success"
    }, error = function(e) {
      return(paste("Error:", e$message))
    })
  })
  
  dev.off()

  current_search_path <- search()
  new_pkgs <- setdiff(current_search_path, initial_search_path)
  for (pkg in new_pkgs) {
    if (grepl("^package:", pkg)) try(detach(pkg, character.only = TRUE, force = TRUE), silent = TRUE)
  }

  gcs_plot_path <- NULL
  plot_url <- ""
  plot_paths <- list()
  if (file.exists(tmp_plot) && file.info(tmp_plot)$size > 3000) {
    rand_id <- basename(tempfile(pattern=""))
    plot_name <- paste0("plot_", format(Sys.time(), "%Y%m%d_%H%M%OS6"), "_", rand_id, ".png")
    gcs_plot_path <- paste0("sessions/", session_id, "/artifacts/", plot_name)
    gcs_upload(tmp_plot, bucket = persist_bucket, name = gcs_plot_path)
    
    plot_url <- paste0("https://storage.googleapis.com/", persist_bucket, "/", gcs_plot_path)
    plot_paths <- list(gcs_plot_path)
    plot_history <- c(gcs_plot_path, plot_history)
    assign(".air_plot_history", plot_history, envir = target_env)
  }
  if (file.exists(tmp_plot)) unlink(tmp_plot)

  final_objs <- ls(all.names = TRUE, envir = target_env)
  changed <- !identical(initial_objs, final_objs)
  objects_changed <- setdiff(final_objs, initial_objs)
  visible_objs <- final_objs[!grepl("^\\.", final_objs)]
  environment <- lapply(visible_objs, summarize_object, env = target_env)
  
  if (changed || !has_state || !is.null(gcs_plot_path)) {
      tryCatch({
        save(list = ls(all.names = TRUE, envir = target_env), file = local_state_path, envir = target_env)
        gcs_upload(local_state_path, bucket = persist_bucket, name = gcs_state_path)
      }, error = function(e) {
        print(paste("GCS Save Error:", e$message))
      })
  }
  
  if (file.exists(local_state_path)) unlink(local_state_path)

  # Consolidate output
  output_text <- paste(stdout, collapse = "\n")
  if (grepl("^Error:", result)) {
    output_text <- paste0(output_text, "\n", result)
  }

  list(
    status = if (grepl("^Error:", result)) "error" else "success",
    stdout = output_text,
    output = output_text,
    plots = plot_paths,
    plot_url = plot_url,
    environment = environment,
    objects_changed = objects_changed,
    error = if (grepl("^Error:", result)) result else NULL
  )
}
