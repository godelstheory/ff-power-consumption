from os import path

from energy_consumption.reduction import experiment_reduction as reduce


# Sum all the performance counter tabs
# reducer = reduce.SumExperimentReducer(exp_id=1, exp_name='Experiment - EDA')
#
# df = reducer.run()
#
# df.to_csv(path.join(reducer.exp_dir_path, 'df_reduced.csv'))

# Filter all the performance counter tabs to '1'
reducer = reduce.Filter1ExperimentReducer(exp_id=1, exp_name='Experiment - EDA')

df = reducer.run()

df.to_csv(path.join(reducer.exp_dir_path, 'df_filter1_reduced.csv'))


