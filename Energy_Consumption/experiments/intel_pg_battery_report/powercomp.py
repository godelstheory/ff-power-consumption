import threading
import time
import subprocess
from os import path
from helpers.io_helpers import make_dir

output_dir_path = r'C:\Users\Experimenter\Desktop\powercomp'
intel_pg_exe_path = r'C:\Program Files\Intel\Power Gadget 3.5\PowerLog3.0.exe'

"""
Scratch the below: replace with addition thread for battery report.
"""


class BatteryReportTask(object):
    def __init__(self, output_dir_path, interval=1, **kwargs):
        super(BatteryReportTask, self).__init__(**kwargs)
        self.output_dir_path = output_dir_path
        self.interval = interval
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def get_battery_report(self, i):
        batt_rep_file_path = path.join(self.output_dir_path, 'batter_report_{}.xml'.format(i))
        subprocess.check_call('powercfg', '/batteryreport', '/duration', 'num_seconds',
                              '/output', batt_rep_file_path, '/xml')

    def run(self):
        i = 0
        while True:
            self.get_battery_report(i)
            i += 1
            time.sleep(self.interval)


make_dir(output_dir_path, clear=True)

num_seconds = 10
brt = BatteryReportTask(output_dir_path)

subprocess.check_call(intel_pg_exe_path, '-duration', '600',
                      '-file', path.join(output_dir_path, 'powerlog.txt'))
