import logging
import time
from random import shuffle

from os import path
from energy_consumption.experiment import Tasks, Task
from energy_consumption.tp100.experiment_tp100 import ExperimentTp100
from energy_consumption.helpers.io_helpers import log_to_stdout
import energy_consumption.data_streams.sampled_data as sd

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.DEBUG)


"""
Description: 

Testing Windows Priority Manager impact on power consumption (https://bugzilla.mozilla.org/show_bug.cgi?id=1556458). 

Start with a list of URIs:
1. Open Firefox and wait 60 seconds
2. Open the first URI and wait 60 seconds
3. Open a new tab, shift the focus, open the next URI and wait 60 seconds.
4. Repeat 3 for each URI.
5. Once each URI has been opened, shutdown Firefox. 
6. Change to the next set of prefs. Do steps 1-5

The above is done fives times for a total of # of prefs * 5 runs. 
"""

pages = [
    ('google', 'https://www.google.com'),
    ('youtube', 'https://www.youtube.com/'),
    ('youtube_vid', 'https://www.youtube.com/watch?v=87p53rAD7Sk'),
    ('espncricinfo', 'http://www.espncricinfo.com'),
    ('lingscars', 'https://www.lingscars.com'),
    ('slate', 'https://www.slate.com'),
    ('twitch', 'https://www.twitch.tv'),
    ('smh', 'https://www.smh.com.au'),
    ('nytimes', 'https://www.nytimes.com'),
    ('cbc_article', 'https://www.cbc.ca/radio/asithappens/as-it-happens-friday-edition-1.4936736/researchers-don-t-know-why-seals-are-getting-eels-stuck-in-their-noses-1.4936743'),
    ('bbc_article', 'https://www.bbc.co.uk/news/world-us-canada-46487944'),
    ('cbs_article', 'https://www.cbsnews.com/news/how-did-an-eel-get-stuck-up-a-seals-nose/'),
    ('popsci_article', 'https://www.popsci.com/seal-eel-nose'),
    ('livescience_article', 'https://www.livescience.com/64249-seal-eel-stuck-nose.html'),
    ('newsweek_article', 'https://www.newsweek.com/hawaii-seal-gets-eel-stuck-nose-1244770'),
    ('cnn_article', 'https://www.cnn.com/2018/12/07/americas/seals-eels-nostril-hawaii-intl-scli/index.html'),
    ('cnet_article', 'https://www.cnet.com/news/eel-snorting-seal-gets-help-from-nosy-scientists/'),
    ('rt_article', 'https://www.rt.com/usa/445963-hawaiian-monk-seal-eel-nose/'),
    ('gizmodo_article', 'https://gizmodo.com/dumbass-seal-gets-an-eel-stuck-in-his-nose-1830898375'),
    ('mashable_article', 'https://mashable.com/article/seal-with-eel-up-its-nose/#QJda7ruy7mqk'),
    ('google_doc', 'https://docs.google.com/document/d/1n1Hj64Gd-y5z1J9UXKcssSSeAyme1TixPS0RruQZFAE/edit?usp=sharing'),
    ('google_pres', 'https://docs.google.com/presentation/d/1Xzfn3tM5ZpymenzhRuaj9sdJaMECb71DFYE48n-ml7g/edit')
]

exp_prefs = {
    'cohort_1': {'privacy.trackingprotection.enabled': True,
                "media.autoplay.default": 0,
                "dom.ipc.processPriorityManager.enabled": True},
    'cohort_2': {'privacy.trackingprotection.enabled': True,
                "media.autoplay.default": 0,
                "dom.ipc.processPriorityManager.enabled": False},
    'cohort_3': {'privacy.trackingprotection.enabled': True,
                "media.autoplay.default": 1,
                "dom.ipc.processPriorityManager.enabled": True},
    'cohort_4': {'privacy.trackingprotection.enabled': True,
                "media.autoplay.default": 1,
                "dom.ipc.processPriorityManager.enabled": False},
}


def run_exp(exp_id, uris, **kwargs):
    prefs = kwargs.get('prefs', {})

    class TasksTest(Tasks):
        @property
        def tasks(self):
            c = "h = self.client.open(type='tab', focus=True)\nself.client.switch_to_window(h['handle'], focus=True)"
            tasks = [Task("time.sleep(2)", self.client)]
            Task("self.client.navigate('about:blank')", self.client, meta={'website': 'HOME'}),
            for uri in uris:
                tasks.extend([
                    # Task("time.sleep(30)", self.client),
                    Task(c, self.client, meta={'task': 'newtab_open'}),
                    Task("self.client.navigate('{}')".format(uri[1]), self.client, meta={'website': uri[0]}),
                    Task("time.sleep(60)", self.client)
                    # Task("time.sleep(2)", self.client)
                ]
                )
            return tasks

    exp_name = path.splitext(path.basename(__file__))[0]
    exp = ExperimentTp100(
        exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=1350,
        sampled_data_retrievers=(sd.PerformanceProcessesRetriever(), sd.PsutilDataRetriever(),
                                 sd.WindowsBatteryReportRetriever()),
        prefs=prefs,
        battery_thresh=(75, 95)
    )

    exp.run(wait_interval=10, split_task=False)

    time.sleep(10)


samples_per_page = 10
shuffles = 5
for j in range(shuffles):
    shuffle(pages)
    for i in range(samples_per_page):
        for cohort, prefs in exp_prefs.iteritems():
            run_exp('run_{}_shuff_{}_{}'.format(i, j, cohort), pages, prefs=prefs)
