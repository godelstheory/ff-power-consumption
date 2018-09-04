from Energy_Consumption.experiment import Experiment, Tasks, Task


class TasksTest(Tasks):
    @property
    def tasks(self):
        tasks = [
            # wait for 2 minutes
            Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go to Mozilla.org
            Task("self.client.navigate('http://mozilla.org')", self.client,
                 meta={'website': 'http://mozilla.org'}),
            # wait for 2 minutes
            # Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go back HOME
            Task("self.client.go_back()", self.client, meta={'website': 'HOME'}),
            # wait for 2 minutes
            # Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go to Mozilla.org
            Task("self.client.go_forward()", self.client, meta={'website': 'http://mozilla.org'}),
            # wait for 30 seconds
            # Task('time.sleep(30)', self.client, meta={'website': 'HOME'}),
            # go to Twitch
            Task("self.client.navigate('https://www.twitch.tv')", self.client,
                 meta={'website': 'https://www.twitch.tv'}),
            # wait for 2 minutes
            # Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go to Twitch: Fortnite
            Task("self.client.navigate('https://www.twitch.tv/directory/game/Fortnite')", self.client,
                 meta={'website': 'https://www.twitch.tv/directory/game/Fortnite'}),
            # wait for 2 minutes
            # Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
        ]
        return tasks


exp = Experiment(exp_id=0, exp_name='Test Experiment', tasks=TasksTest())

exp.run()
