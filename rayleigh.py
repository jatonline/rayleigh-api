"""
A minimal wrapper for getting data from the rayleighconnect™ API into Pandas.

This library are not associated with Raleigh Instruments or UXEON.
rayleighconnect is a trademark of Rayleigh Instruments Limited.
"""

__author__ = "James Thomas"
__license__ = "MIT License"

import base64
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
import json

import pandas as pd
import requests


def decode_credentials(auth_string):
    """
    Helper function to decode a base64-encoded response from the access token
    generator, into your client_id and access_token.

    You can get an access token via
    <https://www.rayleighconnect.net/oauth2/authorize?client_id=uob&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=token>.
    The response you get from the access token generator will be a
    base64-encoded string, which you can decode using this function.

    Parameters
    ----------
    auth_string : str
        The base64-encoded response from the access token generator.

    Returns
    -------
    client_id : str access_token : str

    Usage
    -----
    >>> client_id, access_token = decode_credentials("tdnTD35 ... bF46F60=")
    """
    credentials = base64.b64decode(auth_string)
    credentials = json.loads(credentials)
    return credentials["client_id"], credentials["access_token"]


@dataclass
class Client:
    """
    A client to make requests to the rayleighconnect™ API.

    This is a very basic client that will only retrieve the general parameters
    of devices and sensors, and get their data in a helpful pandas-compatible
    way. All of the requests are GETs, there are no POSTs or PUTs.

    Parameters
    ----------
    client_id : str
        Your username for the API, which is the same as your login to the
        rayleighconnect.net website, which is likely to be your email address.
    access_token : str
        The secret access token you have been issued for API use. If you don't
        have one, then you can get one via
        <https://www.rayleighconnect.net/oauth2/authorize?client_id=uob&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=token>.
        The response you get from the access token generator will be a
        base64-encoded string, which you can decode using the
        `decode_credentials()` helper-function.
    app_id : str, default "uob"
        The app identifier that you have been issued.
    endpoint : str, default "https://api.uxeon.com/consumer/v1"
        The endpoint address for the API. Should not need changing if you're
        using rayleighconnect.net.
    debug : str, default False
        Whether to print each request as it is made.
    """

    client_id: str
    access_token: str = field(repr=False)
    app_id: str = "uob"
    endpoint: str = "https://api.uxeon.com/consumer/v1"
    debug: bool = False

    def request(self, path, method="get", data=None, **params):
        """
        Make an API request. This method is generally used internally, but you
        can call it yourself for additional functionality.

        None of the methods defined in this API wrapper will make anything other
        than GET requests, however if you call it manually you can make any kind
        of request that you like.

        Parameters
        ----------
        path : str
            The call for the API request, without slashes on either end, e.g.
            "devices".
        **params
            Additional parameters to include in the query string of the API
            request, used for filtering by date, etc.

        For non-GET requests, the following parameters can also be used:

        method : str, default "get"
            The type of HTTP request to make, can be "get", "post", "put".
        data : dict, list of tuples, bytes, or file-like, optional
            For POST and PUT requests, the object to send in the body of the
            request.

        Returns
        -------
        dict
            The response from the API, parsed as JSON into a dict.
        """

        # app_id and access_token need to be provided with every request (as
        # query parameters), as does the client_id (in the URL). The caller can
        # specify the api path to call, in addition to further params.
        request_url = f"{self.endpoint}/{self.client_id}/{path}"
        params["app_id"] = self.app_id
        params["access_token"] = self.access_token

        response = requests.request(
            method,
            request_url,
            params=params,
            data=data,
        )
        if self.debug:
            print(f"Requested: {response.url.replace(self.access_token, '***')}")

        # Check for errors
        response.raise_for_status()

        # Response should be json
        return response.json()

    @cached_property
    def devices(self):
        """
        Get all of the devices available on this account.

        Returns
        -------
        `DevicesList` of `Device`s
            A `DevicesList` is a special type of list with an additional methods
            to recursively load sensors belonging to those devices.

        This property is cached, so it is only requested once per invocation of
        the `Client`.
        """
        devices = self.request("devices")
        return DevicesList(Device(device, self) for device in devices)

    def get_device(self, device_id):
        """
        Get a specific device.

        Parameters
        ----------
        device_id : str
            The device_id should be in the format "300000000000000@rayleigh".

        Returns
        -------
        `Device`
            The requested device.

        Raises
        ------
        KeyError
            If the device is not found.
        """
        try:
            return self.get_devices([device_id])[0]
        except IndexError:
            raise KeyError("device not found")

    def get_devices(self, device_ids):
        """
        Get one or more devices.

        Any devices that are not found will not be returned, and will not raise
        and exception.

        Parameters
        ----------
        device_ids : list of str, optional
            A list of requested device_ids. Each device_id should be in the
            format "300000000000000@rayleigh". Defaults to returning all devices.

        Returns
        -------
        `DevicesList` of `Device`s
            A `DevicesList` is a special type of list with an additional methods
            to recursively load sensors belonging to those devices.
        """
        if not device_ids:
            # Default to all devices
            return self.devices
        return DevicesList(
            device
            for device in self.devices
            if device.id in device_ids
        )


