import operator as op
from collections import defaultdict
import datetime as dt
from operator import itemgetter as itg
from functools import reduce
from typing import List, Union, Dict
import re

import numpy as np
import toolz.curried as z
from numba import njit
from pandas import DataFrame
from pandas.compat import lmap
import pandas as pd

Ts_tabs = Dict[str, dict]
Disp_dur = Dict[str, int]
Tab_num = str
Tabs_doc = Dict[Tab_num, Dict]
Num = Union[float, int]


def join_json_cols(df, cols):
    df = df.copy()
    for c in cols:
        coldf = DataFrame(fillna_it(df.pop(c), {}), index=df.index)
        for cc in coldf:
            df[cc] = coldf[cc]
    return df


def fillna_it(l, v):
    return [
        e if (e == e) else v
        for e in l
    ]


def get_oom_names(df, group_col='Met'):
    df['Oom_'] = (df.groupby(group_col).V.transform('mean')
                  .pipe(np.log10).pipe(np.floor))
    oom_name_ = df.groupby('Oom_')[group_col].apply(set)
    oom_name = oom_name_.map(lambda x: ', '.join(sorted(x)))
    df['Oom'] = df.Oom_.map(oom_name.to_dict())
    return df


# Calcs
@njit
def diff(s):
    "current element - prev. Unless it's gone down."
    r = np.empty_like(s)
    r[0] = np.nan
    for i in range(1, len(s)):
        r[i] = max(0, s[i] - s[i - 1])
    return r


def reduce_keys(fn, ds: List[dict], default_type: Num=1):
    accum: Dict[str, Num] = defaultdict(type(default_type))

    def combine(accum, d):
        for k, v in d.items():
            accum[k] = fn(accum[k], v)
        return accum

    return reduce(combine, ds, accum)


def to_array(x):
    try:
        return x.values
    except AttributeError:
        return x


def non_zero_cols(df):
    """Some tabs have either null or 0 for all
    entries. Drop those columns"""
    all_nz = ~df.fillna(0).eq(0).all()
    return all_nz[all_nz].index.tolist()


diffs = z.compose(diff, to_array)


def cleanup_counter_df(df, diff=True):
    "df.index: timestamp"
    df = df.sort_index().resample('s').ffill(limit=1)
    if diff:
        return df.apply(diffs)
    return df


# Utility to easily access time index by minute
def tix(min, n=15, s2=None, time_ix=None):
    if hasattr(time_ix, 'index'):
        time_ix = time_ix.index
    if n is None:
        raise NotImplementedError
    imin = int(min)
    frac = min % imin
    sec = int(frac * 100)
    st = dt.datetime(2018, 9, 13, 9, imin, sec)

    ix_loc = time_ix.searchsorted(st)
    rix = time_ix[ix_loc:][:n]
    return rix


# Extract stuff
def extract_dur_disp_tab(doc: Disp_dur) -> Disp_dur:
    return z.keyfilter(lambda x: x in {'dispatchCount', 'duration'}, doc)


def extract_ctr_main(doc: Tabs_doc) -> Dict[Tab_num, Disp_dur]:
    tab_docs = z.valmap(extract_dur_disp_tab, doc)
    # {'0': {'dispatchCount': 4, 'duration': 0},
    #  '1': {'dispatchCount': 4, 'duration': 0},}
    return tab_docs


def extract_ctr_children_sum(doc: Tabs_doc) -> Dict[Tab_num, Disp_dur]:
    default = {'dispatchCount': np.nan, 'duration': np.nan}

    def reduce_children(chs: List[Disp_dur]):
        # TODO: extract host info?
        disp_durs = lmap(extract_dur_disp_tab, chs)
        return reduce_keys(op.add, disp_durs) or default

    tab_docs = z.valmap(z.compose(reduce_children, itg('children')), doc)
    return tab_docs


#####################
# Process raw files #
#####################
def rn_hobo1(s):
    "Rename the weird Hobo csv columns"
    lbl_re = re.compile(r".+?LBL: (.+?)\)")
    lgr_re = re.compile(r"(.+?) \(LGR S\/N.+")
    lbl_res = lbl_re.findall(s)
    if lbl_res:
        [res] = lbl_res
        return res
    lgr_res = lgr_re.findall(s)
    if lgr_res:
        [res] = lgr_res
        return res
    elif s.startswith('Date Time'):
        return 'Dt'
    return s


def rn_hobo2(s):
    if s.endswith('yy'):
        return s[:-1]
    return s.replace('/', '_').capitalize()


def hobo_process(ng):
    ng = (
        ng.rename(columns=rn_hobo)
        .assign(Dt=lambda x: pd.to_datetime(x.Dt))
    )
    if ng.iloc[-1].isnull().sum() > 7:
        ng = ng[:-1].copy()

    num_null_cols = ng.isnull().sum(axis=0).eq(0).mean()
    assert num_null_cols > .5, "Want quant cols to be nonnull"
    return ng


rn_hobo = z.compose(rn_hobo2, rn_hobo1)


#############################
# Experiment actions/events #
#############################
def concat_simult_acts(ss):
    "Dedupe actions that occur at 'about' the same time"
    if len(ss) == 1:
        return ss.iloc[0]
    return ' & '.join(ss)


def match_site_abbrev(s):
    "Shorten website representations"
    if 'addons.mozilla.org' in s:
        return 'AMO'
    if 'mozilla.org' in s:
        return 'Moz'
    if 'Fortnite' in s:
        return 'Fortnite'
    if 'twitch.tv' in s:
        return 'twitch.tv'
    return s


def abbrev_action(s):
    nav_re = re.compile(r"self.client.navigate\('(.+?)'\)")
    nav = nav_re.findall(s)
    if nav:
        [site] = nav
        return '-> ' + match_site_abbrev(s)
    if s.startswith('self.client'):
        return 'sc' + s[11:]
    if s.startswith('Experiment: Starting 1'):
        return 'Start'
    if s.startswith('Experiment: Ending'):
        return 'End'
    if s.startswith('time.sleep'):
        return 'slp' + s[10:]
    return s


def abbrev_actions(ss):
    return [abbrev_action(s) if (s == s) else s for s in ss]


def test_reduce_keys():
    ds = [{'a': 1}, {'a': 1, 'b': 3}]
    assert reduce_keys(op.add, ds, default_type=int) == {'a': 2, 'b': 3}
