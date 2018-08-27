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
                results.append({'timestamp': row[0], 'action': row[1]})
        return pd.DataFrame(results)

    def parse_perf(self, **kwargs):
        perf_counter_file_path = kwargs.get('perf_counter_file_path', self.perf_counter_file_path)
        with open(perf_counter_file_path, 'r') as f:
            results = json.load(f)
        # massage timestamp into DateTime
        for x in results:
            x['timestamp'] = datetime.strptime(x['timestamp'], perf.TIMESTAMP_FMT)
        raw_df = pd.DataFrame(results)

        return raw_df

    @abc.abstractmethod
    def reduce_perf_counters(self):
        """
        Method to reduce by tab and nested data structure into a vector of values per timestamp. 
        """
        pass




