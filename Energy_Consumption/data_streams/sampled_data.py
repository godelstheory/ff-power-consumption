import abc
import json
import threading
import time
from datetime import datetime
from os import path

import psutil
from structlog import get_logger

from marionette_driver.marionette import Marionette

from helpers.io_helpers import read_txt_file
from mixins import NameMixin

logger = get_logger()

TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S.%f'


def get_now():
    return datetime.now().strftime(TIMESTAMP_FMT)


class SampledDataRetriever(NameMixin):
    __metaclass__ = abc.ABCMeta

    def __init__(self, interval=1):
        self.samples = []
        self.interval = interval

    @abc.abstractproperty
    def message(self):
        """ Log file message"""
        return

    def run(self):
        thread = threading.Thread(target=self.collect, args=())
        thread.daemon = True
        thread.start()

    @abc.abstractmethod
    def get_counters(self, **kwargs):
        return

    def collect(self):
        while True:
            logger.debug(self.message)
            self.append_sample()
            time.sleep(self.interval)

    def append_sample(self, **kwargs):
        self.samples.append(self.get_counters(**kwargs))

    def dump_counters(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.samples, f, indent=4, sort_keys=True)


class PsutilDataRetriever(SampledDataRetriever):
    """Note: 1st element of counters will be the schema of which measures
    come from which psutil method calls. e.g., `syscalls` and `interrupts`
    come from `psutil.cpu_stats`.
    """

    def __init__(self, method_names=('cpu_stats', 'cpu_times')):
        super(PsutilDataRetriever, self).__init__()
        logger.debug("{}: instantiating".format(self.name))
        self.method_names = method_names
        self.samples.append(self.gen_cpu_stat_names(method_names=method_names))

    def message(self):
        return '{}: sampling psutil'.format(self.name)

    @staticmethod
    def gen_cpu_stat_names(method_names=('cpu_stats', 'cpu_times')):
        "Some of these are platform-dependent"
        dct = {}
        for method_name in method_names:
            method = getattr(psutil, method_name)
            res = method()
            dct.update({field: method_name for field in res._fields})
        return dct

    def get_counters(self, **_):
        counters = {'timestamp': get_now()}
        for method_name in self.method_names:
            method = getattr(psutil, method_name)
            res = method()  # NamedTuples
            counters.update(dict(zip(res._fields, res)))
        return counters


class PerformanceCounterRetriever(SampledDataRetriever):

    def __init__(self):
        logger.debug("{}: instantiating".format(self.name))
        logger.info('{}: connecting to Marionette and beginning session')
        self.client = Marionette('localhost', port=2828)
        self.client.start_session()
        self.perf_getter_script = read_txt_file(path.join(path.dirname(__file__), 'retrieve_performance_counters.js'))
        super(PerformanceCounterRetriever, self).__init__()

    def get_counters(self, **kwargs):
        with self.client.using_context(self.client.CONTEXT_CHROME):
            counters = {'tabs': self.client.execute_script(self.perf_getter_script),
                        'timestamp': get_now()}
        return counters

    def message(self):
        return '{}: sampling performance counters'.format(self.name)

