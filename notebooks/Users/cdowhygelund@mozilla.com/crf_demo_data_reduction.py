# Databricks notebook source
spark.conf.set('spark.databricks.queryWatchdog.enabled', False)

# COMMAND ----------

# MAGIC %md # Date Range

# COMMAND ----------

# MAGIC %md Configuration the date range to perform analysis. By default, query the last week

# COMMAND ----------

from datetime import datetime as dt, timedelta, date

now = date(2017, 4, 27)
# now = datetime.now().date()

start_date = dt.strftime(now - timedelta(6), "%Y%m%d")
end_date = dt.strftime(now, "%Y%m%d")

# COMMAND ----------

# MAGIC %md # Query Main Summary

# COMMAND ----------

probe_ms_map = {
  'TIME_TO_DOM_COMPLETE_MS': 'histogram_content_time_to_dom_complete_ms',
  'TIME_TO_DOM_INTERACTIVE_MS': 'histogram_content_time_to_dom_interactive_ms',
  'TIME_TO_DOM_LOADING_MS': 'histogram_content_time_to_dom_loading_ms',
  'TIME_TO_FIRST_INTERACTION_MS': 'histogram_content_time_to_first_interaction_ms',
  'TIME_TO_NON_BLANK_PAINT_MS': 'histogram_content_time_to_non_blank_paint_ms',
  'TIME_TO_RESPONSE_START_MS': 'histogram_content_time_to_response_start_ms'
}

# COMMAND ----------

# MAGIC %md Retrieve all probe data for builds that are within a week

# COMMAND ----------

probe_query = ',\n\t'.join(['COLLECT_LIST({0}) as {0}'.format(x) for x in probe_ms_map.values()])

# COMMAND ----------

ms_query = """
    SELECT 
        client_id, 
        SUBSTRING(app_build_id, 1, 8) as app_build_id,
        {0},
        COUNT(*) as num_client_pings
    FROM
        main_summary
    WHERE
        app_build_id >= '{1}'
        AND app_build_id <= '{2}'        
        AND app_name = 'Firefox'        
        AND normalized_channel = 'nightly'
        AND sample_id = '42'
    GROUP BY 1, 2
""".format(probe_query, start_date, end_date)

# COMMAND ----------

df = spark.sql(ms_query)

# COMMAND ----------

# MAGIC %md # Aggregate Client Histograms

# COMMAND ----------

probes = probe_ms_map.values()

# COMMAND ----------

from collections import defaultdict
from pyspark.sql.types import StructType, StructField, MapType, IntegerType, DoubleType
from pyspark.sql.functions import udf, col, struct

def agg_client_hists(*args):
  agg = []
  for probe in args[0]:
    agg.append(agg_client_probe(probe))
  return tuple(agg)

def apply_estimator(hist):
  return {x: y+1 for x, y in hist.iteritems()}

def unit_density(hist):
  weight = float(sum(hist.values()))
  return {x: y/weight for x, y in hist.iteritems()}

def agg_client_probe(hists):
  # sum ping histogram bins
  try:
    agg_hist = defaultdict(int)
    for hist in hists:
      for key, value in hist.iteritems():
        agg_hist[key] += value    
  except Exception:
    agg_hist = defaultdict(int)
  # Apply the Bayesian estimator (remove zeros)
  hist_v2 = apply_estimator(agg_hist)
  # normalize to unit density
  return unit_density(hist_v2)

schema = StructType([StructField(x, MapType(IntegerType(), DoubleType()), False) for x in probes])
agg_hist_udf = udf(agg_client_hists,  schema)

# COMMAND ----------

df = df.withColumn('hist_agg', agg_hist_udf(struct(*probes)))

# COMMAND ----------

# df.count()

# COMMAND ----------

# MAGIC %md # Poisson Bootstrap Replicates

# COMMAND ----------

NUM_REPS = 1000

# COMMAND ----------

from numpy.random import poisson, binomial
from pyspark.sql import Row

def get_ws(partition):     
    for profile in partition:
      weights = poisson(1, NUM_REPS).tolist()   
      yield ((profile.client_id, profile.app_build_id), {'weights': weights, 'hists': profile.hist_agg})

def weight_hists(profile):
  key, value = profile
  app_build_id = key[1]
  for i, w in enumerate(value['weights']):
    if w > 0:
      result = {
        'n': w,
        'hists': {x: weight_hist(w, getattr(value['hists'], x)) for x in probes}
      }    
      yield ((i, app_build_id), result)  

def weight_hist(w, hist):
  return {x:w*y for x, y in hist.iteritems()}

def sum_hists(a, b):
  results = {
    'hists': {},
    'n': a.get('n', 0) + b.get('n', 0)
  } 
  for probe in probes:
    results['hists'][probe] = sum_hist(a.get('hists', {}), b.get('hists', {}), probe)
  return results
    
def sum_hist(a, b, probe):  
  hist_a, hist_b = a.get(probe, {}), b.get(probe, {})
  result = {}
  for key in set(hist_a.keys()+hist_b.keys()):
    result[key] = hist_a.get(key, 0)+hist_b.get(key, 0)
  return result

