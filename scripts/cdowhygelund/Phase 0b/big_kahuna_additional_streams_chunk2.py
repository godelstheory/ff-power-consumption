import logging
import time

from os import path
from energy_consumption.experiment import Experiment, Tasks, Task
from energy_consumption.helpers.io_helpers import log_to_stdout
from energy_consumption.data_streams.sampled_data import PerformanceProcessesRetriever, PsutilDataRetriever

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.DEBUG)


pages = [
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


def run_exp(exp_id, uri):
    class TasksTest(Tasks):
        @property
        def tasks(self):
            tasks = [
                Task("self.client.navigate('about:blank')", self.client,
                     meta={'website': 'HOME'}),
                Task('time.sleep(60)', self.client, # Deal with ghost windows
                     meta={'website': 'HOME'}),
                Task("self.client.navigate('{}')".format(uri), self.client,
                     meta={'website': uri}),
                Task('time.sleep(60)', self.client,
                     meta={'website': uri}),
                Task("self.client.navigate('about:blank')", self.client,
                     meta={'website': 'HOME'}),
                Task('time.sleep(30)', self.client,
                     meta={'website': 'HOME'}),
                # One last task to keep the browser alive while we dump counters
                Task('time.sleep(5)', self.client,
                     meta={'website': 'HOME'}),
            ]
            return tasks

    exp_name = path.splitext(path.basename(__file__))[0]
    exp = Experiment(
        exp_id=exp_id, exp_name=exp_name, tasks=TasksTest(), duration=150,
        sampled_data_retrievers=(PerformanceProcessesRetriever(), PsutilDataRetriever())
    )

    exp.run(wait_interval=10)
    time.sleep(10)


samples_per_page = 5
for _ in range(samples_per_page):
    for exp_id, uri in pages:
        run_exp(exp_id, uri)
