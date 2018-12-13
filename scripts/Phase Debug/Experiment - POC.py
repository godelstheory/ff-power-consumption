from os import path
from energy_consumption.experiment import PlugLoadExperiment, Tasks, Task

exp_id = 0


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [Task("self.client.navigate('http://mozilla.org')", self.client,
                      meta={'website': 'http://mozilla.org'}),
                 Task("self.client.go_back()", self.client, meta={'website': 'HOME'}),
                 Task("self.client.go_forward()", self.client, meta={'website': 'http://mozilla.org'})
                 ]
        return tasks


exp_name = path.splitext(path.basename(__file__))[0]
exp = PlugLoadExperiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksTest())

exp.run()
