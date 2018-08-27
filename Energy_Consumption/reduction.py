import abc
import csv
import json
from datetime import datetime

import pandas as pd

from experiment import ExperimentMeta
from performance_counter import PerformanceCounterConnector as perf


class ExperimentReducer(ExperimentMeta):
    """
    Combines all of the various data streams into a single pandas DataFrame
    Performs time frame alignment of data streams: shifting to common clock, resampling to same time grid

    ability to serialize to a variety of formats
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, exp_id, exp_name, **kwargs):
        super(ExperimentReducer, self).__init__(exp_id, exp_name, **kwargs)

    def parse_exp(self, **kwargs):
        results = []
        exp_file_path = kwargs.get('exp_file_path', self.experiment_file_path)
        with open(exp_file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                results.append({'timestamp': datetime.strptime(row[0], perf.TIMESTAMP_FMT), 'action': row[1]})
        return pd.DataFrame(results).sort_values('timestamp')

    def parse_perf(self, **kwargs):
        perf_counter_file_path = kwargs.get('perf_counter_file_path', self.perf_counter_file_path)
        with open(perf_counter_file_path, 'r') as f:
            results = json.load(f)
        # massage timestamp into DateTime
        for x in results:
            x['timestamp'] = datetime.strptime(x['timestamp'], perf.TIMESTAMP_FMT)
        raw_df = pd.DataFrame(results)
        reduce_df = self.reduce_perf_counters(raw_df).sort_values('timestamp')
        return {'raw': raw_df, 'reduced': reduce_df}

    def merge(self, exp_df, counters_df, **kwargs):
        results_df = counters_df.copy()

        def get_action(timestamp):
            action = exp_df.action[exp_df.timestamp >= timestamp].iloc[0]
            return action

        results_df['action'] = results_df.timestamp.apply(get_action)
        return results_df

    def run(self, **kwargs):
        exp_results = self.parse_exp(**kwargs)
        perf_results = self.parse_perf(**kwargs)['reduced']
        final = self.merge(exp_results, perf_results, **kwargs)
        return final

    @abc.abstractmethod
    def reduce_perf_counters(self, raw_df):
        """
        Method to reduce by tab and nested data structure into a vector of values per timestamp.
        """
        pass


def agg_top(x):
    """
    Adds up all of the dispatchCount and duration values for each "tab". Ignores children.
    :param x:
    :return:
    """
    duration = 0
    dispatch_count = 0
    num_windows = len(x)
    for win_id, results in x.iteritems():
        duration += results['duration']
        dispatch_count += results['dispatchCount']
    return pd.Series({'duration': duration, 'dispatch_count': dispatch_count, 'num_windows': num_windows})


class AggExperimentReducer(ExperimentReducer):
    def reduce_perf_counters(self, raw_df):
        reduce_df = raw_df.tabs.apply(agg_top)
        reduce_df['timestamp'] = raw_df['timestamp']
        return reduce_df
