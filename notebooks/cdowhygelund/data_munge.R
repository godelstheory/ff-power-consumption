library(jsonlite)
library(lubridate)
library(stringr)
library(ggplot2)
library(plyr)
library(dplyr)
library(readr)


get_seconds <- function(measures){
  timestamp <- hms(str_split(ymd_hms(measures[[1]]$timestamp), ' ')[[1]][2])
  start <- hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp)
  seconds <- NULL
  for (measure in measures){
    timestamp <- hms(str_split(ymd_hms(measure$timestamp), ' ')[[1]][2])
    seconds <- c(seconds, hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp) - start)
  }
  return(seconds)
}

get_process_data <- function(dir_path){
  process_data <- read_json(file.path(dir_path, 'ff_performance_processes_sampled_data.json'))
  names(process_data) <- paste(get_seconds(process_data), 's', sep='')
  return(process_data)
}

parse_counters_sum <- function(file_path, exp_bounds, tz='US/Pacific'){ #, include_addons=FALSE){
  # FIXME: Rewrite using dplyr 
  counters <- read_json(file_path)
  df <- data.frame(timestamp=as.POSIXct(character()), seconds=integer(), duration=integer(), counters=integer())
  for (counter in counters){
    duration <- 0
    counts <- 0
    memory <- 0
    for (tab_name in names(counter$tabs$tabs)) {
      tab <- counter$tabs$tabs[[tab_name]]
      duration = duration + tab$duration
      counts = counts + tab$dispatchCount
      memory = memory + tab$memory
    }
    # timestamp <- hms(str_split(ymd_hms(counter$timestamp), ' ')[[1]][2])
    timestamp <- with_tz(ymd_hms(counter$timestamp, tz=tz), 'UTC')
    seconds <- round(hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp))
    df <- rbind(df, list(timestamp=timestamp, seconds=seconds, 
                         duration=duration, counts=counts, memory=memory))
  }
  if (!is.null(exp_bounds)){
    df <- df[df$seconds>min(df$seconds)+exp_bounds[1] & df$seconds<min(df$seconds)+exp_bounds[2], ]
  }
  return(df)
}

parse_ipg <- function(file_path, tz='US/Pacific'){
  text = trimws(str_split(read_file(file_path), 'Total')[[1]][1])
  df <- read.csv(text = text, stringsAsFactors = FALSE)
  clean_time <-with_tz(strptime(str_extract(df$System.Time, '^[0-9]+:[0-9]+:[0-9]+'), 
                        format = "%H:%M:%S", tz=tz), tz='UTC')
  df$seconds <- (hour(clean_time))*60*60+minute(clean_time)*60+second(clean_time)
  return(df)
}

get_action <- function(file_path){
  #FIXME: Timezone support to UTC
  log <- read_json(file_path)
  log <- ldply(log, data.frame, stringsAsFactors=FALSE)
  action <- log$action[3]
  timestamp = hms(str_split(ymd_hms(log$timestamp[3]), ' ')[[1]][2])
  seconds <- hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp)
  return(list(action=action, seconds=seconds))
}

parse_log <- function(file_path){
  log <- read_json(file_path)
  log <- ldply(log, data.frame, stringsAsFactors=FALSE)
  return(log) 
}

parse_psutil <- function(file_path, tz='US/Pacific'){
  metrics <- read_json(file_path)
  metrics[[1]] <- NULL
  df <- ldply(metrics, data.frame, stringsAsFactors=FALSE)
  timestamp <- with_tz(ymd_hms(df$timestamp, tz=tz), tz='UTC')
  df$seconds <- round(hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp))
  return(df)
}

parse_battery_report <- function(file_path){
  samples <- read_json(file_path)
  bind_rows(samples) %>%
    mutate(level = ChargeCapacity/FullChargeCapacity, timestamp = ymd_hms(Timestamp)) %>%
    mutate(seconds = hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp)) -> df
  return(df)
}

get_data <- function(counter_file_path, ipg_file_path, psutil_file_path=NULL, 
                     battery_report_file_path=NULL, ...){
  df.counter <- parse_counters_sum(counter_file_path, ...)
  df.ipg <- parse_ipg(ipg_file_path)
  df.final <- merge(df.counter, df.ipg, by='seconds')
  df.final$stopwatch <- df.final$seconds - df.final$seconds[1]
  if (!is.null(psutil_file_path)){
    df.psutil <- parse_psutil(psutil_file_path)
    df.final <- merge(df.final, df.psutil, by='seconds')
  }
  if (!is.null(battery_report_file_path)){
    df.br <- parse_battery_report(battery_report_file_path)
    df.final <- merge(df.final, df.br, by='seconds')
  }
  return(df.final)
}

plot_clean_data <- function(df, log){
  idx = df$stopwatch[df$seconds==log$seconds]
  a <- ggplot(df, aes(stopwatch, CPU.Processor.Energy.Excess)) + 
    geom_line() + 
    geom_point() +
    geom_text(x=idx, y=0.75*max(df$CPU.Processor.Energy.Excess), 
              label=log$action, color='blue') + 
    geom_vline(xintercept = idx, linetype='dashed', color='red')
  c <- ggplot(df, aes(counts, CPU.Processor.Energy.Excess)) + 
    geom_line() + 
    geom_point() + 
    geom_text(x=idx, y=0.75*max(df$CPU.Processor.Energy.Excess), 
              label=log$action, color='blue') + 
    geom_vline(xintercept = idx, linetype='dashed', color='red')
  print(a)
  print(c)
}

get_perf_data <- function(dir_path, exp_bounds = NULL){
  # get the performance counters
  counter_file_path <- file.path(dir_path, 'ff_performance_processes_sampled_data.json')
  # get the battery consumption data
  ipg_file_path <- list.files(dir_path, pattern='ipg.*_1_.txt', full.names = TRUE)[1]
  # get the psutil data
  psutil_file_path <- file.path(dir_path, 'psutil_sampled_data.json')
  if (!file.exists(psutil_file_path)) psutil_file_path <- NULL
  # get the Windows battery report
  br_file_path <- file.path(dir_path, 'windows_battery_report_sampled_data.json')
  if (!file.exists(psutil_file_path)) psutil_file_path <- NULL
  # merge
  df <- get_data(counter_file_path, ipg_file_path, psutil_file_path = psutil_file_path, 
                 battery_report_file_path = br_file_path, exp_bounds = exp_bounds)
  return(df)
}

merge_perf_data <- function(exps){
  perf_merged <- list()
  for (exp in names(exps)){
    df <- exps[[exp]] %>%
      lapply(function(x) x$perf) %>%
      bind_rows() %>%
      add_column(exp = exp) %>% 
      rename(battery_drain = Cumulative.Processor.Energy_0.mWh.) %>%
      mutate(run_id = as.factor(run_id))
    perf_merged[[exp]] <- df
  }
  return(perf_merged)
}

# Primary method for importing performance counter and process data
get_exp_data <- function(dir_path='data/', exp_bounds=NULL){
  results <- list()
  for (exp_dir in list.dirs(dir_path, full.names = TRUE, recursive=FALSE)){
    exp <- basename(exp_dir)
    url <- str_split(exp, '_2019')[[1]][1]
    run_id <- length(results[[url]])+1
    perf <- get_perf_data(exp_dir, exp_bounds)
    perf$run_id <- run_id
    results[[url]][[run_id]] <- list(perf=perf, process=get_process_data(exp_dir))
  }
  return(results)
}
