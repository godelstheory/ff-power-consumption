import logging

from os import path
from Energy_Consumption.experiment import Experiment, Tasks, Task
from helpers.io_helpers import log_to_stdout

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
log_to_stdout(logger, level=logging.DEBUG)

exp_id = 6


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [
            # wait for 2 minutes
            Task('time.sleep(300)', self.client, meta={'website': 'HOME'}),
            # go to Mozilla.org
            Task("https://www.google.com/')", self.client,
                 meta={'website': 'https://www.lingscars.com/'}),
            # wait for 2 minutes
            Task('time.sleep(600)', self.client, meta={'website': 'HOME'}),
        ]
        return tasks


""" DON'T MODIFY THE BELOW!!!!"""

exp_name = path.splitext(path.basename(__file__))[0]
exp = Experiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=1200)

exp.run()
