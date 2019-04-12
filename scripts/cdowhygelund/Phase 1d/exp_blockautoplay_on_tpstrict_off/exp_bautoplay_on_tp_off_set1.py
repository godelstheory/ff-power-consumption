import logging
import time

from os import path
from energy_consumption.experiment import Experiment, Tasks, Task
from energy_consumption.helpers.io_helpers import log_to_stdout
import energy_consumption.data_streams.sampled_data as sd

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_to_stdout(logger, level=logging.DEBUG)


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
    ('cbs_article', 'https://www.cbsnews.com/news/how-did-an-eel-get-stuck-up-a-seals-nose/')
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
        sampled_data_retrievers=(sd.PerformanceProcessesRetriever(), sd.PsutilDataRetriever(),
                                 sd.WindowsBatteryReportRetriever()),
        prefs={'privacy.trackingprotection.enabled': False,
               "media.autoplay.default": 1}
    )

    exp.run(wait_interval=10)

    time.sleep(10)


samples_per_page = 4
for _ in range(samples_per_page):
    for exp_id, uri in pages:
        run_exp(exp_id, uri)
