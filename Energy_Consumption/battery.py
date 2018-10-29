import json
import logging
import subprocess
import sys
import threading
import time
from datetime import datetime
from os import path

from marionette_driver.marionette import Marionette

from helpers.io_helpers import read_txt_file

from mixins import NameMixin

logger = logging.getLogger(__name__)


class IntelPowerGadget(NameMixin):
    def __init__(self, **kwargs):
        exe_file_path = kwargs.get('exe_file_path', self.get_exe_default_path())
        duration = kwargs.get('duration', 10)
        output_file_path = kwargs.get('output_file_path', 'powerlog.txt')
        self.output_dir_path, self.output_file_name = path.split(output_file_path)
        self.output_file_prefix, self.output_file_ext = path.splitext(self.output_file_name)
        self.file_counter = 0

        # __ipg_process = subprocess.Popen(['{}'.format(exe_file_path), '-duration', '600',
        #                                   ''])
        thread = threading.Thread(target=self.run, args=(exe_file_path, duration))
        thread.daemon = True
        thread.start()
        # self.run(exe_file_path, duration, output_file_path)

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
        while True:
            output_file_path = self.get_output_file_path()
            print output_file_path
            subprocess.check_call([exe_file_path, '-duration', str(duration), '-file', output_file_path])


