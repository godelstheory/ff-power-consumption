import socket
import struct
import json
import datetime
import logging
from collections import defaultdict
import warnings


logger = logging.getLogger(__name__)

"""
Ported to Py2 from https://github.com/GadgetReactor/pyHS100
"""

class TPLinkSmartHomeProtocol:
    """
    Implementation of the TP-Link Smart Home Protocol
    Encryption/Decryption methods based on the works of
    Lubomir Stroetmann and Tobias Esser
    https://www.softscheck.com/en/reverse-engineering-tp-link-hs110/
    https://github.com/softScheck/tplink-smartplug/
    which are licensed under the Apache License, Version 2.0
    http://www.apache.org/licenses/LICENSE-2.0
    """
    INITIALIZATION_VECTOR = 171
    DEFAULT_PORT = 9999
    DEFAULT_TIMEOUT = 5

    @staticmethod
    def query(host,
              request,
              port=DEFAULT_PORT):
        """
        Request information from a TP-Link SmartHome Device and return the
        response.
        :param str host: host name or ip address of the device
        :param int port: port on the device (default: 9999)
        :param request: command to send to the device (can be either dict or
        json string)
        :return:
        """
        if isinstance(request, dict):
            request = json.dumps(request)

        timeout = TPLinkSmartHomeProtocol.DEFAULT_TIMEOUT
        sock = None
        try:
            sock = socket.create_connection((host, port), timeout)

            logger.debug("> (%i) %s", len(request), request)
            sock.send(TPLinkSmartHomeProtocol.encrypt(request))

            buffer = bytes()
            # Some devices send responses with a length header of 0 and
            # terminate with a zero size chunk. Others send the length and
            # will hang if we attempt to read more data.
            length = -1
            while True:
                chunk = sock.recv(4096)
                if length == -1:
                    length = struct.unpack(">I", chunk[0:4])[0]
                buffer += chunk
                if (length > 0 and len(buffer) >= length + 4) or not chunk:
                    break

        finally:
            try:
                if sock:
                    sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                # OSX raises OSError when shutdown() gets called on a closed
                # socket. We ignore it here as the data has already been read
                # into the buffer at this point.
                pass

            finally:
                if sock:
                    sock.close()

        response = TPLinkSmartHomeProtocol.decrypt(buffer[4:])
        logger.debug("< (%i) %s", len(response), response)

        return json.loads(response)

    @staticmethod
    def encrypt(request):
        """
        Encrypt a request for a TP-Link Smart Home Device.
        :param request: plaintext request data
        :return: ciphertext request
        """
        key = TPLinkSmartHomeProtocol.INITIALIZATION_VECTOR

        plainbytes = request  # request.encode()
        buffer = bytearray(struct.pack(">I", len(plainbytes)))

        for plainbyte in plainbytes:
            cipherbyte = key ^ ord(plainbyte)
            key = cipherbyte
            buffer.append(cipherbyte)

        return bytes(buffer)

    @staticmethod
    def decrypt(ciphertext):
        """
        Decrypt a response of a TP-Link Smart Home Device.
        :param ciphertext: encrypted response data
        :return: plaintext response
        """
        key = TPLinkSmartHomeProtocol.INITIALIZATION_VECTOR
        buffer = []

        for cipherbyte in ciphertext:
            plainbyte = key ^ ord(cipherbyte)
            key = ord(cipherbyte)
            buffer.append(plainbyte)

        plaintext = "".join(map(chr, buffer))

        return plaintext


