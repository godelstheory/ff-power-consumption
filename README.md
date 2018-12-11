# Firefox Power Consumption Experiments
Codebase to perform and analyze power consumption experiments of Firefox performing various tasks. Internal Firefox counters are compared to (and hopefully utilized as a proxy thereof) power usage of various OS components. The latter is measured using Intel Power Gadget.

## Installation
Install with `pip install -e`, probably inside a Python 2.7 virtualenv.

The `-e` is not just a convenience (letting you edit the package without reinstalling it) - it's actually necessary since we don't properly package essential files like `retrieve_performance_counters.js`.

Once installed, run experiment scripts from another directory (a directory you want the files dumped into):
```
$python FF-power-consumption/scripts/cdowhygelund/Experiment\ -\ V0\ -\ high.py
```

## Development/hacking
Felix plans to develop on his main machine, then rsync the package to the (mac) test laptop:
```
rsync -ar --delete ~/Code/FF-power-consumption felix@felix-ec.local:/Users/felix/
```
run (after installing once with `-e`) on the test laptop, then analyze the data from a notebook on his main machine that directly accesses the test laptop's data using sftp. This requires that the experiment script be invoked from *outside* the repo, else the data will be wiped on the next rsync.
