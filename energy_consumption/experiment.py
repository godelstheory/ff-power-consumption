import abc
import glob
import json
import logging
import sys
import time
import traceback
from os import path, getcwd

from marionette_driver.marionette import Marionette

from energy_consumption.helpers.io_helpers import make_dir
from mixins import NameMixin
from energy_consumption.data_streams.intel_power_gadget import IntelPowerGadget, read_ipg
from energy_consumption.data_streams.sampled_data import PerformanceCounterRetriever, get_now

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

    @property
    def exp_dir_path(self):
        return self.__exp_dir_path

    @property
    def perf_counter_file_path(self):
        return path.join(self.__exp_dir_path, '{}_{}_perf_counters.json'.format(self.exp_name, self.exp_id))

    @property
    def experiment_file_path(self):
        return path.join(self.exp_dir_path, '{}_{}_experiment.json'.format(self.exp_name, self.exp_id))


class Experiment(ExperimentMeta):
    """
    Runs the experiment: fires up data samples, ensures all data logging pieces in place, fires off Marionette tasks

    """

    def __init__(self, exp_id, exp_name, tasks, sampled_data_retrievers=None, **kwargs):
        """ Create an Experiment

            Args:
            exp_id:
            exp_name:
            task: tuple. Contains various Task for Marionette to perform
            sampled_data_retrievers: tuple. Contains various SampledDataRetriever
            Kwargs:
                duration: int. Default 60. # of seconds for Intel Power Gadget (IPG) to run.
            Return:
                Experiment
        """
        super(Experiment, self).__init__(exp_id, exp_name, **kwargs)
        clear_exp_dir = kwargs.get('clear_exp_dir', True)
        self.__perf_counters = None
        self.__results = []
        self.__tasks = tasks
        # self.__ff_process = None
        self.__ff_exe_path = kwargs.get('ff_exe_path', self.get_ff_default_path())
        self.__ipg = None
        # ensure the experiment results directory exists and is cleaned out
        make_dir(self.exp_dir_path, clear=clear_exp_dir)
        self.duration = kwargs.get('duration', 60)
        self.start_time = None
        self.sampled_data_retrievers = sampled_data_retrievers or (PerformanceCounterRetriever(),)

    @property
    def results(self):
        return self.__results

    @property
    def tasks(self):
        return self.__tasks

    @property
    def ipg_results_path(self):
        return path.join(self.exp_dir_path, 'ipg_{}'.format(self.exp_id))

    @ipg_results_path.setter
    def ipg_results_path(self, _):
        raise AttributeError('{}: ipg_file_path cannot be manually set'.format(self.name))

    def start_client(self):
        logger.info('{}: connecting to Marionette and beginning session'.format(self.name))
        client = Marionette('localhost', port=2828, bin=self.get_ff_default_path(),
                            prefs={"browser.tabs.remote.autostart": True},
                            gecko_log='-')
        client.start_session()
        return client

    def get_ff_default_path(self):
        platform = sys.platform.lower()
        if platform == 'darwin':
            ff_exe_path = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
        elif platform == 'win32':
            ff_exe_path = 'C:/Program Files/Firefox Nightly/firefox.exe'
        else:
            raise ValueError('{}: {} platform currently not supported'.format(self.name, platform))
        return ff_exe_path

    def initialize(self, **kwargs):
        logger.debug('{}: initializing experiment'.format(self.name))
        # Initialize client on tasks
        self.tasks.client = self.start_client()
        # connect to Firefox, begin collecting sampled data streams (e.g., performance counters, psutil)
        self.start_sampling_data()
        # fire up Intel Power Gadget
        self.initialize_ipg(**kwargs)
        # log the experiment start
        self.results.append({'timestamp': get_now(),
                             'action': '{}: Starting {}/{}'.format(self.name, self.exp_id, self.exp_name)})

    def start_sampling_data(self):
        for data_retriever in self.sampled_data_retrievers:
            data_retriever.run(self.duration, self.exp_dir_path)

    def initialize_ipg(self, **_):
        logger.info('{}: Starting Intel Power Gadget to record for {}'.format(self.name, self.duration))
        self.__ipg = IntelPowerGadget(duration=self.duration, output_file_path=self.ipg_results_path)
        self.start_time = time.time()

    def run(self, **kwargs):
        try:
            # begin experiment: start Firefox and logging performance counters
            self.initialize(**kwargs)
            # run tasks
            self.perform_experiment(**kwargs)
            # end experiment
            self.finalize(**kwargs)
        except Exception as e:
            logger.error('{}: Experiment failed due to {}\n{}'.format(self.name, e, traceback.format_exc()))
            with open(path.join(self.exp_dir_path, 'failure.alert')) as f:
                f.write('Experimental data in this directory could be contaminated!\nUse at own risk!')

    def perform_experiment(self, **kwargs):
        self.results.extend(self.tasks.run(**kwargs))

    def serialize(self):
        self.results.append({'timestamp': get_now(),
                             'action': '{}: Ending {}/{}'.format(self.name, self.exp_id, self.exp_name)})
        with open(self.experiment_file_path, 'wb') as f:
            json.dump(self.results, f, indent=4, sort_keys=True)

    def serialize_sampled_data(self):
        for data_retriever in self.sampled_data_retrievers:
            data_retriever.dump_counters(self.exp_dir_path)

    def check_ipg_status(self, **kwargs):
        wait_interval = kwargs.get('wait_interval', 60)
        while (time.time() - self.start_time) < self.duration:
            wait_time = self.duration - (time.time() - self.start_time)
            logger.debug('{}: Waiting {} sec until Intel Power Gadget is complete'.format(self.name, wait_time))
            time.sleep(wait_time)
        while not glob.glob(path.join(self.ipg_results_path + '*')):
            logger.info('{}: Waiting {} sec until Intel Power Gadget is found'.format(self.name, wait_interval))
            time.sleep(wait_interval)

    def clean_ipg_file(self):
        # FIXME: Broken !!!
        logger.info('{}: Stripping Intel Power Gadget of funny end of file stuff.')
        for ipg_file_path in glob.glob(path.join(self.ipg_results_path + '*')):
            ipg = read_ipg(ipg_file_path)
            ipg_clean_file_path = ipg_file_path.replace(self.__ipg.output_file_ext, 'clean.txt')
            ipg.to_csv(ipg_clean_file_path, index=False)

    def finalize(self, **kwargs):
        # save the experiment log
        self.serialize()
        # wait to finish until Intel Power Gadget is done
        self.check_ipg_status(**kwargs)
        # strip the Intel Power Gadget file of summary garbage at end of txt file
        self.clean_ipg_file()
        # Stop Marionette and Firefox
        self.tasks.client.quit(in_app=True)


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

    @property
    def meta(self):
        return self.__meta

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
            raise e
        return result

