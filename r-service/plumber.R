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
#* @param session_id The unique session ID
#* @param code The R code to execute
#* @param persist_bucket The GCS bucket name for state persistence
function(session_id, code, persist_bucket) {
  # Authenticate using the Cloud Run service account metadata
  if (!googleAuthR::gar_has_token()) {
    googleAuthR::gar_gce_auth()
  }

  initial_search_path <- search()
  target_env <- new.env()
  gcs_state_path <- paste0("sessions/", session_id, "/snapshots/state.RData")
  local_state_path <- tempfile(fileext = ".RData")
  
  # Restore State from GCS
  has_state <- FALSE
  tryCatch({
    # Only download if we don't have a local warm cache (optional future optimization)
    gcs_get_object(gcs_state_path, bucket = persist_bucket, saveToDisk = local_state_path, overwrite = TRUE)
    if (file.exists(local_state_path)) {
        load(local_state_path, envir = target_env)
        has_state <- TRUE
    }
  }, error = function(e) { 
    # Not an error if it's a new session
  })

  # Initialize or retrieve plot history from the target environment
  if (!exists(".air_plot_history", envir = target_env)) {
      assign(".air_plot_history", list(), envir = target_env)
  }
  plot_history <- get(".air_plot_history", envir = target_env)

  # Capture initial object names to detect changes
  initial_objs <- ls(all.names = TRUE, envir = target_env)
  
  tmp_plot <- tempfile(fileext = ".png")
  ragg::agg_png(tmp_plot, width = 800, height = 600, res = 72)
  
  stdout <- capture.output({
    result <- tryCatch({
      exprs <- parse(text = code)
      for (i in seq_along(exprs)) {
        visible_res <- withVisible(eval(exprs[i], envir = target_env))
        if (visible_res$visible) print(visible_res$value)
      }
      "success"
    }, error = function(e) {
      return(paste("Error:", e$message))
    })
  })
  
  dev.off()

  # Cleanup search path contamination (detach new libraries)
  current_search_path <- search()
  new_pkgs <- setdiff(current_search_path, initial_search_path)
  for (pkg in new_pkgs) {
    if (grepl("^package:", pkg)) try(detach(pkg, character.only = TRUE, force = TRUE), silent = TRUE)
  }

  # Artifacts and Persistence
  gcs_plot_path <- NULL
  if (file.exists(tmp_plot) && file.info(tmp_plot)$size > 3000) {
    rand_id <- basename(tempfile(pattern=""))
    plot_name <- paste0("plot_", format(Sys.time(), "%Y%m%d_%H%M%OS6"), "_", rand_id, ".png")
    gcs_plot_path <- paste0("sessions/", session_id, "/artifacts/", plot_name)
    gcs_upload(tmp_plot, bucket = persist_bucket, name = gcs_plot_path)
    
    # Update history
    plot_history <- c(gcs_plot_path, plot_history)
    assign(".air_plot_history", plot_history, envir = target_env)
  }
  if (file.exists(tmp_plot)) unlink(tmp_plot)

  # Check for changes before saving back to GCS (Speed optimization)
  final_objs <- ls(all.names = TRUE, envir = target_env)
  changed <- !identical(initial_objs, final_objs)
  
  if (changed || !has_state || !is.null(gcs_plot_path)) {
      tryCatch({
        save(list = ls(all.names = TRUE, envir = target_env), file = local_state_path, envir = target_env)
        gcs_upload(local_state_path, bucket = persist_bucket, name = gcs_state_path)
      }, error = function(e) {
        print(paste("GCS Save Error:", e$message))
      })
  }
  
  if (file.exists(local_state_path)) unlink(local_state_path)

  objs <- ls(envir = target_env)
  # Filter out internal tracking objects from the environment list
  objs <- objs[!grepl("^\\.air_", objs)]
  
  obj_list <- lapply(objs, function(name) {
    obj <- get(name, envir = target_env)
    list(name = name, type = class(obj)[1], details = if(is.data.frame(obj)) paste(nrow(obj), "rows") else "object")
  })

  list(
    status = if(grepl("^Error:", result)) "error" else "success",
    error = if(grepl("^Error:", result)) result else NULL,
    stdout = paste(stdout, collapse = "\n"),
    plots = if(length(plot_history) > 0) as.list(plot_history) else list(),
    environment = obj_list
  )
}
