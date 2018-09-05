from os import path

from Energy_Consumption.reduction import AggExperimentReducer

reducer = AggExperimentReducer(exp_id=1, exp_name='Experiment - EDA')

df = reducer.run()

df.to_json(path.join(reducer.exp_dir_path, 'df_reduced.json'))
