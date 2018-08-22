import logging
import cPickle

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
