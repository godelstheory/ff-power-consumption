from Energy_Consumption.experiment import Experiment, Tasks, Task

task_1 = """self.client.navigate('http://mozilla.org')
        self.client.go_back()
        self.client.go_forward()
        """


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [Task("self.client.navigate('http://mozilla.org')", self.client,
                      meta={'website': 'http://mozilla.org'}),
                 Task("self.client.go_back()", self.client, meta={'website': 'HOME'}),
                 Task("self.client.go_forward()", self.client, meta={'website': 'http://mozilla.org'})
                 ]
        return tasks


exp = Experiment(exp_id=0, exp_name='Test Experiment', tasks=TasksTest())

exp.run()