def norm_hists(a): 
  key, value = a
  hists = {}
  for probe, hist in value['hists'].iteritems():
    hists[probe] = unit_density(hist)  
  return (key, hists)
  # return Row(rep=key[0], app_build_id=key[1], **hists)

# COMMAND ----------

hist_bts = df.rdd.mapPartitions(get_ws).flatMap(weight_hists).reduceByKey(sum_hists).map(norm_hists)

# COMMAND ----------

# hist_bts.count()

# COMMAND ----------

# MAGIC %md # Calculate RelDS

# COMMAND ----------

# MAGIC %md Retrieve unique builds across date range and generate a map for the relevant comparisons.

# COMMAND ----------

builds = sorted([x.app_build_id for x in df.select('app_build_id').distinct().collect()], reverse=True)

# COMMAND ----------

comps = {}
num_comps = len(builds)
for i in range(num_comps):
  result = []
  if i != (num_comps-1):
    result.append((i, 'test'))
  if i != 0:
    result.append((i-1, 'control'))
  comps[builds[i]] = result

# COMMAND ----------

# MAGIC %md Calculate the relevant comparisons for each build

# COMMAND ----------

def set_comp(a):
  key, value = a
  app_build_id = key[1]
  for comp in comps[app_build_id]:
    yield (comp[0], key[0]), (app_build_id, comp[1], value)
  
def calc_relds(a, b):    
  assert b[1] != a[1]  
  hists = [a[2], b[2]]
  c_idx = 0 if a[1]=='control' else 1
  controls = hists.pop(c_idx)
  tests = hists[0]
  app_build_id = a[0] if a[1]=='test' else b[0]
  return (calc_relds_stat(controls, tests), app_build_id)

def calc_relds_stat(controls, tests):
  results = {}
  for probe, control in controls.iteritems():
    test = tests.get(probe, {})
    crr = 0.0
    for key in control:
      p_c = control[key]
      p_t = test.get(key, 0.0)
      crr += abs(((p_c-p_t)/p_c))*((p_c+p_t)/2.0)
    results[probe] = crr
  return results

def finalize(a):
  key, value = a
  results = value[0]
  results['rep'] = key[1]
  results['app_build_id'] = value[1]
  return Row(**results)

# COMMAND ----------

final = hist_bts.flatMap(set_comp).reduceByKey(calc_relds).map(finalize).toDF()

# COMMAND ----------

# final.head(5)

# COMMAND ----------

# final.count()

# COMMAND ----------

# MAGIC %md Get ping and client counts for each build

# COMMAND ----------

df.createOrReplaceTempView('df')
build_stats = spark.sql("""
  SELECT 
    app_build_id,
    COUNT(*) as num_profiles,
    SUM(num_client_pings) as build_pings
  FROM df
  GROUP BY 1
  """).toPandas()

# COMMAND ----------

# MAGIC %md Determine quantiles across builds. Append number of profiles and number of pings used for calculation. Append the current date. 

# COMMAND ----------

import pandas as pd
from pyspark.sql.functions import pandas_udf, PandasUDFType, lit
from pyspark.sql.types import StringType, ArrayType, TimestampType
from datetime import datetime

quantiles = [0.25, 0.50, 0.75, 0.95]
relds_cols = ['relds_{}'.format(str(x)[2:]) for x in quantiles]

schema = StructType([StructField('probe', StringType(), False), StructField('app_build_id', StringType(), False),
                     StructField('num_profiles', IntegerType(), True),
                     StructField('num_pings', IntegerType(), True)] + 
                    [StructField(x, DoubleType(), False) for x in relds_cols]
                   )

@pandas_udf(schema, PandasUDFType.GROUPED_MAP)
def calculate_quantile(pdf):
  result_df = pdf[probes].quantile(quantiles)
  app_build_id = pdf.app_build_id.iloc[0]  
  app_build_df = build_stats[build_stats.app_build_id==app_build_id]
  num_profiles = app_build_df.num_profiles.iloc[0]
  num_pings = app_build_df.build_pings.iloc[0]
  results = []
  for probe in probes:
    result = {'probe':probe, 'app_build_id': app_build_id, 'num_profiles': num_profiles, 'num_pings': num_pings}
    result.update({relds_cols[i]: result_df[probe][x] for i,x in enumerate(quantiles)})
    results.append(result)
  final_df = pd.DataFrame(results)
  return final_df[['probe', 'app_build_id', 'num_profiles', 'num_pings'] + relds_cols]

relds = final.groupby('app_build_id').apply(calculate_quantile)
relds = relds.withColumn('creation_date', lit(now))

# COMMAND ----------

# MAGIC %md # Serialize

# COMMAND ----------

data_bucket = "telemetry-parquet"
s3path = "cdowhygelund/CRF/V0_3/relds"

output_file = 's3://{}/{}'.format(data_bucket, s3path)

relds.write.parquet(output_file, mode='append')