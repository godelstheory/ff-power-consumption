# Databricks notebook source
# MAGIC %md Prototyping data pulls and plots in absence of shiny server access

# COMMAND ----------

# MAGIC %md # Data Retrieval

# COMMAND ----------

library(SparkR)

file_path <- "s3://telemetry-parquet/cdowhygelund/CRF/V0_3/relds"

relds <- read.parquet(file_path)

# COMMAND ----------

registerTempTable(relds, 'relds')

# COMMAND ----------

df <- sql("
  SELECT *
  FROM relds
  ORDER BY app_build_id DESC, creation_date DESC,  probe   
  ")

# COMMAND ----------

relds_df <- collect(df)

# COMMAND ----------

library(dplyr)

relds_df = relds_df %>% group_by(app_build_id) %>% filter(creation_date == max(creation_date))

# COMMAND ----------

# MAGIC %md Artifically add a threshold of 20% for testing purposes.

# COMMAND ----------

relds_df$thresh <- relds_df$relds_95 >= 0.30

# COMMAND ----------

# MAGIC %md Create an initial test plot

# COMMAND ----------

probes = unique(relds_df$probe)

# COMMAND ----------

library('ggplot2')

probe = probes[1]
probe_df = relds_df[relds_df$probe==probe, ]

cbPalette <- c("black", "red")
ggplot(probe_df, aes(x=app_build_id, y=relds_5, color=thresh, shape=thresh)) + 
  geom_point(aes(size=probe_df$num_profiles)) +
  geom_errorbar(aes(ymin=relds_25, ymax=relds_95), width=.1) +
  theme(axis.text.x = element_text(angle = 90, hjust = 1)) + 
  scale_colour_manual(values=cbPalette) +
  geom_hline(yintercept=0.30, linetype="dashed", color = "red") +
  theme(legend.position="none", panel.background = element_blank(), axis.line = element_line(colour = 'black'))+
  ggtitle(probe)