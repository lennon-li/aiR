# r-service/plumber.R
library(plumber)
library(jsonlite)
library(googleAuthR)
library(googleCloudStorageR)
library(ragg)

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
  tryCatch({
    gcs_get_object(gcs_state_path, bucket = persist_bucket, saveToDisk = local_state_path, overwrite = TRUE)
    if (file.exists(local_state_path)) load(local_state_path, envir = target_env)
  }, error = function(e) { 
    print(paste("GCS Restore Info:", e$message))
  })

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
  }
  if (file.exists(tmp_plot)) unlink(tmp_plot)

  tryCatch({
    save(list = ls(all.names = TRUE, envir = target_env), file = local_state_path, envir = target_env)
    gcs_upload(local_state_path, bucket = persist_bucket, name = gcs_state_path)
  }, error = function(e) {
    print(paste("GCS Save Error:", e$message))
  })
  
  if (file.exists(local_state_path)) unlink(local_state_path)

  objs <- ls(envir = target_env)
  obj_list <- lapply(objs, function(name) {
    obj <- get(name, envir = target_env)
    list(name = name, type = class(obj)[1], details = if(is.data.frame(obj)) paste(nrow(obj), "rows") else "object")
  })

  list(
    status = if(grepl("^Error:", result)) "error" else "success",
    error = if(grepl("^Error:", result)) result else NULL,
    stdout = paste(stdout, collapse = "\n"),
    plots = if(!is.null(gcs_plot_path)) as.list(gcs_plot_path) else list(),
    environment = obj_list
  )
}
