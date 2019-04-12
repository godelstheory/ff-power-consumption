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

remove_bg <- function(df, log){
  model <- lm(Cumulative.Processor.Energy_0.mWh. ~ stopwatch, df[df$seconds<log$seconds, ])
  cleaned <- df$Cumulative.Processor.Energy_0.mWh.- predict(model, df)
  return(cleaned)
}