# FIXME: Not supported under changes with battery consumption work. Needs lots of love to work!
# class PlugLoadExperiment(ExperimentMeta):
#     """
#     Plug Load Experiment: Utilizes 120v wall outlet logger
#     """
#
#     COUNTER_CLASS = None
#
#     def __init__(self, exp_id, exp_name, tasks, **kwargs):
#         super(PlugLoadExperiment, self).__init__(exp_id, exp_name, **kwargs)
#         self.__perf_counters = None
#         self.__results = []
#         self.__tasks = tasks
#         self.__ff_process = None
#         self.__ff_exe_path = kwargs.get('ff_exe_path', self.get_ff_default_path())
#         # ensure the experiment results directory exists and is cleaned out
#         make_dir(self.exp_dir_path, clear=True)
#
#     @property
#     def hobo_sync_log_tag(self):
#         return 'hobo_sync_marker'
#
#     @hobo_sync_log_tag.setter
#     def hobo_sync_log_tag(self, _):
#         raise AttributeError('{}: hobo_sync_log_tag cannot be manually set'.format(self.name))
#
#     def get_ff_default_path(self):
#         platform = sys.platform.lower()
#         if platform == 'darwin':
#             ff_exe_path = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
#         elif platform == 'win32':
#             ff_exe_path = 'C:/Program Files/Firefox Nightly/firefox.exe'
#         else:
#             raise ValueError('{}: {} platform currently not supported'.format(self.name, platform))
#         return ff_exe_path
#
#     @property
#     def ff_exe_path(self):
#         return self.__ff_exe_path
#
#     @ff_exe_path.setter
#     def ff_exe_path(self, _):
#         raise AttributeError('{}: ff_exe_path cannot be manually set'.format(self.name))
#
#     @property
#     def perf_counters(self):
#         if self.__perf_counters is None:
#             self.__perf_counters = self.COUNTER_CLASS()
#         return self.__perf_counters
#
#     @perf_counters.setter
#     def perf_counters(self, value):
#         raise AttributeError('{}: perf_counters cannot be manually set'.format(self.name))
#
#     @property
#     def results(self):
#         return self.__results
#
#     @results.setter
#     def results(self, value):
#         raise AttributeError('{}: results cannot be manually set'.format(self.name))
#
#     @property
#     def tasks(self):
#         return self.__tasks
#
#     @tasks.setter
#     def tasks(self, value):
#         raise AttributeError('{}: tasks cannot be manually set'.format(self.name))
#
#     @property
#     def ff_process(self):
#         return self.__ff_process
#
#     @ff_process.setter
#     def ff_process(self, _):
#         raise AttributeError('{}: ff_process cannot be manually set'.format(self.name))
#
#     @staticmethod
#     def validate_usr_input(text):
#         status = True
#         if text.lower() not in ['y']:
#             status = False
#         return status
#
#     def log_sync(self, **kwargs):
#         synced = False
#         while not synced:
#             # query usr to press Hobo log button and return at similar times
#             msg = 'Sync in process: press Hobo log button and enter on keyboard at same time'
#             get_usr_input(msg, None, lambda x: True)
#             self.results.append({'timestamp': get_now(), 'action': self.hobo_sync_log_tag})
#             synced = True  # TODO: Address ability to sync again if necessary
#
#     def query_usr(self, how):
#         # TODO: Refactor to support log_sync, remove other how options other than Hobo
#         err = 'Once started, please say "Y"'
#         msg = 'Unhandled incorrect input'
#         if how == 'FF':
#             msg = 'Please start Firefox in Marionette mode (./firefox.exe --marionette)'
#         elif how == 'Hobo':
#             msg = 'Please start Hobo logger'
#         elif how == 'WPM':
#             msg = 'Please start Windows Performance Manager'
#         get_usr_input(msg, err, self.validate_usr_input)
#
#     @staticmethod
#     def start_client():
#         client = Marionette('localhost', port=2828)
#         client.start_session()
#         return client
#
#     def initialize(self):
#         logger.debug('{}: initializing experiment'.format(self.name))
#         # start Firefox in Marionette mode subprocess
#         self.__ff_process = subprocess.Popen(['{}'.format(self.ff_exe_path), '--marionette'])
#         # Initialize client on tasks
#         self.tasks.client = self.start_client()
#         # connect to Firefox, begin collecting counters
#         _ = self.perf_counters
#         # log the experiment start
#         self.results.append({'timestamp': get_now(),
#                              'action': '{}: Starting {}/{}'.format(self.name, self.exp_id, self.exp_name)})
#
#     def run(self, **kwargs):
#         # begin experiment: start Firefox and logging performance counters
#         self.initialize()
#         # prompt user: start Hobo Logger
#         self.query_usr(how='Hobo')
#         # prompt user: Windows Performance Manager
#         # self.query_usr(how='WPM')
#         # calculate necessary time frame of reference syncs
#         self.log_sync()
#         # perform experiment
#         self.perform_experiment(**kwargs)
#         # end experiment
#         self.finalize()
#
#     def perform_experiment(self, **kwargs):
#         self.results.extend(self.tasks.collect(**kwargs))
#
#     def serialize(self):
#         with open(self.experiment_file_path, 'wb') as f:
#             json.dump(self.results, f, indent=4, sort_keys=True)
#         # with open(self.experiment_file_path, 'wb') as csv_file:
#         #     writer = csv.writer(csv_file, delimiter=',')
#         #     for result in self.results:
#         #         writer.writerow(list(result))
#
#     def finalize(self):
#         # serialize performance counters
#         self.perf_counters.dump_counters(self.perf_counter_file_path)
#         # save the experiment log
#         self.results.append({'timestamp': get_now(),
#                              'action': '{}: Ending {}/{}'.format(self.name, self.exp_id, self.exp_name)})
#         self.serialize()
#         # kill the Firefox subprocess
#         self.__ff_process.terminate()
