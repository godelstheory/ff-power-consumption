import json
import logging
import threading
import time
from os import path

from marionette_driver.marionette import Marionette

from mixins import NameMixin
from helpers.io_helpers import write_txt_file, pickle_object, read_txt_file

logger = logging.getLogger(__name__)


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
            counters = self.client.execute_script(script)
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
