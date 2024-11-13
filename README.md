# HydraSense
This page will hold the coed as well as the instructions on how to set up influxDB and grafana. 

**Influx DB Set Up (Windows)** 

1) Open up Windows powershell (with admin permissions)
2) Navigate to the folder that holds your influx executable (Example : C:\Program Files\InfluxData)
3) Once you are at the correct path, you can startup the server database with the following command : .\influxd.exe
4) Once server is turned on, navigate to the webpage of InfluxDB (http://127.0.0.1:8086/signin)

**InfluxDB Navigation**
1) Once in Influx, navigate to the Buckets section.
2) Pick some sample data from the following website (https://docs.influxdata.com/influxdb/cloud/reference/sample-data/)
3) You will need to copy the function for each dataset into the Query Builder so you can get access to it

Grafana Set Up (Windows) 
1) Go to the following website and download the installer (https://grafana.com/grafana/download)
2) Hit Next until its complete
3) To activate Grafana go to Windows Start -> Services -> Grafana -> Start
4) Then go to this website to set up your account (http://localhost:3000)

**Grafana/Influx Connection** 
1) On Grafana go to Connections -> Add New Data Source
2) Fill in the following sections :
   HTTPS URL : http://localhost:8086
   Turn on Auth
   Change the query language to Flux
   Put in your login credentials for both Influx & Grafana
   To create the API token go to Influx -> API Tokens -> Create API Token (insert this to the Grafana page)
   Insert the default bucket name

   This video probably explains it better hehehehe (https://www.youtube.com/watch?v=Jszd7zrl-_U)

**IMPORTANT***
To be able to embedd the grafana panels onto the HTML Page follow these steps : 
1) You need to modify your configuration file so traverse to (C:\Program Files\GrafanaLabs\grafana\conf\defaults)
2) In your defaults file you need to change the following : (This video will help https://www.youtube.com/watch?v=Ct9PjmrExzo)
   allow_embedding = true
   auth.anonymous
     enabled = true
     org_name = <<org name>> (could leave it as is)
     org_role = Viewer
**YOU WILL NEED TO RESTART GRAFANA TO SEE THESE CHANGES **
Go to Windows Start -> Services -> Grafana -> Click on Restart (BOOM Youre done) 


**How to Actually Create a HTML Dashboard**
1) Go to Dashboards (on Grafana) then click New
2) Add Visualization
3) Data Source = influxdb
4) In the query section copy and paste the same query you had on InfluxDB
5) Once you have copied tha query refresh the page and the data should pop up
6) Once your Dashbaord is established, close out of that page and go back to the dashboard homepage
7) There hit on the three dots on the upper right, and select Share -> Embed (This is what you need to import to the HTML) 
   
   
   
   
