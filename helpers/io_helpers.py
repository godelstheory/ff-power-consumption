import logging

logger = logging.getLogger(__name__)


def read_txt_file(file_path):
    with open(file_path, 'r') as file:
        txt = file.read()
    return txt


def write_txt_file(file_path, txt):
    with open(file_path, 'w') as file:
        file.write(txt)
