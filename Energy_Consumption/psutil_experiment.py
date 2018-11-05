import json
import logging
import subprocess
import sys
from os.path import join
# from os import getcwd, path

from marionette_driver.marionette import Marionette

# from battery import IntelPowerGadget
from Energy_Consumption.experiment import ExperimentMeta
# from Energy_Consumption.performance_counter import (
#     PerformanceCounterTask, get_now)
from Energy_Consumption.performance_counter import (
    PsUtilTask, get_now)
from helpers.io_helpers import make_dir

logger = logging.getLogger(__name__)


class PsUtilsExperiment(ExperimentMeta):
    """
    psutil experiment: Grab cpu and other system stats using psutil.
    """
    def __init__(self, exp_id, exp_name, tasks, method_names, **kwargs):
        super(PsUtilsExperiment, self).__init__(exp_id, exp_name, **kwargs)
        self.perf_counters = None
        self.results = []
        self.tasks = tasks
        self.method_names = method_names
        self.ff_process = None
        self.ff_exe_path = kwargs.get(
            'ff_exe_path', self.get_ff_default_path()
        )
        self.exp_dir_path = self.exp_dir_path.copy()
        self.psu_loc = join(
            self.exp_dir_path,
            '{}_{}_psutil.json'.format(exp_name, exp_id)
        )
        # ensure the experiment results directory exists and is cleaned out
        make_dir(self.exp_dir_path, clear=True)

    def init_perf_counters(self):
        self.perf_counters = PsUtilTask(method_names=self.method_names)

    def get_ff_default_path(self):
        platform = sys.platform.lower()
        if platform == 'darwin':
            ff_exe_path = '/Applications/Firefox Nightly.app/Contents/MacOS/firefox'
        elif platform == 'win32':
            ff_exe_path = 'C:/Program Files/Firefox Nightly/firefox.exe'
        else:
            raise ValueError(
                '{}: {} platform currently not supported'.format(self.name, platform))
        return ff_exe_path

    @staticmethod
    def validate_usr_input(text):
        return text.lower() == 'y'

    @staticmethod
    def start_client():
        client = Marionette('localhost', port=2828)
        client.start_session()
        return client

    def initialize(self):
        logger.debug('%s: initializing experiment', self.name)
        # logger.debug('{}: initializing experiment'.format(self.name))
        # start Firefox in Marionette mode subprocess
        self.ff_process = subprocess.Popen(
            # ['{}'.format(self.ff_exe_path), '--marionette'])
            [self.ff_exe_path, '--marionette'])
        # Initialize client on tasks
        self.tasks.client = self.start_client()
        # connect to Firefox, begin collecting counters
        self.init_perf_counters()
        # log the experiment start
        self.results.append({
            'timestamp': get_now(),
            'action': '{}: Starting {}/{}'.format(self.name, self.exp_id, self.exp_name)
        })

    def run(self, **kwargs):
        # begin experiment: start Firefox and logging performance counters
        self.initialize()
        # calculate necessary time frame of reference syncs
        # perform experiment
        self.perform_experiment(**kwargs)
        # end experiment
        self.finalize()

    def perform_experiment(self, **kwargs):
        self.results.extend(self.tasks.run(**kwargs))

    def serialize(self):
        with open(self.experiment_file_path, 'wb') as f:
            json.dump(self.results, f, indent=4, sort_keys=True)

    def finalize(self):
        # serialize performance counters
        self.perf_counters.dump_counters(self.perf_counter_file_path)
        # save the experiment log
        self.results.append({
            'timestamp': get_now(),
            'action': '{}: Ending {}/{}'.format(self.name, self.exp_id, self.exp_name)
        })
        self.serialize()
        # kill the Firefox subprocess
        self.ff_process.terminate()
