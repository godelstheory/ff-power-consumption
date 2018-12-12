import cPickle
import logging
import sys
import tempfile
from os import path, makedirs, listdir, remove

from text_helpers import always_str

logger = logging.getLogger(__name__)


def read_txt_file(file_path):
    with open(file_path, 'r') as f:
        txt = f.read()
    return txt


def write_txt_file(file_path, txt):
    with open(file_path, 'w') as f:
        f.write(txt)


def unpickle_object(file_path):
    with open(file_path, 'r') as f:
        obj = cPickle.load(f)
    return obj


def pickle_object(obj, file_path):
    with open(file_path, 'wb') as f:
        cPickle.dump(obj, f)


def get_usr_input(msg, err, validator):
        res = None
        while res is None:
            res = raw_input(always_str(msg) + ': ')
            if not validator(res):
                print always_str(err)
                res = None
        return res


def make_dir(dir_path, clear=False):
    if not path.isdir(dir_path):
        makedirs(dir_path)
    elif clear:
        for file_name in listdir(dir_path):
            remove(path.join(dir_path, file_name))


def log_to_stdout(logger, level=logging.INFO):
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def get_temp_filename(root_dir_path=None):
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.close()
    if root_dir_path is not None:
        file_path = path.join(root_dir_path, path.basename(temp.name))
    else:
        file_path = temp.name
    return file_path
