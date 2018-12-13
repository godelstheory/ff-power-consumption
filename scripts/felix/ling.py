import logging

from os import path
from energy_consumption.experiment import Experiment, Tasks, Task
from helpers.io_helpers import log_to_stdout

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.INFO)

exp_id = 'ling'


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [
            Task('time.sleep(30)', self.client, meta={'website': 'HOME'}),
            Task("self.client.navigate('https://lingscars.com/')", self.client,
                 meta={'website': 'https://lingscars.com/'}),
            Task('time.sleep(60)', self.client,
                 meta={'website': 'https://lingscars.com/'}),
            Task("self.client.navigate('about:newtab')", self.client,
                 meta={'website': 'HOME'}),
            Task('time.sleep(30)', self.client,
                 meta={'website': 'HOME'}),
        ]
        return tasks


""" DON'T MODIFY THE BELOW!!!!"""

exp_name = path.splitext(path.basename(__file__))[0]
exp = Experiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=120)

exp.run()
