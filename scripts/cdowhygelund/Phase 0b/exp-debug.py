import logging

from os import path
from energy_consumption.experiment import Experiment, Tasks, Task
from helpers.io_helpers import log_to_stdout
import energy_consumption.data_streams.sampled_data as sd

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.INFO)

exp_id = 8


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [
            Task('time.sleep(10)', self.client, meta={'website': 'HOME'}),
            # go to Mozilla.org
            # Task("self.client.navigate('https://www.twitch.tv/')", self.client,
            Task("self.client.navigate('https://www.slate.com')", self.client,
                 meta={'website': 'https://twitch.com/'}),
            # wait for 2 minutes
            Task('time.sleep(10)', self.client, meta={'website': 'HOME'}),
        ]
        return tasks


""" DON'T MODIFY THE BELOW!!!!"""

exp_name = path.splitext(path.basename(__file__))[0]
sampled_data_retrievers = (sd.PerformanceCounterRetriever(), sd.PsutilDataRetriever(), sd.ProcessesRetriever())
# sampled_data_retrievers = (sd.PerformanceCounterRetriever(), sd.PsutilDataRetriever())
exp = Experiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=20,
                 sampled_data_retrievers=sampled_data_retrievers)

exp.run()
