import abc
import csv
import json
from datetime import datetime
from os import path

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

    def parse_hobo(self, **kwargs):
        col_names = kwargs.get('col_names', ['timestamp', 'rms_voltage', 'rms_current', 'active_pwr', 'active_energy',
                                             'apparent_pwr', 'power_factor', 'started', 'btn_up', 'btn_dwn', 'stopped',
                                             'end'])
        hobo_file_path = kwargs.get('hobo_file_path',
                                    path.join(self.exp_dir_path, 'exp_{}_hobo.csv'.format(self.exp_id)))

        hobo_df = pd.read_csv(hobo_file_path, parse_dates=[0, 1], header=1)
        if '#' in hobo_df:
            hobo_df = hobo_df.drop('#', axis=1)
        hobo_df.columns = col_names
        return hobo_df

    def merge(self, exp_df, counters_df, hobo_df, **kwargs):
        # merge: Perf counter to experiment
        results_df = self.merge_counters(exp_df, counters_df, **kwargs)
        # merge: Hobo logger to counters
        self.merge_hobo(results_df, hobo_df, **kwargs)
        return results_df

    def merge_hobo(self, results_df, hobo_df, **kwargs):
        # find sync timestamp in both data frames
        hobo_sync = hobo_df.loc[~hobo_df.btn_dwn.isna(), ['timestamp', 'btn_dwn']].iloc[0]
        # TODO: Not implemented

    def merge_counters(self, exp_df, counters_df, **kwargs):
        # merge: Add experiment action to counters data frame
        results_df = counters_df.copy()

        def get_action(timestamp):
            action = exp_df.action[exp_df.timestamp <= timestamp].iloc[-1]
            return action

        results_df['action'] = results_df.timestamp.apply(get_action)

        if self.hobo_sync_log_tag not in results_df.action:
            sync_ts = exp_df.timestamp[exp_df.action == self.hobo_sync_log_tag].iloc[0]
            # find the closest timestamp
            results_df.action[(results_df.timestamp - sync_ts).abs().idxmin()] = self.hobo_sync_log_tag

        return results_df

    def run(self, **kwargs):
        exp_results = self.parse_exp(**kwargs)
        perf_results = self.parse_perf(**kwargs)['reduced']
        hobo_results = self.parse_hobo()
        final = self.merge(exp_results, perf_results, hobo_results, **kwargs)
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
