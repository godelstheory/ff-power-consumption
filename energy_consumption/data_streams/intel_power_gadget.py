import logging
import pandas as pd
import subprocess
import sys
import re
from StringIO import StringIO
import threading

from os import path

from mixins import NameMixin
from helpers.io_helpers import read_txt_file

logger = logging.getLogger(__name__)


class IntelPowerGadget(NameMixin):
    def __init__(self, **kwargs):
        exe_file_path = kwargs.get('exe_file_path', self.get_exe_default_path())
        self.sampling_rate = kwargs.get('sampling_rate', 1000)
        self.output_file_ext = kwargs.get('output_file_ext', '.txt')
        duration = kwargs.get('duration', 10)
        output_file_path = kwargs.get('output_file_path', 'powerlog')
        self.output_dir_path, self.output_file_prefix = path.split(output_file_path)
        self.file_counter = 0
        thread = threading.Thread(target=self.run, args=(exe_file_path, duration))
        thread.daemon = True
        thread.start()

    def get_exe_default_path(self):
        platform = sys.platform.lower()
        if platform == 'darwin':
            exe_path = '/Applications/Intel Power Gadget/PowerLog'
        elif platform == 'win32':
            exe_path = 'C:/Program Files/Intel/Power Gadget 3.5/PowerLog3.0.exe'
        else:
            raise ValueError('{}: {} platform currently not supported'.format(self.name, platform))
        return exe_path

    def get_output_file_path(self):
        self.file_counter += 1
        output_file_path = path.join(self.output_dir_path, '{}_{}_{}'.format(self.output_file_prefix,
                                                                             self.file_counter, self.output_file_ext))
        return output_file_path

    def run(self, exe_file_path, duration):
        output_file_path = self.get_output_file_path()
        subprocess.check_call([exe_file_path, '-duration', str(duration), '-resolution', str(self.sampling_rate),
                               '-file', output_file_path])


def read_ipg(ipg_file_path):
    txt = read_txt_file(ipg_file_path)
    txt_clean = re.split('"Total Elapsed Time', txt)[0]
    df = pd.read_csv(StringIO(txt_clean), quotechar='"')
    return df
