set f1="C:\Users\Experimenter\batteryreport_start.html"
set f2="C:\Users\Experimenter\batteryreport_end.html"
del %f1%
del %f2%
powercfg /batteryreport /output %f1% /duration 1

"C:\Program Files\Intel\Power Gadget 3.5\PowerLog3.0.exe" -duration 600 -file "C:\Users\Experimenter\powerlog.txt"

powercfg /batteryreport /output %f2% /duration 1
