import abc
import json
from datetime import datetime
from os import path

import pandas as pd

from energy_consumption.experiment import ExperimentMeta
from energy_consumption.data_streams.sampled_data import TIMESTAMP_FMT
from energy_consumption.reduction.performance_reduction import agg_sum, filter_one


class ExperimentReducer(ExperimentMeta):
    """
    Combines all of the various data streams into a single pandas DataFrame
    Performs time frame alignment of data streams: shifting to common clock, resampling to same time grid

    ability to serialize to a variety of formats
    """

    __metaclass__ = abc.ABCMeta

    @property
    def hobo_columns(self):
        return ['timestamp', 'rms_voltage', 'rms_current', 'active_pwr', 'active_energy',
                'apparent_pwr', 'power_factor', 'started', 'btn_up', 'btn_dwn', 'stopped',
                'end']

    @hobo_columns.setter
    def hobo_columns(self, _):
        raise AttributeError('{}: hobo_columns cannot be manually set'.format(self.name))

    @property
    def hobo_data_columns(self):
        return ['rms_voltage', 'rms_current', 'active_pwr', 'active_energy', 'apparent_pwr',
                'power_factor']

    @hobo_data_columns.setter
    def hobo_data_columns(self, _):
        raise AttributeError('{}: hobo_data_columns cannot be manually set'.format(self.name))

    def __init__(self, exp_id, exp_name, **kwargs):
        super(ExperimentReducer, self).__init__(exp_id, exp_name, **kwargs)

    def parse_exp(self, **kwargs):
        exp_file_path = kwargs.get('exp_file_path', self.experiment_file_path)
        return pd.read_json(exp_file_path, convert_dates=True, orient='records').sort_values('timestamp')

    def parse_perf(self, **kwargs):
        # TODO: use pandas.read_json
        perf_counter_file_path = kwargs.get('perf_counter_file_path', self.perf_counter_file_path)
        with open(perf_counter_file_path, 'r') as f:
            results = json.load(f)
        # massage timestamp into DateTime
        for x in results:
            x['timestamp'] = datetime.strptime(x['timestamp'], TIMESTAMP_FMT)
        raw_df = pd.DataFrame(results)
        reduce_df = self.reduce_perf_counters(raw_df).sort_values('timestamp')
        # make timestamp index
        reduce_df = reduce_df.set_index(pd.DatetimeIndex(reduce_df.timestamp)).drop('timestamp', axis=1)
        # upsample to 1s grid
        reduce_df = reduce_df.resample('s').ffill(limit=1).interpolate().dropna()
        return {'raw': raw_df, 'reduced': reduce_df}

    def parse_hobo(self, **kwargs):
        col_names = kwargs.get('col_names', self.hobo_columns)
        hobo_file_path = kwargs.get('hobo_file_path',
                                    path.join(self.exp_dir_path, 'exp_{}_hobo.csv'.format(self.exp_id)))

        hobo_df = pd.read_csv(hobo_file_path, parse_dates=[0, 1], header=1)
        if '#' in hobo_df:
            hobo_df = hobo_df.drop('#', axis=1)
        hobo_df.columns = col_names
        # hobo_df = hobo_df.set_index(pd.DatetimeIndex(hobo_df.timestamp)).drop('timestamp', axis=1)
        return hobo_df

    def merge(self, exp_df, counters_df, hobo_df, **kwargs):
        # merge: Perf counter to experiment
        results_df = self.merge_counters(exp_df, counters_df, **kwargs)
        # merge: Hobo logger to counters
        full_df = self.merge_hobo(results_df, hobo_df, **kwargs)
        return full_df

    def merge_hobo(self, results_df, hobo_df, **kwargs):
        apply_sync_offset = kwargs.get('apply_sync_offset', False)
        if apply_sync_offset:
            # find sync timestamp in both data frames
            hobo_sync = hobo_df.loc[~hobo_df.btn_dwn.isna(), 'timestamp'].iloc[0]
            exp_sync = results_df.index.to_series()[results_df.action == self.hobo_sync_log_tag].iloc[0]
            new_timestamp = hobo_df.timestamp + (exp_sync - hobo_sync)
            hobo_df = hobo_df.set_index(pd.DatetimeIndex(new_timestamp))
        else:
            hobo_df = hobo_df.set_index(pd.DatetimeIndex(hobo_df.timestamp))
        hobo_df = hobo_df.drop('timestamp', axis=1)
        full_df = results_df.join(hobo_df[self.hobo_data_columns], how='inner')
        return full_df

    def merge_counters(self, exp_df, counters_df, **kwargs):
        """
        Merges Marionette actions and Hobo sync to performance counters data frame

        :param exp_df:
        :param counters_df:
        :param kwargs:
        :return:
        """
        results_df = counters_df.copy()

        def get_action(timestamp):
            action = exp_df.action[exp_df.timestamp <= timestamp].iloc[-1]
            return action

        timestamps = results_df.index.to_series()
        results_df['action'] = timestamps.apply(get_action)

        if self.hobo_sync_log_tag not in results_df.action:
            sync_ts = exp_df.timestamp[exp_df.action == self.hobo_sync_log_tag].iloc[0]
            # find the closest timestamp
            results_df.action[(timestamps - sync_ts).abs().idxmin()] = self.hobo_sync_log_tag

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


class SumExperimentReducer(ExperimentReducer):
    """
    Performance Counter reduction using agg_top: sums all tabs
    """

    def reduce_perf_counters(self, raw_df):
        reduce_df = raw_df.tabs.apply(agg_sum)
        reduce_df['timestamp'] = raw_df['timestamp']
        return reduce_df


class Filter1ExperimentReducer(ExperimentReducer):
    """
    Performance Counter reduction using agg_top: sums all tabs
    """

    def reduce_perf_counters(self, raw_df):
        reduce_df = raw_df.tabs.apply(filter_one)
        reduce_df['timestamp'] = raw_df['timestamp']
        return reduce_df
