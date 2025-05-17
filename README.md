# HydraSense
Initial coding for Webpage

General Instructions 


**Influx DB Set Up (Windows)**

Open up Windows powershell (with admin permissions)
Navigate to the folder that holds your influx executable (Example : C:\Program Files\InfluxData)
Once you are at the correct path, you can startup the server database with the following command : .\influxd.exe
Once server is turned on, navigate to the webpage of InfluxDB (http://127.0.0.1:8086/signin)
InfluxDB Navigation

Once in Influx, navigate to the Buckets section.
Pick some sample data from the following website (https://docs.influxdata.com/influxdb/cloud/reference/sample-data/)
You will need to copy the function for each dataset into the Query Builder so you can get access to it
Grafana Set Up (Windows)

Go to the following website and download the installer (https://grafana.com/grafana/download)
Hit Next until its complete
To activate Grafana go to Windows Start -> Services -> Grafana -> Start
Then go to this website to set up your account (http://localhost:3000)
Grafana/Influx Connection

On Grafana go to Connections -> Add New Data Source

Fill in the following sections : HTTPS URL : http://localhost:8086 Turn on Auth Change the query language to Flux Put in your login credentials for both Influx & Grafana To create the API token go to Influx -> API Tokens -> Create API Token (insert this to the Grafana page) Insert the default bucket name

This video probably explains it better hehehehe (https://www.youtube.com/watch?v=Jszd7zrl-_U)

IMPORTANT* To be able to embedd the grafana panels onto the HTML Page follow these steps :

You need to modify your configuration file so traverse to (C:\Program Files\GrafanaLabs\grafana\conf\defaults)
In your defaults file you need to change the following : (This video will help https://www.youtube.com/watch?v=Ct9PjmrExzo) allow_embedding = true auth.anonymous enabled = true org_name = <> (could leave it as is) org_role = Viewer
YOU WILL NEED TO RESTART GRAFANA TO SEE THESE CHANGES Go to Windows Start -> Services -> Grafana -> Click on Restart (BOOM Youre done)

**How to Actually Create a HTML Dashboard**

Go to Dashboards (on Grafana) then click New
Add Visualization
Data Source = influxdb
In the query section copy and paste the same query you had on InfluxDB
Once you have copied tha query refresh the page and the data should pop up
Once your Dashbaord is established, close out of that page and go back to the dashboard homepage
There hit on the three dots on the upper right, and select Share -> Embed (This is what you need to import to the HTML)

**Node-Red**
This is the video I watched : https://www.youtube.com/watch?v=v8MTF4DdpYI
1)	Install : https://nodered.org/docs/getting-started/windows
  a.	Do all the steps mentioned on there 
2)	To configure : 	
  a.	Open up windows power shell with admin 
  b.	Command : node-red admin init
  c.	Settings File : Enter 
  d.	User Security : set up your login (you will need it to access the website : localhost:1880)
  e.	User permissions : full access 
  f.	Add another user : No
  g.	Projects  : Yes , manual
  h.	Editor Settings : default, monaco 
  i.	Node settings : yes 
3)	To open it : node-red start 
  a.	Once you enter that command go a browser and type  : localhost:1880
  b.	Login and then do a simple example 

**NOTE**
The Influx Nodes dont come automatically with Node-RED. You need to install separately. 
1. Open Node-RED
2. Go to Manage -> Install
3. Search for node-red-contrib-influxdb and install
4. After that you will need to configure the node with our database

Good set of instructions for this : https://flowfuse.com/node-red/database/influxdb/

The current Node-Red script is just using a datapoint insert, formatting the data and then connecting it to Influx. 
To use that example, follow these steps : 
  1. Get an Inject node
     a. In the properties section => msg.value = 50* $random() [choose expression from dropdowm]
     b. Make sure to configure the inject to be an interval every 5 seconds.
  2. Get a Change Node
     a. In the Rules section put 3 sets :
           Set 1 : msg.fields.temperature/msg.value
           Set 2 : msg.tags.timestamp /milliseconds since epoch [choose timestamp from dropdowm]
           Set 3 : msg.payload / $append(fields,tags) [choose expression from dropdowm]
  3. Get an Influx out Node
       a. Name = whatever you want
       b. Server  = https://us-east-1-1.aws.cloud2.influxdata.com, Token = Go to Influx and get the Node-RED token
       c. Organization = HydraSense
       d. Bucket = demo_bucket
       e. Measurment = Pilot
       f. Time Precision = Milliseconds (ms)

To put in an MQTT node 
Server Config
  Server = USE YOUR OWN BROKER IP
    a. Hit the connect automatically button
  Protocol = MQTT V3.1.1
  Keep Alive = 60 
  Click the iSession button
Action = subscribe to single topic
QoS = 0
Output = auto-detect 

You can add a debug node and connect it to see the msg.payload messgaes (click on the debug window)

**How to Run WebPage** 
Disclaimer: You need to setup a dummy account (preferably gmail), and create a app password.
You will need this information to send emails to the account

-  Make sure that you have Git configured and have this repository cloned
-  Additonally, make sure you have some sort of live server addition to the code editor for VSCode I use Live Server
-  Before you go live, we need to run the backend
    - to do so  just run the files_backend.py file
 - Once backend is running, you can go live 





