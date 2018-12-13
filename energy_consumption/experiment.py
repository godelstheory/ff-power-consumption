import abc
import glob
import json
import logging
import subprocess
import sys
import time
import traceback
from os import path, getcwd

from marionette_driver.marionette import Marionette

from helpers.io_helpers import get_usr_input, make_dir
from mixins import NameMixin
from battery import IntelPowerGadget, read_ipg
from performance_counter import PerformanceCounterTask, get_now

logger = logging.getLogger(__name__)


class ExperimentMeta(NameMixin):
    def __init__(self, exp_id, exp_name, **kwargs):
        self.exp_id = exp_id
        self.__exp_name = exp_name
        self.__exp_dir_path = kwargs.get(
            'exp_dir_path',
            path.join(getcwd(), 'exp_{}_{}'.format(
                exp_id, time.strftime('%Y%m%d_%H%M%S'))
            )
        )

    @property
    def exp_name(self):
        return self.__exp_name

    @exp_name.setter
    def exp_name(self, _):
        raise AttributeError('{}: exp_name cannot be manually set'.format(self.name))

    @property
    def exp_dir_path(self):
        return self.__exp_dir_path

    @exp_dir_path.setter
    def exp_dir_path(self, _):
        raise AttributeError('{}: exp_dir_path cannot be manually set'.format(self.name))

    @property
    def perf_counter_file_path(self):
        return path.join(self.__exp_dir_path, '{}_{}_perf_counters.json'.format(self.exp_name, self.exp_id))

    @perf_counter_file_path.setter
    def perf_counter_file_path(self, _):
        raise AttributeError('{}: perf_counter_file_path cannot be manually set'.format(self.name))

    @property
    def experiment_file_path(self):
        return path.join(self.exp_dir_path, '{}_{}_experiment.json'.format(self.exp_name, self.exp_id))

    @experiment_file_path.setter
    def experiment_file_path(self, _):
        raise AttributeError('{}: experiment_file_path cannot be manually set'.format(self.name))


class Experiment(ExperimentMeta):
    """
    Runs the experiment: fires up performance counters, ensures all data logging pieces in place, fires off Marionette tasks
    """

    COUNTER_CLASS = PerformanceCounterTask

    def __init__(self, exp_id, exp_name, tasks, **kwargs):
        super(Experiment, self).__init__(exp_id, exp_name, **kwargs)
        self.__perf_counters = None
        self.__results = []
        self.__tasks = tasks
        self.__ff_process = None
        self.__ff_exe_path = kwargs.get('ff_exe_path', self.get_ff_default_path())
        self.__ipg = None
        # ensure the experiment results directory exists and is cleaned out
        make_dir(self.exp_dir_path, clear=True)
        self.duration = kwargs.get('duration', 60)
        self.start_time = None

    def get_ff_default_path(self):
        platform = sys.platform.lower()
        if platform == 'darwin':
            ff_exe_path = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
        elif platform == 'win32':
            ff_exe_path = 'C:/Program Files/Firefox Nightly/firefox.exe'
        else:
            raise ValueError('{}: {} platform currently not supported'.format(self.name, platform))
        return ff_exe_path

    @property
    def ff_exe_path(self):
        return self.__ff_exe_path

    @ff_exe_path.setter
    def ff_exe_path(self, _):
        raise AttributeError('{}: ff_exe_path cannot be manually set'.format(self.name))

    @property
    def perf_counters(self):
        if self.__perf_counters is None:
            self.__perf_counters = self.COUNTER_CLASS()
        return self.__perf_counters

    @perf_counters.setter
    def perf_counters(self, value):
        raise AttributeError('{}: perf_counters cannot be manually set'.format(self.name))

    @property
    def results(self):
        return self.__results

    @results.setter
    def results(self, value):
        raise AttributeError('{}: results cannot be manually set'.format(self.name))

    @property
    def tasks(self):
        return self.__tasks

    @tasks.setter
    def tasks(self, value):
        raise AttributeError('{}: tasks cannot be manually set'.format(self.name))

    @property
    def ff_process(self):
        return self.__ff_process

    @ff_process.setter
    def ff_process(self, _):
        raise AttributeError('{}: ff_process cannot be manually set'.format(self.name))

    @property
    def ipg_results_path(self):
        return path.join(self.exp_dir_path, 'ipg_{}'.format(self.exp_id))

    @ipg_results_path.setter
    def ipg_results_path(self, _):
        raise AttributeError('{}: ipg_file_path cannot be manually set'.format(self.name))

    @staticmethod
    def start_client():
        client = Marionette('localhost', port=2828)
        client.start_session()
        return client

    def initialize(self, **kwargs):
        logger.debug('{}: initializing experiment'.format(self.name))
        # start Firefox in Marionette mode subprocess
        self.__ff_process = subprocess.Popen(['{}'.format(self.ff_exe_path), '--marionette'])
        # Initialize client on tasks
        self.tasks.client = self.start_client()
        # connect to Firefox, begin collecting counters
        _ = self.perf_counters
        # fire up Intel Power Gadget
        self.initialize_ipg(**kwargs)
        # log the experiment start
        self.results.append({'timestamp': get_now(),
                             'action': '{}: Starting {}/{}'.format(self.name, self.exp_id, self.exp_name)})

    def initialize_ipg(self, **kwargs):
        logger.info('{}: Starting Intel Power Gadget to record for {}'.format(self.name, self.duration))
        self.__ipg = IntelPowerGadget(duration=self.duration, output_file_path=self.ipg_results_path)
        self.start_time = time.time()

    def run(self, **kwargs):
        # begin experiment: start Firefox and logging performance counters
        self.initialize(**kwargs)
        # run tasks
        self.perform_experiment(**kwargs)
        # end experiment
        self.finalize()

    def perform_experiment(self, **kwargs):
        self.results.extend(self.tasks.run(**kwargs))

    def serialize(self):
        with open(self.experiment_file_path, 'wb') as f:
            json.dump(self.results, f, indent=4, sort_keys=True)
        # with open(self.experiment_file_path, 'wb') as csv_file:
        #     writer = csv.writer(csv_file, delimiter=',')
        #     for result in self.results:
        #         writer.writerow(list(result))

    def finalize(self, **kwargs):
        wait_interval = kwargs.get('wait_interval', 60)
        # serialize performance counters
        self.perf_counters.dump_counters(self.perf_counter_file_path)
        # save the experiment log
        self.results.append({'timestamp': get_now(),
                             'action': '{}: Ending {}/{}'.format(self.name, self.exp_id, self.exp_name)})
        self.serialize()
        # wait to finish until Intel Power Gadget is done
        while (time.time() - self.start_time) < self.duration:
            wait_time = self.duration - (time.time() - self.start_time)
            logger.debug('{}: Waiting {} sec until Intel Power Gadget is complete'.format(self.name, wait_time))
            time.sleep(wait_time)
        logger.info('{}: Waiting {} sec until Intel Power Gadget is found'.format(self.name, wait_interval))
        while not glob.glob(path.join(self.ipg_results_path+'*')):
            time.sleep(wait_interval)
        # strip the Intel Power Gadget file of summary garbage at end of txt file
        logger.info('{}: Stripping Intel Power Gadget of funny end of file stuff.')
        for ipg_file_path in glob.glob(path.join(self.ipg_results_path+'*')):
            ipg = read_ipg(ipg_file_path)
            ipg_clean_file_path = ipg_file_path.replace(self.__ipg.output_file_ext, 'clean.txt')
            ipg.to_csv(ipg_clean_file_path, index=False)
        # kill the Firefox subprocess
        self.__ff_process.terminate()


