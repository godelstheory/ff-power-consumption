import logging

from os import path
from energy_consumption.experiment import Experiment, Tasks, Task
from energy_consumption.helpers.io_helpers import log_to_stdout

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.INFO)

exp_id = 6


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [
            # wait for 2 minutes
            Task('time.sleep(300)', self.client, meta={'website': 'HOME'}),
            # go to Mozilla.org
<<<<<<< HEAD
            Task("self.client.navigate('https://google.com')", self.client,
                 meta={'website': 'https://google.com/'}),
=======
            Task("https://www.google.com/')", self.client,
                 meta={'website': 'https://www.google.com/'}),
>>>>>>> 896f7fac4952d3242ce08dd1aee75f49c0f4b1fa
            # wait for 2 minutes
            Task('time.sleep(600)', self.client, meta={'website': 'HOME'}),
        ]
        return tasks


""" DON'T MODIFY THE BELOW!!!!"""

exp_name = path.splitext(path.basename(__file__))[0]
exp = Experiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=960)

exp.run()
