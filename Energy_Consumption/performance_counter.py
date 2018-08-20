import logging

from marionette_driver.marionette import Marionette

from mixins import NameMixin
from helpers.io_helpers import write_txt_file

logger = logging.getLogger(__name__)


class PerformanceCounterConnector(NameMixin):
    def __init__(self, client=None):
        if client is None:
            logger.info('{}: connecting to Marionette and beginning session')
            self.client = Marionette('localhost', port=2828)
            self.client.start_session()
        else:
            self.client = client

    def generate_counter_script(self):
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

    def dump_counters(self, file_path):
        counters = self.get_counters()
        write_txt_file(file_path, counters)
