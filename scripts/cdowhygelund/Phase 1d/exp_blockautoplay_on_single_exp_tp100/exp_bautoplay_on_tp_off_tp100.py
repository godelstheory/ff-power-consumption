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

To determine how well IPG metrics correspond to battery drain, as reported by psutil and Windows
Battery Report. This requires running a single experiment for long enough to acquire sufficient
samples of the latter, rather coarse, measures.  
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


def run_exp(exp_id, uris):
    class TasksTest(Tasks):
        @property
        def tasks(self):
            tasks = [Task("time.sleep(60)", self.client)]
            for uri in uris:
                tasks.extend([
                    Task("self.client.navigate('about:blank')", self.client, meta={'website': 'HOME'}),
                    Task("time.sleep(30)", self.client),
                    Task("self.client.navigate('{}')".format(uri[1]), self.client, meta={'website': uri[0]}),
                    Task("time.sleep(60)", self.client)
                ]
                )
            return tasks

    exp_name = path.splitext(path.basename(__file__))[0]
    exp = ExperimentTp100(
        exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=2100,
        sampled_data_retrievers=(sd.PerformanceProcessesRetriever(), sd.PsutilDataRetriever(),
                                 sd.WindowsBatteryReportRetriever()),
        prefs={'privacy.trackingprotection.enabled': False,
               "media.autoplay.default": 1},
        battery_thresh=(40, 90)
    )

    exp.run(wait_interval=10)

    time.sleep(10)


samples_per_page = 10
for i in range(samples_per_page):
    shuffle(pages)
    run_exp('run_{}'.format(i), pages)
