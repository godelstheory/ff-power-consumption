# Firefox Power Consumption Experiments
Codebase to perform and analyze power consumption experiments of Firefox performing various tasks. Internal Firefox counters are compared to (and hopefully utilized as a proxy thereof) power usage of various OS components. The latter is measured using Intel Power Gadget ([IPG](https://software.intel.com/en-us/articles/intel-power-gadget-20)).

[Experiments](https://drive.google.com/file/d/1KdsnJmEXAL_DIfnPx115Pe94D4FC31c8/view) are implemented as self-contained scripts, and utilize [marionette-driver](https://pypi.org/project/marionette-driver/) to perfom Firefox "tasks", while Firefox-specific metrics are being collected from the resource API in addition to power usage being measured by IPG

## Installation
Install [Intel Power Gadget](https://software.intel.com/en-us/articles/intel-power-gadget-20) for the appropriate OS.

Install with `pip install -e`, probably inside a Python 2.7 virtualenv.

The `-e` is not just a convenience (letting you edit the package without reinstalling it) - it's actually necessary since we don't properly package essential files like `retrieve_performance_counters.js`.

Once installed, run experiment scripts from another directory (a directory you want the files dumped into):
```
$python FF-power-consumption/scripts/cdowhygelund/Experiment\ -\ V0\ -\ high.py
```