@dataclass
class Device:
    """
    Represents a remote rayleighinstruments.net device.

    Parameters
    ----------
    params : dict
        The device parameters dictionary returned by the API. Must at least
        contain an "id" key.
    client : `Client`
        The API client used to retrieve sensors and data for this device.
    """
    params: dict
    client: Client

    @property
    def id(self):
        """
        The id reported by the device.

        Returns
        -------
        str
            The device_id is in the format: "300000000000000@rayleigh".
        """
        return self.params["id"]

    @cached_property
    def sensors(self):
        """
        Get all of the sensors available on this device.

        Returns
        -------
        `SensorsList` of `Sensors`s
            A `SensorsList` is a special type of list with an additional methods
            to recursively load data relating to those sensors.

        This property is cached, so it is only requested once per invocation of
        the `Sensor`.
        """
        sensors = self.client.request(f"devices/{self.id}")

        # Data is returned as nested dictionaries. The outer dictionary has a
        # single item with the device_id as the key and a dictionary of
        # sensor_id => sensor_params as its value. The inner dictionary of
        # sensor_params also includes the sensor_id, so the keys can be safely
        # discarded.
        sensors = sensors[self.id].values()

        return SensorList(Sensor(sensor, self) for sensor in sensors)

    def get_sensor(self, sensor_id):
        """
        Get a specific sensor.

        Parameters
        ----------
        sensor_id : str
            The sensor_id should be in the format "e1", "e1.i3p", "158" etc.

        Returns
        -------
        `Sensor`
            The requested sensor.

        Raises
        ------
        KeyError
            If the sensor is not found.
        """
        try:
            return self.get_sensors([sensor_id])[0]
        except IndexError:
            raise KeyError("sensor not found")

    def get_sensors(self, sensor_ids):
        """
        Get one or more sensors.

        Any sensors that are not found will not be returned, and will not raise
        and exception.

        Parameters
        ----------
        sensor_ids : list of str, optional
            A list of requested sensor_ids. The sensor_id should be in the
            format "e1", "e1.i3p", "158" etc. Defaults to returning all sensors.

        Returns
        -------
        `SensorsList` of `Sensor`s
            A `SensorsList` is a special type of list with an additional methods
            to recursively load data relating to those sensors.
        """
        if not sensor_ids:
            # Default to all sensors
            return self.sensors
        return SensorList(
            sensor
            for sensor in self.sensors
            if sensor.id in sensor_ids
        )

    def __repr__(self):
        return f"Device({self.id})"


@dataclass
class Sensor:
    params: dict
    device: Device

    @property
    def id(self):
        """
        The id reported by the sensor.

        Returns
        -------
        str
            The sensor_id is in the format: "e1", "e1.i3p", "158" etc. Needs to
            be combined with the device_id to uniquely specify a sensor.
        """
        return self.params["id"]

    def get_data(self, from_date, to_date):
        """
        Get data for this sensor, in a specific date range.

        Parameters
        ----------
        from_date : datetime-like str, or anything that acts like a datetime
        to_date : datetime-like str, or anything that acts like a datetime

        Returns
        -------
        pd.Series
            Series of sensor values in long-format. The index of the series is a
            MultiIndex of (device_id, sensor_id, datetime). Be aware that some
            sensors report more than one value per timestamp (e.g. a 3-phase
            electricity meter) and this will be split into multiple rows.
        """
        return SensorList([self]).get_data(from_date, to_date)

    def __repr__(self):
        return f"Sensor({self.device.id}:({self.id}))"