class PlugLoadExperiment(ExperimentMeta):
    """
    Plug Load Experiment: Utilizes 120v wall outlet logger
    """

    COUNTER_CLASS = PerformanceCounterTask

    def __init__(self, exp_id, exp_name, tasks, **kwargs):
        super(PlugLoadExperiment, self).__init__(exp_id, exp_name, **kwargs)
        self.__perf_counters = None
        self.__results = []
        self.__tasks = tasks
        self.__ff_process = None
        self.__ff_exe_path = kwargs.get('ff_exe_path', self.get_ff_default_path())
        # ensure the experiment results directory exists and is cleaned out
        make_dir(self.exp_dir_path, clear=True)

    @property
    def hobo_sync_log_tag(self):
        return 'hobo_sync_marker'

    @hobo_sync_log_tag.setter
    def hobo_sync_log_tag(self, _):
        raise AttributeError('{}: hobo_sync_log_tag cannot be manually set'.format(self.name))

    def get_ff_default_path(self):
        platform = sys.platform.lower()
        if platform == 'darwin':
            ff_exe_path = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
        elif platform == 'win32':
            ff_exe_path = 'C:/Program Files/Firefox Nightly/firefox.exe'
        else:
            raise ValueError('{}: {} platform currently not supported'.format(self.name, platform))
        return ff_exe_path

    @property
    def ff_exe_path(self):
        return self.__ff_exe_path

    @ff_exe_path.setter
    def ff_exe_path(self, _):
        raise AttributeError('{}: ff_exe_path cannot be manually set'.format(self.name))

    @property
    def perf_counters(self):
        if self.__perf_counters is None:
            self.__perf_counters = self.COUNTER_CLASS()
        return self.__perf_counters

    @perf_counters.setter
    def perf_counters(self, value):
        raise AttributeError('{}: perf_counters cannot be manually set'.format(self.name))

    @property
    def results(self):
        return self.__results

    @results.setter
    def results(self, value):
        raise AttributeError('{}: results cannot be manually set'.format(self.name))

    @property
    def tasks(self):
        return self.__tasks

    @tasks.setter
    def tasks(self, value):
        raise AttributeError('{}: tasks cannot be manually set'.format(self.name))

    @property
    def ff_process(self):
        return self.__ff_process

    @ff_process.setter
    def ff_process(self, _):
        raise AttributeError('{}: ff_process cannot be manually set'.format(self.name))

    @staticmethod
    def validate_usr_input(text):
        status = True
        if text.lower() not in ['y']:
            status = False
        return status

    def log_sync(self, **kwargs):
        synced = False
        while not synced:
            # query usr to press Hobo log button and return at similar times
            msg = 'Sync in process: press Hobo log button and enter on keyboard at same time'
            get_usr_input(msg, None, lambda x: True)
            self.results.append({'timestamp': get_now(), 'action': self.hobo_sync_log_tag})
            synced = True  # TODO: Address ability to sync again if necessary

    def query_usr(self, how):
        # TODO: Refactor to support log_sync, remove other how options other than Hobo
        err = 'Once started, please say "Y"'
        msg = 'Unhandled incorrect input'
        if how == 'FF':
            msg = 'Please start Firefox in Marionette mode (./firefox.exe --marionette)'
        elif how == 'Hobo':
            msg = 'Please start Hobo logger'
        elif how == 'WPM':
            msg = 'Please start Windows Performance Manager'
        get_usr_input(msg, err, self.validate_usr_input)

    @staticmethod
    def start_client():
        client = Marionette('localhost', port=2828)
        client.start_session()
        return client

    def initialize(self):
        logger.debug('{}: initializing experiment'.format(self.name))
        # start Firefox in Marionette mode subprocess
        self.__ff_process = subprocess.Popen(['{}'.format(self.ff_exe_path), '--marionette'])
        # Initialize client on tasks
        self.tasks.client = self.start_client()
        # connect to Firefox, begin collecting counters
        _ = self.perf_counters
        # log the experiment start
        self.results.append({'timestamp': get_now(),
                             'action': '{}: Starting {}/{}'.format(self.name, self.exp_id, self.exp_name)})

    def run(self, **kwargs):
        # begin experiment: start Firefox and logging performance counters
        self.initialize()
        # prompt user: start Hobo Logger
        self.query_usr(how='Hobo')
        # prompt user: Windows Performance Manager
        # self.query_usr(how='WPM')
        # calculate necessary time frame of reference syncs
        self.log_sync()
        # perform experiment
        self.perform_experiment(**kwargs)
        # end experiment
        self.finalize()

    def perform_experiment(self, **kwargs):
        self.results.extend(self.tasks.run(**kwargs))

    def serialize(self):
        with open(self.experiment_file_path, 'wb') as f:
            json.dump(self.results, f, indent=4, sort_keys=True)
        # with open(self.experiment_file_path, 'wb') as csv_file:
        #     writer = csv.writer(csv_file, delimiter=',')
        #     for result in self.results:
        #         writer.writerow(list(result))

    def finalize(self):
        # serialize performance counters
        self.perf_counters.dump_counters(self.perf_counter_file_path)
        # save the experiment log
        self.results.append({'timestamp': get_now(),
                             'action': '{}: Ending {}/{}'.format(self.name, self.exp_id, self.exp_name)})
        self.serialize()
        # kill the Firefox subprocess
        self.__ff_process.terminate()


