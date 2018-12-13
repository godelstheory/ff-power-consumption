from os import path

from structlog import get_logger

# from energy_consumption.experiment import Tasks, Task
from scripts.wbeard.psutil_experiment import PsUtilsExperiment
from energy_consumption.experiment import Tasks, Task


exp_id = 4
logger = get_logger()


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
