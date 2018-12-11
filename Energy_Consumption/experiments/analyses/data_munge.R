library(jsonlite)
library(lubridate)
library(stringr)
library(ggplot2)
library(plyr)

parse_counters_sum <- function(file_path){
  counters <- read_json(file_path)
  df <- data.frame(timestamp=as.POSIXct(character()), seconds=integer(), duration=integer(), counters=integer())
  for (counter in counters){
    duration <- 0
    counts <- 0
    for (tab in counter$tabs) {
      duration = duration + tab$duration
      counts = counts + tab$dispatchCount
    }
    timestamp <- hms(str_split(ymd_hms(counter$timestamp), ' ')[[1]][2])
    seconds <- hour(timestamp)*60*60 + minute(timestamp)*60 + second(timestamp)
    df <- rbind(df, list(timestamp=ymd_hms(counter$timestamp), seconds=seconds, 
                         duration=duration, counts=counts))
  }
  return(df)
}

parse_ipg <- function(file_path){
  df <- read.csv(file_path, stringsAsFactors = FALSE)
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

get_data <- function(counter_file_path, ipg_file_path, psutil_file_path=NULL){
  df.counter <- parse_counters_sum(counter_file_path)
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
