import logging
import threading
import time

from marionette_driver.marionette import Marionette

from mixins import NameMixin
from helpers.io_helpers import write_txt_file, pickle_object

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
        script = """
          async function promiseSnapshot() {
            let counters = await ChromeUtils.requestPerformanceMetrics();
            let tabs = {};
            for (let counter of counters) {
              let {items, host, windowId, duration, isWorker, isTopLevel} = counter;
              // If a worker has a windowId of 0 or max uint64, attach it to the
              // browser UI (doc group with id 1).
              if (isWorker && (windowId == 18446744073709552000 || !windowId))
                windowId = 1;
              let dispatchCount = 0;
              for (let {count} of items) {
                dispatchCount += count;
              }
              let tab;
              if (windowId in tabs) {
                tab = tabs[windowId];
              } else {
                tab = {windowId, host, dispatchCount: 0, duration: 0, children: []};
                tabs[windowId] = tab;
              }
              tab.dispatchCount += dispatchCount;
              tab.duration += duration;
              if (!isTopLevel) {
                tab.children.push({host, isWorker, dispatchCount, duration});
              }
            }
            return {tabs, date: Cu.now()};
          }
          return promiseSnapshot();
        """
        return script

    def get_counters(self, script=None):
        with self.client.using_context(self.client.CONTEXT_CHROME):
            script = script if script is not None else self.generate_counter_script()
            counters = self.client.execute_script(script)
        return counters

    def append_counters(self, script=None):
        self.counters.append(self.get_counters(script=script))

    def dump_counters(self, file_path):
        raise NotImplementedError('Need to massage counters list into a csv file format or DB connection')
        # counters = self.get_counters()
        # write_txt_file(file_path, counters)


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


