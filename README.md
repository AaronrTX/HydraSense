# HydraSense
This page will hold the coed as well as the instructions on how to set up influxDB and grafana. 

Influx DB Set Up (Windows) 

1) Open up Windows powershell (with admin permissions)
2) Navigate to the folder that holds your influx executable (Example : C:\Program Files\InfluxData)
3) Once you are at the correct path, you can startup the server database with the following command : .\influxd.exe
4) Once server is turned on, navigate to the webpage of InfluxDB (http://127.0.0.1:8086/signin)

InfluxDB Navigation
1) Once in Influx, navigate to the Buckets section.
2) Pick some sample data from the following website (https://docs.influxdata.com/influxdb/cloud/reference/sample-data/)
3) You will need to copy the function for each dataset into the Query Builder so you can get access to it

Grafana Set Up (Windows) 
1) Go to the following website and download the installer (https://grafana.com/grafana/download)
2) Hit Next until its complete
3) To activate Grafana go to Windows Start -> Services -> Grafana -> Start
4) Then go to this website to set up your account (http://localhost:3000)

Grafana/Influx Connection 
1) On Grafana go to Connections -> Add New Data Source
2) 
