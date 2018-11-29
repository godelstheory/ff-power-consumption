import abc
import json
import threading
import time
from datetime import datetime
from os import path

import psutil
# from structlog import get_logger
import logging

from marionette_driver.marionette import Marionette

from helpers.io_helpers import read_txt_file
from mixins import NameMixin

logger = logging.getLogger(__name__)

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

    @abc.abstractproperty
    def file_name(self):
        """ Serialization file name"""
        return

    @abc.abstractmethod
    def get_counters(self, **kwargs):
        return

    def run(self):
        thread = threading.Thread(target=self.collect, args=())
        thread.daemon = True
        thread.start()

    def collect(self):
        while True:
            logger.debug(self.message)
            self.append_sample()
            time.sleep(self.interval)

    def append_sample(self, **kwargs):
        self.samples.append(self.get_counters(**kwargs))

    def dump_counters(self, dir_path):
        file_path = path.join(dir_path, self.file_name)
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

    @property
    def message(self):
        return '{}: sampling psutil'.format(self.name)

    @property
    def file_name(self):
        return 'psutil_sampled_data.json'

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
        self._client = None
        self.perf_getter_script = read_txt_file(path.join(path.dirname(__file__), 'js',
                                                          'retrieve_performance_counters.js'))
        super(PerformanceCounterRetriever, self).__init__()

    @property
    def client(self):
        # Lazy-load to ensure Firefox process has been started
        if self._client is None:
            self._client = self.start_client()
        return self._client

    @property
    def message(self):
        return '{}: sampling performance counters'.format(self.name)

    @property
    def file_name(self):
        return 'ff_perf_counter_sampled_data.json'

    @staticmethod
    def start_client():
        logger.info('{}: connecting to Marionette and beginning session')
        client = Marionette('localhost', port=2828)
        client.start_session()
        return client

    def get_counters(self, **kwargs):
        with self.client.using_context(self.client.CONTEXT_CHROME):
            counters = {'tabs': self.client.execute_script(self.perf_getter_script),
                        'timestamp': get_now()}
        return counters
