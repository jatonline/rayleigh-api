# rayleigh-api

A minimal wrapper for getting data from the rayleighconnect™ API into Pandas.

## Usage

```python
from rayleigh import Client, decode_credentials

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
        datetime             device                    sensor    value
     0  2021-01-01 00:01:00  300000000000001@rayleigh  e1.kwh     10.0
     1  2021-01-01 00:02:00  300000000000001@rayleigh  e1.kwh     11.0
     2  2021-01-01 00:03:00  300000000000001@rayleigh  e1.kwh     12.0
     3  2021-01-01 00:04:00  300000000000001@rayleigh  e1.kwh     13.0
     4  2021-01-01 00:05:00  300000000000001@rayleigh  e1.kwh     14.0
 ...     ...                  ...                       ...        ... 
178555  2021-01-31 23:55:00  300000000000003@rayleigh  e1.i3p_3    2.0
178556  2021-01-31 23:56:00  300000000000003@rayleigh  e1.i3p_3    2.5
178557  2021-01-31 23:57:00  300000000000003@rayleigh  e1.i3p_3    2.0
178558  2021-01-31 23:58:00  300000000000003@rayleigh  e1.i3p_3    1.5
178559  2021-01-31 23:59:00  300000000000003@rayleigh  e1.i3p_3    2.0
```

## Notes

This library is not associated with Raleigh Instruments or UXEON.  
rayleighconnect is a trademark of Rayleigh Instruments Limited.
