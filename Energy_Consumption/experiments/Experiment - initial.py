from Energy_Consumption.experiment import Experiment, Tasks, Task

task_1 = """self.client.navigate('http://mozilla.org')
        self.client.go_back()
        self.client.go_forward()
        """


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [Task(task_1.strip(), self.client)]
        return tasks


exp = Experiment(exp_id=0, exp_name='Test Experiment', tasks=TasksTest())

exp.run()
