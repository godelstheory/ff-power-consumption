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

parse_counters_sum <- function(file_path, exp_bounds){ #, include_addons=FALSE){
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
    timestamp <- hms(str_split(ymd_hms(counter$timestamp), ' ')[[1]][2])
    seconds <- hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp)
    df <- rbind(df, list(timestamp=ymd_hms(counter$timestamp), seconds=seconds, 
                         duration=duration, counts=counts, memory=memory))
  }
  if (!missing(exp_bounds)){
    df <- df[df$seconds>min(df$seconds)+exp_bounds[1] & df$seconds<min(df$seconds)+exp_bounds[2], ]
  }
  return(df)
}

parse_ipg <- function(file_path){
  text = trimws(str_split(read_file(file_path), 'Total')[[1]][1])
  df <- read.csv(text = text, stringsAsFactors = FALSE)
  clean_time <- hms(str_extract(df$System.Time, '^[0-9]+:[0-9]+:[0-9]+'))
  df$seconds <- (hour(clean_time))*60*60+minute(clean_time)*60+second(clean_time)
  return(df)
}

get_action <- function(file_path){
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

parse_psutil <- function(file_path){
  metrics <- read_json(file_path)
  metrics[[1]] <- NULL
  df <- ldply(metrics, data.frame, stringsAsFactors=FALSE)
  timestamp <- ymd_hms(df$timestamp)
  df$seconds <- round(hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp))
  return(df)
}

get_data <- function(counter_file_path, ipg_file_path, psutil_file_path=NULL, ...){
  df.counter <- parse_counters_sum(counter_file_path, ...)
  df.ipg <- parse_ipg(ipg_file_path)
  df.final <- merge(df.counter, df.ipg, by='seconds')
  df.final$stopwatch <- df.final$seconds - df.final$seconds[1]
  if (!missing(psutil_file_path)){
    df.psutil <- parse_psutil(psutil_file_path)
    df.final <- merge(df.final, df.psutil, by='seconds')
  }
  return(df.final)
}

plot_data <- function(df, log=NULL, add_fit=TRUE){
  a <- ggplot(df, aes(stopwatch, Cumulative.Processor.Energy_0.mWh.)) + 
    geom_line() + 
    geom_point()
  b <- ggplot(df, aes(stopwatch, counts)) + 
    geom_line() + 
    geom_point()
  c <- ggplot(df, aes(counts, Cumulative.Processor.Energy_0.mWh.)) + 
    geom_line() + 
    geom_point()
  if(!missing(log)){
    idx = df$stopwatch[df$seconds==log$seconds]
    idx_pwr = df$Cumulative.Processor.Energy_0.mWh.[df$seconds==log$seconds]
    a <- a + 
      geom_text(x=idx, y=0.75*max(df$Cumulative.Processor.Energy_0.mWh.), 
                label=log$action, color='blue') + 
      geom_vline(xintercept = idx, linetype='dashed', color='red')
    b <- b + 
      geom_text(x=idx, y=0.75*max(df$counts), 
                label=log$action, color='blue') + 
      geom_vline(xintercept = idx, linetype='dashed', color='red')
    c <- c + 
      geom_text(x=idx, y=0.75*max(df$Cumulative.Processor.Energy_0.mWh.), 
                label=log$action, color='blue') + 
      geom_vline(xintercept = idx, linetype='dashed', color='red')
  }
  if(add_fit){
    a <- a +
      geom_smooth(method='lm')
  }
  print(a)
  print(b)
  print(c)
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

remove_bg <- function(df, log){
  model <- lm(Cumulative.Processor.Energy_0.mWh. ~ stopwatch, df[df$seconds<log$seconds, ])
  cleaned <- df$Cumulative.Processor.Energy_0.mWh.- predict(model, df)
  return(cleaned)
}

get_perf_data <- function(dir_path, exp_bounds = NULL){
  # get the performance counters
  counter_file_path <- file.path(dir_path, 'ff_performance_processes_sampled_data.json')
  # get the battery consumption data
  ipg_file_path <- list.files(dir_path, pattern='ipg.*_1_.txt', full.names = TRUE)[1]
  # merge
  df <- get_data(counter_file_path, ipg_file_path, exp_bounds = exp_bounds)
  return(df)
}

# Primary method for importing performance counter and process data
get_exp_data <- function(dir_path='data/', exp_bounds=NULL){
  results <- list()
  for (exp_dir in dir(dir_path, full.names = TRUE)){
    exp <- basename(exp_dir)
    url <- str_split(exp, '_2019')[[1]][1]
    run_id <- length(results[[url]])+1
    perf <- get_perf_data(exp_dir, exp_bounds)
    perf$run_id <- run_id
    results[[url]][[run_id]] <- list(perf=perf, process=get_process_data(exp_dir))
  }
  return(results)
}