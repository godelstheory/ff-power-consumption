import json
import logging
import threading
import time
from datetime import datetime
from os import path

import psutil

from marionette_driver.marionette import Marionette

from helpers.io_helpers import read_txt_file
from mixins import NameMixin

logger = logging.getLogger(__name__)

TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S.%f'


def get_now():
    return datetime.now().strftime(TIMESTAMP_FMT)


class PerformanceCounterConnector(NameMixin):

    def __init__(self, **kwargs):
        logger.info('{}: connecting to Marionette and beginning session')
        self.client = Marionette('localhost', port=2828)
        self.client.start_session()
        self.counters = []
        self.script_generator = kwargs.get('script_generator', self.generate_counter_script)

    @staticmethod
    def generate_counter_script():
        script = read_txt_file(path.join(path.dirname(__file__), 'retrieve_performance_counters.js'))
        return script

    def get_counters(self, script=None):
        with self.client.using_context(self.client.CONTEXT_CHROME):
            script = script if script is not None else self.generate_counter_script()
            counters = {'tabs': self.client.execute_script(script),
                        'timestamp': get_now()}
        return counters

    def append_counters(self, script=None):
        self.counters.append(self.get_counters(script=script))

    def dump_counters(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.counters, f, indent=4, sort_keys=True)


class PerformanceCounterTask(PerformanceCounterConnector):
    def __init__(self, interval=1, **kwargs):
        super(PerformanceCounterTask, self).__init__(**kwargs)
        self.interval = interval
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):
        while True:
            logger.debug('{}: grabbing performance counters'.format(self.name))
            self.append_counters()
            time.sleep(self.interval)


class CounterConnector(NameMixin):
    """TODO: make PerformanceCounterConnector a subclass
    of this
    """
    def __init__(self, interval=1, debug_arg=None):
        self.counters = []
        self.interval = interval
        self.debug_arg = (
            debug_arg or "grabbing performance counters")

    def start_thread(self):
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def get_counters(self, **kw):
        raise NotImplementedError

    def run(self, **_):
        while True:
            # TODO: end arg?
            logger.debug('%s:', self.name)
            logger.debug(self.debug_arg)
            self.append_counters()
            time.sleep(self.interval)

    def append_counters(self, **kw):
        self.counters.append(self.get_counters(**kw))

    def dump_counters(self, file_path):
        with open(file_path, 'w') as f:
            json.dump(self.counters, f, indent=4, sort_keys=True)


class PsUtilTask(CounterConnector):
    """Note: 1st element of counters will be the schema of which measures
    come from which psutil method calls. e.g., `syscalls` and `interrupts`
    come from `psutil.cpu_stats`.
    TODO: should I save this to a separate file?
    """
    def __init__(self, method_names=('cpu_stats', 'cpu_times')):
        super(PsUtilTask, self).__init__()
        self.method_names = method_names
        self.counters.append(self.gen_cpu_stat_names(method_names=method_names))

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
