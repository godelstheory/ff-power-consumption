from mixins import NameMixin
from helpers.io_helpers import get_usr_input
from performance_counter import PerformanceCounterTask


class Experiment(NameMixin):
    COUNTER_CLASS = PerformanceCounterTask

    def __init__(self, exp_id, exp_name):
        self.exp_id = exp_id
        self.exp_name = exp_name
        self.__perf_counters = None

    @property
    def perf_counters(self):
        if self.__perf_counters is None:
            self.__perf_counters = self.COUNTER_CLASS()
        return self.__perf_counters

    @perf_counters.setter
    def perf_counters(self, value):
        raise AttributeError('{}: perf_counters cannot be manually set'.format(self.name))

    @staticmethod
    def validate_usr_input(text):
        status = True
        if text.lower() not in ['y']:
            status = False
        return status

    def calculate_syncs(self, **kwargs):
        raise NotImplementedError('{}: to be determined!'.format(self.name))

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

    def run(self):
        # prompt user: begin FF in Marionette mode
        self.query_usr(how='FF')
        # connect to Firefox, begin collecting counters
        counter = self.perf_counters
        # prompt user: start Hobo Logger
        self.query_usr(how='Hobo')
        # prompt user: Windows Performance Manager
        self.query_usr(how='WPM')
        # calculate necessary time frame of reference syncs
        self.calculate_syncs()
        # begin the experiment



