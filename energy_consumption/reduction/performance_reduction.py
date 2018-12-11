import pandas as pd


def agg_sum(x):
    """
    Adds up all of the dispatchCount and duration values for each "tab". Ignores children.
    :param x:
    :return:
    """
    duration = 0
    dispatch_count = 0
    num_windows = len(x)
    for win_id, results in x.iteritems():
        duration += results['duration']
        dispatch_count += results['dispatchCount']
    return pd.Series({'duration': duration, 'dispatch_count': dispatch_count, 'num_windows': num_windows})


def filter_one(x):
    """
    Chooses the primary tab (host='www.mozilla.org')
    :param x:
    :return:
    """
    tab = x['1']
    return pd.Series({'duration': tab['duration'], 'dispatch_count': tab['dispatchCount'], 'num_windows': len(x)})