class Tasks(NameMixin):
    """
    Marionette tasks. Abstract as each experiment has a different set of actions.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.__client = None
        # self.__client = Marionette('localhost', port=2828)
        # self.__client.start_session()

    @property
    def client(self):
        return self.__client

    @client.setter
    def client(self, value):
        self.__client = value

    @abc.abstractproperty
    def tasks(self):
        """
        # returns a list of Task objects
        :return:
        """
        return

    def run(self, **kwargs):
        results = []
        for task in self.tasks:
            results.append(task.run(**kwargs))
        return results


class Task(NameMixin):
    """
    A single Marionette task
    """

    def __init__(self, task, client, **kwargs):
        self.__task = task
        self.__client = client
        self.__meta = kwargs.get('meta', {})

    @property
    def client(self):
        return self.__client

    @client.setter
    def client(self, _):
        raise AttributeError('{}: client cannot be manually set'.format(self.name))

    @property
    def meta(self):
        return self.__meta

    @meta.setter
    def meta(self, _):
        raise AttributeError('{}: meta cannot be manually set'.format(self.name))

    @property
    def task(self):
        """ string of form:
        url = 'http://mozilla.org'
        self.client.navigate(url)
        self.client.go_back()
        self.client.go_forward()
        """
        return self.__task

    @task.setter
    def task(self, _):
        raise AttributeError('{}: task cannot be manually set'.format(self.name))

    def run(self, **kwargs):
        # log the task time
        result = {'timestamp': get_now(), 'action': self.task.replace('\n', '\t'), 'meta': self.meta}
        try:
            # fire off the task
            for action in self.task.split('\n'):
                eval(action)
        except Exception as e:
            exp = traceback.format_exc()
            logger.error('{}: Failed on task\n{}\n{}'.format(self.name, e, exp))
            result['meta']['error'] = exp
        return result
