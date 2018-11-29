from os import path

from structlog import get_logger
import logging

# from Energy_Consumption.experiment import Tasks, Task
from Energy_Consumption.psutil_experiment import PsUtilsExperiment
from Energy_Consumption.experiment import Tasks, Task


exp_id = 4
logger = get_logger()
logger.setLevel(logging.INFO)


class TasksTest(Tasks):
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
exp = PsUtilsExperiment(
    exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(),
    method_names=['cpu_stats', 'cpu_times']
)

exp.run()
