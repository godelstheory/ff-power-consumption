from ..experiment import Experiment
import tp100
import psutil
import time
import logging

logger = logging.getLogger(__name__)


class ExperimentTp100(Experiment):
    def __init__(self, exp_id, exp_name, tasks, sampled_data_retrievers=None, **kwargs):
        super(ExperimentTp100, self).__init__(exp_id, exp_name, tasks=tasks,
                                              sampled_data_retrievers=sampled_data_retrievers, **kwargs)
        self.battery_thresh = kwargs.get('battery_thresh', (10, 95))  # % battery threshold to turn off plug
        # Get connection to tp100
        self._plug = self.get_plug()

    @property
    def plug(self):
        if self._plug is None:
            self._plug = self.get_plug()
        return self._plug

    def get_plug(self):
        plugs = tp100.Discover.discover().values()
        plug = None if not plugs else tp100.SmartPlug(plugs[0].host)
        if plug is None:
            logger.warn('{}: Could not find tp100 smart plug!'.format(self.name))
        return plug

    def run(self, **kwargs):
        # Determine if battery charged
        battery = psutil.sensors_battery()
        if battery.percent < self.battery_thresh[0]:  # battery reports too low
            logger.info('{}: Charging battery due to level reaching {}'.format(self.name, self.battery_thresh[0]))
            start_charging = time.clock()
            if self.plug and self.plug.is_off:  # ensure it is on
                self.plug.turn_on()
            while battery.percent < self.battery_thresh[1]:  # charge until maximum met
                time.sleep(300)  # wait 5 minutes
                battery = psutil.sensors_battery()
            # turn off the plug
            end_charging = time.clock()
            logger.info('{}: Charging battery took {}'.format(self.name, end_charging - start_charging))
            if self.plug:
                self.plug.turn_off()
        # otherwise, make sure it is off
        else:
            logger.info('{}: Skipping battery charge: level @ {}'.format(self.name, battery.percent))
            if self.plug and self.plug.is_on:
                logger.info('{}: plug left on! Unplugging'.format(self.name))
                self.plug.turn_off()

        super(ExperimentTp100, self).run(**kwargs)