class SmartDevice(object):
    # possible device features
    FEATURE_ENERGY_METER = 'ENE'
    FEATURE_TIMER = 'TIM'

    ALL_FEATURES = (FEATURE_ENERGY_METER, FEATURE_TIMER)

    def __init__(self,
                 host,
                 protocol=None,
                 context=None):
        """
        Create a new SmartDevice instance.
        :param str host: host name or ip address on which the device listens
        :param context: optional child ID for context in a parent device
        """
        self.host = host
        if not protocol:
            protocol = TPLinkSmartHomeProtocol()
        self.protocol = protocol
        self.emeter_type = "emeter"  # type: str
        self.context = context
        self.num_children = 0

    def _query_helper(self,
                      target,
                      cmd,
                      arg=None):
        """
        Helper returning unwrapped result object and doing error handling.
        :param target: Target system {system, time, emeter, ..}
        :param cmd: Command to execute
        :param arg: JSON object passed as parameter to the command
        :return: Unwrapped result for the call.
        :rtype: dict
        :raises SmartDeviceException: if command was not executed correctly
        """
        if self.context is None:
            request = {target: {cmd: arg}}
        else:
            request = {"context": {"child_ids": [self.context]},
                       target: {cmd: arg}}
        if arg is None:
            arg = {}
        try:
            response = self.protocol.query(
                host=self.host,
                request=request,
            )
        except Exception as ex:
            raise Exception('Communication error')

        if target not in response:
            raise Exception("No required {} in response: {}"
                            .format(target, response))

        result = response[target]
        if "err_code" in result and result["err_code"] != 0:
            raise Exception("Error on {}.{}: {}"
                            .format(target, cmd, result))

        if cmd not in result:
            raise Exception("No command in response: {}"
                            .format(response))
        result = result[cmd]
        del result["err_code"]

        return result

    @property
    def features(self):
        """
        Returns features of the devices
        :return: list of features
        :rtype: list
        """
        warnings.simplefilter('always', DeprecationWarning)
        warnings.warn(
            "features works only on plugs and its use is discouraged, "
            "and it will likely to be removed at some point",
            DeprecationWarning,
            stacklevel=2
        )
        warnings.simplefilter('default', DeprecationWarning)
        if "feature" not in self.sys_info:
            return []

        features = self.sys_info['feature'].split(':')

        for feature in features:
            if feature not in SmartDevice.ALL_FEATURES:
                logger.warning("Unknown feature %s on device %s.",
                               feature, self.model)

        return features

    @property
    def has_emeter(self):
        """
        Checks feature list for energy meter support.
        Note: this has to be implemented on a device specific class.
        :return: True if energey meter is available
                 False if energymeter is missing
        """
        raise NotImplementedError()

    @property
    def sys_info(self):
        """
        Returns the complete system information from the device.
        :return: System information dict.
        :rtype: dict
        """
        return defaultdict(lambda: None, self.get_sysinfo())

    def get_sysinfo(self):
        """
        Retrieve system information.
        :return: sysinfo
        :rtype dict
        :raises SmartDeviceException: on error
        """
        return self._query_helper("system", "get_sysinfo")

    @property
    def model(self):
        """
        Get model of the device
        :return: device model
        :rtype: str
        :raises SmartDeviceException: on error
        """
        return str(self.sys_info['model'])

    @property
    def alias(self):
        """
        Get current device alias (name)
        :return: Device name aka alias.
        :rtype: str
        """
        return str(self.sys_info['alias'])

    @alias.setter
    def alias(self, alias):
        """
        Sets the device name aka alias.
        :param alias: New alias (name)
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_dev_alias", {"alias": alias})

    @property
    def icon(self):
        """
        Returns device icon
        Note: not working on HS110, but is always empty.
        :return: icon and its hash
        :rtype: dict
        :raises SmartDeviceException: on error
        """
        return self._query_helper("system", "get_dev_icon")

    @icon.setter
    def icon(self, icon):
        """
        Content for hash and icon are unknown.
        :param str icon: Icon path(?)
        :raises NotImplementedError: when not implemented
        :raises SmartPlugError: on error
        """
        raise NotImplementedError()
        # here just for the sake of completeness
        # self._query_helper("system",
        #                    "set_dev_icon", {"icon": "", "hash": ""})
        # self.initialize()

    @property
    def time(self):
        """
        Returns current time from the device.
        :return: datetime for device's time
        :rtype: datetime.datetime or None when not available
        :raises SmartDeviceException: on error
        """
        try:
            res = self._query_helper("time", "get_time")
            return datetime.datetime(res["year"], res["month"], res["mday"],
                                     res["hour"], res["min"], res["sec"])
        except Exception:
            return None

    @time.setter
    def time(self, ts):
        """
        Sets time based on datetime object.
        Note: this calls set_timezone() for setting.
        :param datetime.datetime ts: New date and time
        :return: result
        :type: dict
        :raises NotImplemented: when not implemented.
        :raises SmartDeviceException: on error
        """
        raise NotImplementedError("Fails with err_code == 0 with HS110.")

    @property
    def timezone(self):
        """
        Returns timezone information
        :return: Timezone information
        :rtype: dict
        :raises SmartDeviceException: on error
        """
        return self._query_helper("time", "get_timezone")

    @property
    def hw_info(self):
        """
        Returns information about hardware
        :return: Information about hardware
        :rtype: dict
        """
        keys = ["sw_ver", "hw_ver", "mac", "mic_mac", "type",
                "mic_type", "hwId", "fwId", "oemId", "dev_name"]
        info = self.sys_info
        return {key: info[key] for key in keys if key in info}

    @property
    def location(self):
        """
        Location of the device, as read from sysinfo
        :return: latitude and longitude
        :rtype: dict
        """
        info = self.sys_info
        loc = {"latitude": None,
               "longitude": None}

        if "latitude" in info and "longitude" in info:
            loc["latitude"] = info["latitude"]
            loc["longitude"] = info["longitude"]
        elif "latitude_i" in info and "longitude_i" in info:
            loc["latitude"] = info["latitude_i"]
            loc["longitude"] = info["longitude_i"]
        else:
            logger.warning("Unsupported device location.")

        return loc

    @property
    def rssi(self):
        """
        Returns WiFi signal strenth (rssi)
        :return: rssi
        :rtype: int
        """
        if "rssi" in self.sys_info:
            return int(self.sys_info["rssi"])
        return None

    @property
    def mac(self):
        """
        Returns mac address
        :return: mac address in hexadecimal with colons, e.g. 01:23:45:67:89:ab
        :rtype: str
        """
        info = self.sys_info

        if 'mac' in info:
            return str(info["mac"])
        elif 'mic_mac' in info:
            return str(info['mic_mac'])
        else:
            raise Exception("Unknown mac, please submit a bug"
                            "with sysinfo output.")

    @mac.setter
    def mac(self, mac):
        """
        Sets new mac address
        :param str mac: mac in hexadecimal with colons, e.g. 01:23:45:67:89:ab
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_mac_addr", {"mac": mac})

    def reboot(self, delay=1):
        """
        Reboot the device.
        :param delay: Delay the reboot for `delay` seconds.
        :return: None
        Note that giving a delay of zero causes this to block.
        """
        self._query_helper("system", "reboot", {"delay": delay})

    def turn_off(self):
        """
        Turns the device off.
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    @property
    def is_off(self):
        """
        Returns whether device is off.
        :return: True if device is off, False otherwise.
        :rtype: bool
        """
        return not self.is_on

    def turn_on(self):
        """
        Turns the device on.
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    @property
    def is_on(self):
        """
        Returns whether the device is on.
        :return: True if the device is on, False otherwise.
        :rtype: bool
        :return:
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    @property
    def state_information(self):
        """
        Returns device-type specific, end-user friendly state information.
        :return: dict with state information.
        :rtype: dict
        """
        raise NotImplementedError("Device subclass needs to implement this.")

    def __repr__(self):
        is_on = self.is_on
        if callable(is_on):
            is_on = is_on()
        return "<%s at %s (%s), is_on: %s - dev specific: %s>" % (
            self.__class__.__name__,
            self.host,
            self.alias,
            is_on,
            self.state_information)


class Discover:
    DISCOVERY_QUERY = {"system": {"get_sysinfo": None},
                       "emeter": {"get_realtime": None}}

    @staticmethod
    def discover(protocol=None,
                 port=9999,
                 timeout=3):
        """
        Sends discovery message to 255.255.255.255:9999 in order
        to detect available supported devices in the local network,
        and waits for given timeout for answers from devices.

        :param protocol: Protocol implementation to use
        :param timeout: How long to wait for responses, defaults to 3
        :param port: port to send broadcast messages, defaults to 9999.
        :rtype: dict
        :return: Array of json objects {"ip", "port", "sys_info"}
        """
        if protocol is None:
            protocol = TPLinkSmartHomeProtocol()

        target = "255.255.255.255"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        req = json.dumps(Discover.DISCOVERY_QUERY)
        logger.debug("Sending discovery to %s:%s", target, port)

        encrypted_req = protocol.encrypt(req)
        sock.sendto(encrypted_req[4:], (target, port))

        devices = {}
        logger.debug("Waiting %s seconds for responses...", timeout)

        try:
            while True:
                data, addr = sock.recvfrom(4096)
                ip, port = addr
                info = json.loads(protocol.decrypt(data))
                device_class = Discover._get_device_class(info)
                if device_class is not None:
                    devices[ip] = device_class(ip)
        except socket.timeout:
            logger.debug("Got socket timeout, which is okay.")
        except Exception as ex:
            logger.error("Got exception %s", ex, exc_info=True)
        return devices

    @staticmethod
    def _get_device_class(info):
        """Find SmartDevice subclass for device described by passed data."""
        if "system" in info and "get_sysinfo" in info["system"]:
            sysinfo = info["system"]["get_sysinfo"]
            if "type" in sysinfo:
                type = sysinfo["type"]
            elif "mic_type" in sysinfo:
                type = sysinfo["mic_type"]
            else:
                logger.error("Unable to find the device type field!")
                type = "UNKNOWN"
        else:
            logger.error("No 'system' nor 'get_sysinfo' in response")

        if "smartplug" in type.lower() and "children" in sysinfo:
            # return SmartStrip
            return "boo"
        elif "smartplug" in type.lower():
            return SmartPlug

        return None


class SmartPlug(SmartDevice):
    """Representation of a TP-Link Smart Switch.
    Usage example when used as library:
    p = SmartPlug("192.168.1.105")
    # print the devices alias
    print(p.alias)
    # change state of plug
    p.state = "ON"
    p.state = "OFF"
    # query and print current state of plug
    print(p.state)
    Errors reported by the device are raised as SmartDeviceExceptions,
    and should be handled by the user of the library.
    Note:
    The library references the same structure as defined for the D-Link Switch
    """
    # switch states
    SWITCH_STATE_ON = 'ON'
    SWITCH_STATE_OFF = 'OFF'
    SWITCH_STATE_UNKNOWN = 'UNKNOWN'

    def __init__(self,
                 host,
                 protocol=None,
                 context=None):
        SmartDevice.__init__(self, host, protocol, context)
        self._type = "emeter"

    @property
    def state(self):
        """
        Retrieve the switch state
        :returns: one of
                  SWITCH_STATE_ON
                  SWITCH_STATE_OFF
                  SWITCH_STATE_UNKNOWN
        :rtype: str
        """
        relay_state = self.sys_info['relay_state']

        if relay_state == 0:
            return SmartPlug.SWITCH_STATE_OFF
        elif relay_state == 1:
            return SmartPlug.SWITCH_STATE_ON
        else:
            logger.warning("Unknown state %s returned.", relay_state)
            return SmartPlug.SWITCH_STATE_UNKNOWN

    @state.setter
    def state(self, value):
        """
        Set the new switch state
        :param value: one of
                    SWITCH_STATE_ON
                    SWITCH_STATE_OFF
        :raises ValueError: on invalid state
        :raises SmartDeviceException: on error
        """
        if not isinstance(value, str):
            raise ValueError("State must be str, not of %s.", type(value))
        elif value.upper() == SmartPlug.SWITCH_STATE_ON:
            self.turn_on()
        elif value.upper() == SmartPlug.SWITCH_STATE_OFF:
            self.turn_off()
        else:
            raise ValueError("State %s is not valid.", value)

    @property
    def brightness(self):
        """
        Current brightness of the device, if supported.
        Will return a a range between 0 - 100.
        :returns: integer
        :rtype: int
        """
        if not self.is_dimmable:
            return None

        return int(self.sys_info['brightness'])

    @brightness.setter
    def brightness(self, value):
        """
        Set the new switch brightness level.
        Note:
        When setting brightness, if the light is not
        already on, it will be turned on automatically.
        :param value: integer between 1 and 100
        """
        if not self.is_dimmable:
            return

        if not isinstance(value, int):
            raise ValueError("Brightness must be integer, "
                             "not of %s.", type(value))
        elif value > 0 and value <= 100:
            self.turn_on()
            self._query_helper("smartlife.iot.dimmer", "set_brightness",
                               {"brightness": value})
        else:
            raise ValueError("Brightness value %s is not valid.", value)

    @property
    def is_dimmable(self):
        """
        Whether the switch supports brightness changes
        :return: True if switch supports brightness changes, False otherwise
        :rtype: bool
        """
        return "brightness" in self.sys_info

    @property
    def has_emeter(self):
        """
        Returns whether device has an energy meter.
        :return: True if energy meter is available
                 False otherwise
        """
        features = self.sys_info['feature'].split(':')
        return SmartDevice.FEATURE_ENERGY_METER in features

    @property
    def is_on(self):
        """
        Returns whether device is on.
        :return: True if device is on, False otherwise
        """
        return bool(self.sys_info['relay_state'])

    def turn_on(self):
        """
        Turn the switch on.
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_relay_state", {"state": 1})

    def turn_off(self):
        """
        Turn the switch off.
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_relay_state", {"state": 0})

    @property
    def led(self):
        """
        Returns the state of the led.
        :return: True if led is on, False otherwise
        :rtype: bool
        """
        return bool(1 - self.sys_info["led_off"])

    @led.setter
    def led(self, state):
        """
        Sets the state of the led (night mode)
        :param bool state: True to set led on, False to set led off
        :raises SmartDeviceException: on error
        """
        self._query_helper("system", "set_led_off", {"off": int(not state)})

    @property
    def on_since(self):
        """
        Returns pretty-printed on-time
        :return: datetime for on since
        :rtype: datetime
        """
        if self.context:
            for plug in self.sys_info["children"]:
                if plug["id"] == self.context:
                    on_time = plug["on_time"]
                    break
        else:
            on_time = self.sys_info["on_time"]

        return datetime.datetime.now() - datetime.timedelta(seconds=on_time)

    @property
    def state_information(self):
        """
        Return switch-specific state information.
        :return: Switch information dict, keys in user-presentable form.
        :rtype: dict
        """
        info = {
            'LED state': self.led,
            'On since': self.on_since
        }
        if self.is_dimmable:
            info["Brightness"] = self.brightness
        return info


#
# class SmartStrip(SmartPlug):
#     """Representation of a TP-Link Smart Power Strip.
#     Usage example when used as library:
#     p = SmartStrip("192.168.1.105")
#     # print the devices alias
#     print(p.alias)
#     # change state of plug
#     p.state = "ON"
#     p.state = "OFF"
#     # query and print current state of plug
#     print(p.state)
#     Errors reported by the device are raised as SmartDeviceExceptions,
#     and should be handled by the user of the library.
#     Note:
#     The library references the same structure as defined for the D-Link Switch
#     """
#
#     def __init__(self,
#                  host: str,
#                  protocol: 'TPLinkSmartHomeProtocol' = None) -> None:
#         SmartPlug.__init__(self, host, protocol)
#         self.emeter_type = "emeter"
#         self.plugs = {}
#         children = self.sys_info["children"]
#         self.num_children = len(children)
#         for plug in range(self.num_children):
#             self.plugs[plug] = SmartPlug(host, protocol,
#                                          context=children[plug]["id"])
#
#     def raise_for_index(self, index: int):
#         """
#         Raises SmartStripException if the plug index is out of bounds
#         :param index: plug index to check
#         :raises SmartStripException: index out of bounds
#         """
#         if index not in range(self.num_children):
#             raise Exception("plug index of %d "
#                                       "is out of bounds" % index)
#
#     @property
#     def state(self) -> Dict[int, str]:
#         """
#         Retrieve the switch state
#         :returns: list with the state of each child plug
#                   SWITCH_STATE_ON
#                   SWITCH_STATE_OFF
#                   SWITCH_STATE_UNKNOWN
#         :rtype: dict
#         """
#         states = {}
#         children = self.sys_info["children"]
#         for plug in range(self.num_children):
#             relay_state = children[plug]["state"]
#
#             if relay_state == 0:
#                 switch_state = SmartPlug.SWITCH_STATE_OFF
#             elif relay_state == 1:
#                 switch_state = SmartPlug.SWITCH_STATE_ON
#             else:
#                 _LOGGER.warning("Unknown state %s returned for plug %u.",
#                                 relay_state, plug)
#                 switch_state = SmartPlug.SWITCH_STATE_UNKNOWN
#
#             states[plug] = switch_state
#
#         return states
#
#     @state.setter
#     def state(self, value: str):
#         """
#         Sets the state of all plugs in the strip
#         :param value: one of
#                     SWITCH_STATE_ON
#                     SWITCH_STATE_OFF
#         :raises ValueError: on invalid state
#         :raises SmartDeviceException: on error
#         """
#         if not isinstance(value, str):
#             raise ValueError("State must be str, not of %s.", type(value))
#         elif value.upper() == SmartPlug.SWITCH_STATE_ON:
#             self.turn_on()
#         elif value.upper() == SmartPlug.SWITCH_STATE_OFF:
#             self.turn_off()
#         else:
#             raise ValueError("State %s is not valid.", value)
#
#     def set_state(self, value: str, *, index: int = -1):
#         """
#         Sets the state of a plug on the strip
#         :param value: one of
#                     SWITCH_STATE_ON
#                     SWITCH_STATE_OFF
#         :param index: plug index (-1 for all)
#         :raises ValueError: on invalid state
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         if index < 0:
#             self.state = value
#         else:
#             self.raise_for_index(index)
#             self.plugs[index].state = value
#
#     def is_on(self, *, index: int = -1) -> Any:
#         """
#         Returns whether device is on.
#         :param index: plug index (-1 for all)
#         :return: True if device is on, False otherwise, Dict without index
#         :rtype: bool if index is provided
#                 Dict[int, bool] if no index provided
#         :raises SmartStripException: index out of bounds
#         """
#         children = self.sys_info["children"]
#         if index < 0:
#             is_on = {}
#             for plug in range(self.num_children):
#                 is_on[plug] = bool(children[plug]["state"])
#             return is_on
#         else:
#             self.raise_for_index(index)
#             return bool(children[index]["state"])
#
#     def turn_on(self, *, index: int = -1):
#         """
#         Turns outlets on
#         :param index: plug index (-1 for all)
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         if index < 0:
#             self._query_helper("system", "set_relay_state", {"state": 1})
#         else:
#             self.raise_for_index(index)
#             self.plugs[index].turn_on()
#
#     def turn_off(self, *, index: int = -1):
#         """
#         Turns outlets off
#         :param index: plug index (-1 for all)
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         if index < 0:
#             self._query_helper("system", "set_relay_state", {"state": 0})
#         else:
#             self.raise_for_index(index)
#             self.plugs[index].turn_off()
#
#     def on_since(self, *, index: int = -1) -> Any:
#         """
#         Returns pretty-printed on-time
#         :param index: plug index (-1 for all)
#         :return: datetime for on since
#         :rtype: datetime with index
#                 Dict[int, str] without index
#         :raises SmartStripException: index out of bounds
#         """
#         if index < 0:
#             on_since = {}
#             children = self.sys_info["children"]
#             for plug in range(self.num_children):
#                 on_since[plug] = \
#                     datetime.datetime.now() - \
#                     datetime.timedelta(seconds=children[plug]["on_time"])
#             return on_since
#         else:
#             self.raise_for_index(index)
#             return self.plugs[index].on_since
#
#     @property
#     def state_information(self) -> Dict[str, Any]:
#         """
#         Returns strip-specific state information.
#         :return: Strip information dict, keys in user-presentable form.
#         :rtype: dict
#         """
#         state = {'LED state': self.led}
#         on_since = self.on_since()
#         is_on = self.is_on()
#         for plug_index in range(self.num_children):
#             plug_number = plug_index + 1
#             if is_on[plug_index]:
#                 state['Plug %d on since' % plug_number] = on_since[plug_index]
#
#         return state
#
#     def get_emeter_realtime(self, *, index: int = -1) -> Optional[Any]:
#         """
#         Retrieve current energy readings from device
#         :param index: plug index (-1 for all)
#         :returns: list of current readings or None
#         :rtype: Dict, Dict[int, Dict], None
#                 Dict if index is provided
#                 Dict[int, Dict] if no index provided
#                 None if device has no energy meter or error occurred
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         if not self.has_emeter:
#             return None
#
#         if index < 0:
#             emeter_status = {}
#             for plug in range(self.num_children):
#                 emeter_status[plug] = self.plugs[plug].get_emeter_realtime()
#             return emeter_status
#         else:
#             self.raise_for_index(index)
#             return self.plugs[index].get_emeter_realtime()
#
#     @property
#     def icon(self):
#         """
#         Override for base class icon property, SmartStrip and children do not
#         have icons.
#         :raises NotImplementedError: always
#         """
#         raise NotImplementedError("no icons for this device")
#
#     def get_alias(self, *, index: int = -1) -> Union[str, Dict[int, str]]:
#         """
#         Gets the alias for a plug.
#         :param index: plug index (-1 for all)
#         :return: the current power consumption in Watts.
#                  None if device has no energy meter.
#         :rtype: str if index is provided
#                 Dict[int, str] if no index provided
#         :raises SmartStripException: index out of bounds
#         """
#         children = self.sys_info["children"]
#
#         if index < 0:
#             alias = {}
#             for plug in range(self.num_children):
#                 alias[plug] = children[plug]["alias"]
#             return alias
#         else:
#             self.raise_for_index(index)
#             return children[index]["alias"]
#
#     def set_alias(self, alias: str, index: int):
#         """
#         Sets the alias for a plug
#         :param index: plug index
#         :param alias: new alias
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         self.raise_for_index(index)
#         self.plugs[index].alias = alias
#
#     def get_emeter_daily(self,
#                          year: int = None,
#                          month: int = None,
#                          kwh: bool = True,
#                          *,
#                          index: int = -1) -> Optional[Dict]:
#         """
#         Retrieve daily statistics for a given month
#         :param year: year for which to retrieve statistics (default: this year)
#         :param month: month for which to retrieve statistics (default: this
#                       month)
#         :param kwh: return usage in kWh (default: True)
#         :return: mapping of day of month to value
#                  None if device has no energy meter or error occurred
#         :rtype: dict
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         if not self.has_emeter:
#             return None
#
#         emeter_daily = {}
#         if index < 0:
#             for plug in range(self.num_children):
#                 emeter_daily = self.plugs[plug].get_emeter_daily(year=year,
#                                                                  month=month,
#                                                                  kwh=kwh)
#             return emeter_daily
#         else:
#             self.raise_for_index(index)
#             return self.plugs[index].get_emeter_daily(year=year,
#                                                       month=month,
#                                                       kwh=kwh)
#
#     def get_emeter_monthly(self,
#                            year: int = None,
#                            kwh: bool = True,
#                            *,
#                            index: int = -1) -> Optional[Dict]:
#         """
#         Retrieve monthly statistics for a given year.
#         :param year: year for which to retrieve statistics (default: this year)
#         :param kwh: return usage in kWh (default: True)
#         :return: dict: mapping of month to value
#                  None if device has no energy meter
#         :rtype: dict
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         if not self.has_emeter:
#             return None
#
#         emeter_monthly = {}
#         if index < 0:
#             for plug in range(self.num_children):
#                 emeter_monthly = self.plugs[plug].get_emeter_monthly(year=year,
#                                                                      kwh=kwh)
#             return emeter_monthly
#         else:
#             self.raise_for_index(index)
#             return self.plugs[index].get_emeter_monthly(year=year,
#                                                         kwh=kwh)
#
#     def erase_emeter_stats(self, *, index: int = -1) -> bool:
#         """
#         Erase energy meter statistics
#         :param index: plug index (-1 for all)
#         :return: True if statistics were deleted
#                  False if device has no energy meter.
#         :rtype: bool
#         :raises SmartDeviceException: on error
#         :raises SmartStripException: index out of bounds
#         """
#         if not self.has_emeter:
#             return False
#
#         if index < 0:
#             for plug in range(self.num_children):
#                 self.plugs[plug].erase_emeter_stats()
#         else:
#             self.raise_for_index(index)
#             self.plugs[index].erase_emeter_stats()
#
#         # As query_helper raises exception in case of failure, we have
#         # succeeded when we are this far.
#         return True
#
#

# plug_atts = Discover.discover().values()[0]
# plug = SmartPlug(plug_atts.host)
#
# if plug.is_off:
#     plug.turn_on()
# elif plug.is_on:
#     plug.turn_off()
