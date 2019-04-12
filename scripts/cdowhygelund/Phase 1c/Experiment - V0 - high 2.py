import logging

from os import path
from energy_consumption.experiment import Experiment, Tasks, Task
from energy_consumption.helpers.io_helpers import log_to_stdout
from energy_consumption.data_streams.sampled_data import PerformanceCounterRetriever, PsutilDataRetriever

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.INFO)

exp_id = 8


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [
            Task('time.sleep(300)', self.client, meta={'website': 'HOME'}),
            # go to Mozilla.org
            Task("self.client.navigate('https://twitch.com')", self.client,
                 meta={'website': 'https://twitch.com/'}),
            # wait for 2 minutes
            Task('time.sleep(600)', self.client, meta={'website': 'HOME'}),
        ]
        return tasks


""" DON'T MODIFY THE BELOW!!!!"""

exp_name = path.splitext(path.basename(__file__))[0]
sampled_data_retrievers = (PerformanceCounterRetriever(), PsutilDataRetriever())
exp = Experiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=960,
                 sampled_data_retrievers=sampled_data_retrievers)

exp.run()
