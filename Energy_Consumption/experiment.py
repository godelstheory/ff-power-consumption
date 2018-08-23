from mixins import NameMixin
from helpers.io_helpers import get_usr_input
from performance_counter import PerformanceCounterTask
from datetime import datetime
from marionette_driver.marionette import Marionette
import abc
import csv


class Experiment(NameMixin):
    """
    Runs the experiment: fires up performance counters, ensures all data logging pieces in place, fires off Marionette tasks
    """

    COUNTER_CLASS = PerformanceCounterTask

    def __init__(self, exp_id, exp_name, tasks):
        self.exp_id = exp_id
        self.exp_name = exp_name
        self.__perf_counters = None
        self.__results = []
        self.__tasks = tasks

    @property
    def perf_counters(self):
        if self.__perf_counters is None:
            self.__perf_counters = self.COUNTER_CLASS()
        return self.__perf_counters

    @perf_counters.setter
    def perf_counters(self, value):
        raise AttributeError('{}: perf_counters cannot be manually set'.format(self.name))

    @property
    def perf_counter_file_path(self):
        return '{}_{}_perf_counters.json'.format(self.exp_name, self.exp_id)

    @perf_counter_file_path.setter
    def perf_counter_file_path(self, _):
        raise AttributeError('{}: perf_counter_file_path cannot be manually set'.format(self.name))

    @property
    def experiment_file_path(self):
        return '{}_{}_experiment.csv'.format(self.exp_name, self.exp_id)

    @experiment_file_path.setter
    def experiment_file_path(self, _):
        raise AttributeError('{}: experiment_file_path cannot be manually set'.format(self.name))

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

    @staticmethod
    def validate_usr_input(text):
        status = True
        if text.lower() not in ['y']:
            status = False
        return status

    def calculate_syncs(self, **kwargs):
        raise NotImplementedError('{}: calculate_syncs to be determined!'.format(self.name))

    def query_usr(self, how):
        err = 'Once started, please say "Y"'
        msg = 'Unhandled incorrect input'
        if how == 'FF':
            msg = 'Please start Firefox in Marionette mode (./firefox.exe --marionette)'
        elif how == 'Hobo':
            msg = 'Please start Hobo logger'
        elif how == 'WPM':
            msg = 'Please start Windows Performance Manager'
        get_usr_input(msg, err, self.validate_usr_input)

    def run(self, **kwargs):
        # prompt user: begin FF in Marionette mode
        self.query_usr(how='FF')
        # connect to Firefox, begin collecting counters
        counter = self.perf_counters
        # prompt user: start Hobo Logger
        self.query_usr(how='Hobo')
        # prompt user: Windows Performance Manager
        self.query_usr(how='WPM')
        # calculate necessary time frame of reference syncs
        # self.calculate_syncs()
        # begin the experiment
        self.results.append((datetime.now(), '{}: Starting {}/{}'.format(self.name, self.exp_id, self.exp_name)))
        # perform experiment
        self.perform_experiment(**kwargs)
        # serialize performance counters
        counter.dump_counters(self.perf_counter_file_path)
        # end experiment
        self.finalize()

    def perform_experiment(self, **kwargs):
        self.results.extend(self.tasks.run(**kwargs))

    def serialize(self):
        with open(self.experiment_file_path, 'wb') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            for result in self.results:
                writer.writerow(list(result))

    def finalize(self):
        self.results.append((datetime.now(), '{}: Ending {}/{}'.format(self.name, self.exp_id, self.exp_name)))
        self.serialize()


class Tasks(NameMixin):
    """
    Marionette tasks. Abstract as each experiment has a different set of actions.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.__client = Marionette('localhost', port=2828)
        self.__client.start_session()

    @property
    def client(self):
        return self.__client

    @client.setter
    def client(self, _):
        raise AttributeError('{}: client cannot be manually set'.format(self.name))

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

    def __init__(self, task, client):
        self.__task = task
        self.__client = client

    @property
    def client(self):
        return self.__client

    @client.setter
    def client(self, _):
        raise AttributeError('{}: client cannot be manually set'.format(self.name))

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
        result = (datetime.now(), self.task.replace('\n', '\t'))
        # fire off the task
        for action in self.task.split('\n'):
            eval(action)
        return result
