import threading
import time
import subprocess
from os import path, chdir, system
from helpers.io_helpers import make_dir


num_seconds = 60
output_dir_path = r'C:\Users\Experimenter\Desktop\powercomp'
intel_pg_exe_path = 'C:/Program Files/Intel/Power Gadget 3.5/PowerLog3.0.exe'


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
        subprocess.check_call(['powercfg', '/batteryreport', '/duration', str(num_seconds),
                              '/output', batt_rep_file_path, '/xml'])

    def run(self):
        i = 0
        while True:
            self.get_battery_report(i)
            i += 1
            time.sleep(self.interval)


make_dir(output_dir_path, clear=True)


brt = BatteryReportTask(output_dir_path)

# TODO: Not working... Why?
# chdir(r"C:\\Program Files\\Intel\\Power Gadget 3.5")
# intel_pg_call = r"PowerLog3.0.exe -duration {}".format(str(600) )
# system(intel_pg_call)
subprocess.check_call([intel_pg_exe_path, '-duration', str(num_seconds), '-file', 'powerlog.txt'])
