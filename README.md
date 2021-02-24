# rayleigh-api

A minimal wrapper for getting data from the rayleighconnect™ API into Pandas.

## Usage

```python
from rayleigh import client, decode_credentials

client_id, access_token = decode_credentials("tdnTD35 ... bF46F60=")
client = Client(client_id, access_token)

devices_of_interest = [
    "300000000000001@rayleigh",
    "300000000000002@rayleigh",
    "300000000000003@rayleigh",
]

sensors_of_interest = ["e1.kwh", "e1.i3p"]

data = (
    client
    .get_devices(devices_of_interest)
    .get_sensor(sensors_of_interest)
    .get_data(from_date="2021-01-01", to_date="2021-02-01")
)

data
```

```
device                    sensor    datetime           
300000000000001@rayleigh  e1.kwh    2021-01-01 00:01:00   10.0
                                    2021-01-01 00:02:00   11.0
                                    2021-01-01 00:03:00   12.0
                                    2021-01-01 00:04:00   13.0
                                    2021-01-01 00:05:00   14.0
                                                          ... 
300000000000003@rayleigh  e1.i3p_3  2021-01-31 23:55:00    2.0
                                    2021-01-31 23:56:00    2.5
                                    2021-01-31 23:57:00    2.0
                                    2021-01-31 23:58:00    1.5
                                    2021-01-31 23:59:00    2.0
Name: value, Length: 178560, dtype: float64
```

## Notes

This library are not associated with Raleigh Instruments or UXEON.  
rayleighconnect is a trademark of Rayleigh Instruments Limited.
