from os import path

from helpers.io_helpers import log_to_stdout
import logging
from Energy_Consumption.experiment import Tasks, Task, Experiment
from Energy_Consumption.data_streams.sampled_data import PerformanceCounterRetriever, PsutilDataRetriever

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.INFO)
# from structlog import get_logger
# logger = get_logger()

exp_id = 100

class TasksDebug(Tasks):
    @property
    def tasks(self):
        tasks = [
            Task("self.client.navigate('http://mozilla.org')", self.client,
                 meta={'website': 'http://mozilla.org'}),
            Task('time.sleep(2)', self.client),
            Task("self.client.go_back()", self.client,
                 meta={'website': 'HOME'}),
            Task("self.client.go_forward()", self.client,
                 meta={'website': 'http://mozilla.org'})
        ]
        return tasks


exp_name = path.splitext(path.basename(__file__))[0]
sampled_data_retrievers=(PerformanceCounterRetriever(), PsutilDataRetriever())
exp = Experiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksDebug(), duration=60,
                 sampled_data_retrievers=sampled_data_retrievers)

exp.run()