class DevicesList(list):
    """
    A `DevicesList` is a special type of list with an additional methods to
    recursively load sensors belonging to those devices.
    """
    def get_sensors(self, sensor_ids):
        """
        Recursively get one or more sensors belonging to these devices.

        Any sensors that are not found will not be returned, and will not raise
        an exception.

        Parameters
        ----------
        sensor_ids : list of str, optional
            A list of requested sensor_ids. The sensor_id should be in the
            format "e1", "e1.i3p", "158" etc. Defaults to returning all sensors.

        Returns
        -------
        `SensorsList` of `Sensor`s
            A `SensorsList` is a special type of list with an additional methods
            to recursively load data relating to those sensors.
        """
        if not sensor_ids:
            # Default to all sensors
            return SensorList(chain(
                *(device.sensors for device in self)
            ))
        return SensorList(chain(
            *(device.get_sensors(sensor_ids) for device in self)
        ))

    def __repr__(self):
        id_list = ', '.join(device.id for device in self)
        return f"DevicesList([{id_list}])"


class SensorList(list):
    """
    A `SensorsList` is a special type of list with an additional methods to
    recursively load data relating to those sensors.
    """
    def get_data(self, from_date, to_date):
        """
        Recursively get data for these sensors, in a specific date range.

        Parameters
        ----------
        from_date : datetime-like str, or anything that acts like a datetime
        to_date : datetime-like str, or anything that acts like a datetime

        Returns
        -------
        pd.Series
            Series of sensor values in long-format. The index of the series is a
            MultiIndex of (device_id, sensor_id, datetime). Be aware that some
            sensors report more than one value per timestamp (e.g. a 3-phase
            electricity meter) and this will be split into multiple rows.
        """
        sensor_ids = ",".join(sensor.id for sensor in self)

        # Convert dates into timestamps expressed in milliseconds
        from_date = int(pd.to_datetime(from_date).timestamp() * 1000)
        to_date = int(pd.to_datetime(to_date).timestamp() * 1000)

        # Get the client from the first sensor
        client = self[0].device.client

        # Get the device and sensor ids to query - grouping sensor_ids under
        # each device_id
        to_query = defaultdict(list)
        for sensor in self:
            to_query[sensor.device.id].append(sensor.id)
        query = ",".join(
            f"{device_id}:({','.join(sensor_ids)})"
            for device_id, sensor_ids in to_query.items()
        )

        data = client.request(
            f"data/{query})",
            **{"from": from_date, "to": to_date},
        )

        # Data is returned as nested dictionaries. The outer dictionary has a
        # single item with the device_id as the key and a dictionary of
        # sensor_id => sensor_data as its value.

        # Each sensor_data is a list of [datetime, value] or
        # [datetime, value, value, ...] (depending on the type of sensor), or is
        # empty and should be discarded.

        def loop_through_sensors(data):
            for device_id, device_data in data.items():
                for sensor_id, sensor_data in device_data.items():
                    if sensor_data:
                        yield device_id, sensor_id, sensor_data

        def get_column_headers(sensor_id, sensor_data):
            num_data_columns = len(sensor_data[0]) - 1
            if num_data_columns == 1:
                return ["datetime", sensor_id]
            return ["datetime"] + [f"{sensor_id}_{i}" for i in range(num_data_columns)]

        # We create a DataFrame from each key-value pair of the inner dictionary
        # (taking care to allocate multiple columns if required) and then join
        # those together in a long format Series, indexed by device, sensor and
        # datetime.

        data = (
            (
                pd.DataFrame(sensor_data, columns=get_column_headers(sensor_id, sensor_data))
                .melt(id_vars="datetime", var_name="sensor")
                .assign(device=device_id)
            )
            for device_id, sensor_id, sensor_data in loop_through_sensors(data)
        )
        try:
            data = pd.concat(data)
        except ValueError as e:
            if str(e) == "No objects to concatenate":
                # There was no data returned
                raise KeyError("no data for this device/sensor/datetime combination")
            # Something else
            raise

        # Datetime index is provided milliseconds
        data["datetime"] = pd.to_datetime(data["datetime"], unit="ms")

        # Index by device, sensor and then by datetime
        data = data.set_index(["device", "sensor", "datetime"]).sort_index()

        # Select remaining column to produce a Series
        return data["value"]

    def __repr__(self):
        id_list = ', '.join(f"{sensor.device.id}:({sensor.id})" for sensor in self)
        return f"SensorList([{id_list}])"
