from os import path
from Energy_Consumption.experiment import Experiment, Tasks, Task

exp_id = 1


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
            Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go back HOME
            Task("self.client.go_back()", self.client, meta={'website': 'HOME'}),
            # wait for 2 minutes
            Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go to Mozilla.org
            Task("self.client.go_forward()", self.client, meta={'website': 'http://mozilla.org'}),
            # wait for 30 seconds
            Task('time.sleep(30)', self.client, meta={'website': 'HOME'}),
            # go to Twitch
            Task("self.client.navigate('https://www.twitch.tv')", self.client,
                 meta={'website': 'https://www.twitch.tv'}),
            # wait for 2 minutes
            Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go to Twitch: Fortnite
            Task("self.client.navigate('https://www.twitch.tv/directory/game/Fortnite')", self.client,
                 meta={'website': 'https://www.twitch.tv/directory/game/Fortnite'}),
            # wait for 2 minutes
            Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go to Twitch: Fortnite
            Task("self.client.navigate('https://www.twitch.tv/directory/game/Fortnite')", self.client,
                 meta={'website': 'https://www.twitch.tv/directory/game/Fortnite'}),

            # wait for 2 minutes
            Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
            # go to Firefox Add-ons, back and forward
            Task("self.client.navigate('https://addons.mozilla.org/en-US/firefox/'", self.client,
                 meta={'website': 'https://addons.mozilla.org/en-US/firefox/'}),
            Task("self.client.go_back()", self.client,
                 meta={'website': 'https://www.twitch.tv/directory/game/Fortnite'}),
            Task("self.client.go_forward()", self.client,
                 meta={'website': 'https://addons.mozilla.org/en-US/firefox/'}),
            # wait for 2 minutes
            Task('time.sleep(120)', self.client, meta={'website': 'HOME'}),
        ]
        return tasks


""" DON'T MODIFY THE BELOW!!!!"""

exp_name = path.splitext(path.basename(__file__))[0]
exp = Experiment(exp_id=exp_id, exp_name=exp_name, tasks=TasksTest())

exp.run()
