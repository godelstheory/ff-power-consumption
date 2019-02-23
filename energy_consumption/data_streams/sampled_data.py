import abc
import json
# import lxml
# import subprocess
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
    def get_sample(self, **kwargs):
        return

    def run(self, duration, dir_path):
        thread = threading.Thread(target=self.collect, args=(duration, dir_path))
        thread.daemon = True
        thread.start()

    def collect(self, duration=None, dir_path=None):
        start = time.time()
        while duration is None or time.time() < start + duration:
            logger.debug(self.message)
            self.append_sample()
            time.sleep(self.interval)

        logger.debug("Dumping counters")
        self.dump_counters(dir_path)

    def append_sample(self, **kwargs):
        self.samples.append(self.get_sample(**kwargs))

    def dump_counters(self, dir_path):
        file_path = path.join(dir_path, self.file_name)
        with open(file_path, 'w') as f:
            json.dump(self.samples, f, indent=4, sort_keys=True)


class PsutilDataRetriever(SampledDataRetriever):
    """Note: 1st element of counters will be the schema of which measures
    come from which psutil method calls. e.g., `syscalls` and `interrupts`
    come from `psutil.cpu_stats`.
    """

    def __init__(self, interval=1, method_names=('cpu_stats', 'cpu_times', 'sensors_battery')):
        super(PsutilDataRetriever, self).__init__(interval=interval)
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

    def get_sample(self, **_):
        counters = {'timestamp': get_now()}
        for method_name in self.method_names:
            method = getattr(psutil, method_name)
            res = method()  # NamedTuples
            counters.update(dict(zip(res._fields, res)))
        return counters


class PerformanceCounterRetriever(SampledDataRetriever):
    JS_DIR_PATH = path.join(path.dirname(__file__), 'js')

    def __init__(self, interval=1):
        logger.debug("{}: instantiating".format(self.name))
        self._client = None
        self.perf_getter_script = read_txt_file(path.join(self.JS_DIR_PATH, 'retrieve_performance_counters.js'))
        super(PerformanceCounterRetriever, self).__init__(interval=interval)

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

    def start_client(self):
        logger.info('{}: connecting to Marionette and beginning session'.format(self.name))
        client = Marionette('localhost', port=2828)
        client.start_session()
        return client

    def get_sample(self, **kwargs):
        with self.client.using_context(self.client.CONTEXT_CHROME):
            counters = {'tabs': self.client.execute_script(self.perf_getter_script),
                        'timestamp': get_now()}
        return counters


class PerformanceProcessesRetriever(PerformanceCounterRetriever):
    """
    Anything Marionette based needs to be merged into single class due to sampling issues.
    """

    def __init__(self, interval=1):
        super(PerformanceProcessesRetriever, self).__init__(interval=interval)
        self.process_getter_script = read_txt_file(path.join(self.JS_DIR_PATH, 'retrieve_process_info.js'))

    @property
    def message(self):
        return '{}: sampling performance and process counters'.format(self.name)

    @property
    def file_name(self):
        return 'ff_performance_processes_sampled_data.json'

    def get_sample(self, **kwargs):
        counters = super(PerformanceProcessesRetriever, self).get_sample(**kwargs)
        with self.client.using_context(self.client.CONTEXT_CHROME):
            counters.update({'processes': self.client.execute_script(self.process_getter_script)})
        return counters

# class WindowsBatteryReportRetriever(SampledDataRetriever):
#
#     def __init__(self, interval=1):
#         super(WindowsBatteryReportRetriever, self).__init__(interval=interval)
#         self.__file_name = None
#
#     @property
#     def message(self):
#         return '{}: sampling Windows Battery Report'.format(self.name)
#
#     def get_battery_report(self, i):
#         batt_rep_file_path = path.join(self.output_dir_path, 'batter_report_{}.xml'.format(i))
#
#
#     def run(self):
#         i = 0
#         while True:
#             self.get_battery_report(i)
#             i += 1
#             time.sleep(self.interval)
#
#     @property
#     def file_name(self):
#         if self.file_name is None:
#             self.__file_name = get_temp_filename(None)
#         return self.__file_name
#
#     def get_counters(self, **kwargs):
#         subprocess.check_call(['powercfg', '/batteryreport', '/duration', 1, '/output', self.file_name, '/xml'])
