## IamMeter

Python Client for IamMeter device.

See https://www.iammeter.com/docs

##### Create a new connection by supplying IamMeter host and port(default:80)

`import client`

`s= client.IamMeter("host",port)`

`print(s.client.get_data())`

##### ChangeLog

0.2.1 power_meter.py deprecated,using client.py instead.
Change return format,more readable.

0.1.7 first commit，return sensor‘s map

