from ..experiment import Experiment
import tp100
import psutil
import time


class ExperimentTp100(Experiment):
    def __init__(self, exp_id, exp_name, tasks, sampled_data_retrievers=None, **kwargs):
        super(Experiment, self).__init__(exp_id, exp_name, tasks=tasks, sampled_data_retrievers=sampled_data_retrievers,
                                         **kwargs)
        self.battery_thresh = kwargs.get('battery_thresh', (0.1, 0.9)) # battery threshold to turn off plug
        # Get connection to tp100
        plug_atts = tp100.Discover.discover().values()
        self._plug = None if not plug_atts else tp100.SmartPlug(plug_atts[0].host)

    @property
    def plug(self):
        return self._plug

    def run(self, **kwargs):
        # Determine if battery charged
        battery = psutil.sensors_battery()
        if battery.percent < self.battery_thresh[0]: # battery reports too low
            if self.plug.is_off: # ensure it is on
                self.plug.turn_on()
            while battery.percent < self.battery_thresh[1]: # charge until maximum met
                time.sleep(3000)  # wait 5 minutes
                battery = psutil.sensors_battery()
            # turn off the plug
            self.plug.turn_off()
        # otherwise, make sure it is off
        elif self.plug.is_on:
            self.plug.turn_off()



