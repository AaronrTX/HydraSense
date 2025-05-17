import csv
#pip install flask
from flask import Flask, Response, jsonify, send_file, request
#pip3 install influxdb-client
from influxdb_client import InfluxDBClient
#pip install Flask-Cors
from flask_cors import CORS
from io import BytesIO, StringIO
#pip install reportlab
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from influxdb_client import Point
#pip install DateTime
from datetime import datetime, timezone

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import logging

#pip install pytz
import pytz # type: ignore

# We used vs code live server to test the backend, so we need to allow CORS for it to work
# You can change the origin to your own frontend URL
app = Flask(__name__)
CORS(app, origins = ["http://127.0.0.1:5500"])

startup_time = datetime.now(timezone.utc)
sent_alerts = set()

# InfluxDB connection details
#USE YOUR OWN INFLUXDB URL, TOKEN, ORG, BUCKETS
# You can create a new bucket in your InfluxDB Cloud account and use it for testing
INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "u4qevo7QbZxbknS9-lpGklPOxMPg5pH7PPzRqFT7VxdPzCnLxqW0Y_h4k7oTyIiOr0cbMJ9GlcH_5JOK7O4z8Q=="
INFLUXDB_ORG = "Dev team"
VALVE_BUCKET = "reed_switch" #reads valve status

PRESSURE_BUCKET = "pressure_sensor" #pressure
PRESSURE_ALERT = "alerts_filter1" #filters pressure
FLOW_BUCKET = "flow_sensor" #flow sensor, for now its temperature
FLOW_ALERT = "alerts_filter2"#alerts for flow sensor
VALVE_BUCKET = "reed_switch" #reads valve status"""


#timezone declaration
utc = pytz.utc
central = pytz.timezone('America/Chicago')
"""==========================================================================================================
==========================================================================================================
Email alert configuration
==========================================================================================================
=========================================================================================================="""
def send_email(subject, body, alert_key):
    sender_email = "USE YOUR OWN EMAIL, PREFERABLY GMAIL"  
    sender_password = "CREATE AN APP PASSWORD FOR YOUR GMAIL ACCOUNT"    
    recipient_email = "USE YOUR OWN EMAIL, PREFERABLY GMAIL"  

    

    #check if alert email has been sent
    if alert_key in sent_alerts:
        print(f"Alert '{alert_key}' already sent. Skipping")
        return
    
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.set_debuglevel(1)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()

        sent_alerts.add(alert_key)
        time.sleep(10)

    except Exception as e:
        logging.error(f"Email error: {e}")

# Function to reset sent_alerts every x seconds (configure on your own)
def reset_sent_alerts():
    while True:
        time.sleep(900)  # 86400 seconds = 24 hours | 120 seconds = 2 minutes | 900 = 15 minutes
        sent_alerts.clear()
        print("* Sent alerts have been reset.") #the check mark gave some problem

# Start the reset function in a background thread
threading.Thread(target=reset_sent_alerts, daemon=True).start()


"""==========================================================================================================
==========================================================================================================
Download the reports
==========================================================================================================
=========================================================================================================="""
@app.route('/download-data', methods=['GET'])
def download_data():
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    
    query = f'''
    from(bucket: "{PRESSURE_BUCKET}")
    |> range(start: -2d) 
    '''

    data = query_api.query(org=INFLUXDB_ORG, query=query)
    output = StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(["_time", "_value", "_field", "_measurement"])

    for table in data:
        for record in table.records:
            csv_writer.writerow([record.get_time(), record.get_value(), record.get_field(), record.get_measurement()])


    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=sensor_data.csv"}
    )

"""==========================================================================================================
==========================================================================================================
Get alerts
If there's data entry in the alert bucket, get the alert data to be sent
==========================================================================================================
=========================================================================================================="""
@app.route('/get-alerts', methods=['GET']) 
def get_alerts():
    try:

        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        all_alerts = []

        def is_alert_cleared(alert_key, bucket):
            query =  f'''
            from(bucket: "{bucket}")
            |> range(start: -15m)
            |> filter(fn: (r) => r["alert_key"] == "{alert_key}")
            |> filter(fn: (r) => r["cleared"] == "true")
            '''
            result = query_api.query(org=INFLUXDB_ORG, query=query)
            return any(record for table in result for record in table.records)

        pressure_query = f'''
        from(bucket: "{PRESSURE_ALERT}")
        |> range(start: -15m)
        |> filter(fn: (r) => r["_field"] == "pressureValue")
        '''
        pressure_result = query_api.query(org=INFLUXDB_ORG, query=pressure_query)
        for table in pressure_result:
            for record in table.records:
                alert_time = record.get_time()
                pressure_value = record.get_value()
                
                if alert_time <= startup_time:
                    continue

                dt_central = alert_time.astimezone(central)
                formatted_time = dt_central.strftime("%Y-%m-%d %I:%M:%S %p")

                alert_msg = f"Pressure Alert: Value = {pressure_value}. At the time: = {formatted_time}"
                alert_key = f"pressure_alert|{formatted_time}|{pressure_value}"


                if not is_alert_cleared(alert_key, PRESSURE_ALERT):
                    if alert_key not in sent_alerts:
                        send_email("Pressure Alert", alert_msg, alert_key)
                    all_alerts.append({"message": alert_msg, "key":alert_key})
        

        flow_query = f'''
        from(bucket: "{FLOW_ALERT}")
        |> range(start: -15m)
        |> filter(fn: (r) => r["_field"] == "flowValue")
        '''
        flow_result = query_api.query(org=INFLUXDB_ORG, query=flow_query)
        for table in flow_result:
            for record in table.records:
                alert_time = record.get_time()
                flow_value = record.get_value()
                
                if alert_time <= startup_time:
                    continue

                dt_central = alert_time.astimezone(central)
                formatted_time = dt_central.strftime("%Y-%m-%d %I:%M:%S %p")

                alert_msg = f"Flow Alert: Value = {flow_value}. At the time: {formatted_time}"
                alert_key = f"flow_alert|{formatted_time}|{flow_value}"


                if not is_alert_cleared(alert_key, FLOW_ALERT):
                    if alert_key not in sent_alerts:
                        send_email("Flow Alert", alert_msg, alert_key)
                    all_alerts.append({"message": alert_msg, "key":alert_key})

        if not all_alerts:
            all_alerts.append("✅ All systems are normal.")
            


        return jsonify({"alerts": all_alerts})

    except Exception as e:
        logging.error(f"[ERROR in get-alerts] {e}")
        return jsonify({"alerts": [f"Error fetching data: {str(e)}"]}), 500

#CLEAR ALERT point
@app.route('/clear-alert', methods=['POST', 'OPTIONS'])
def clear_alert():
    if request.method == 'OPTIONS':
        return jsonify({}),200
    try:
        alert_key = request.json.get('alert_key')
        if not alert_key:
            return jsonify({"error": "alert_key is required"}), 400
        
        print(f"Received alert key: {alert_key}") #debugg

        parts = alert_key.split("|")
        if len(parts) < 3:
            return jsonify({"error": "invalid alert key format"}), 400
        
        value = parts[2]

        point = Point("cleared_alert")
        point.tag("alert_key", alert_key)
        point.tag("cleared", "true")
        point.field("value", float(value))

        if(parts[0] == "flow_alert"):
            point.measurement("flow_alert")
            bucket = FLOW_ALERT
        else:
            point.measurement("pressure_alert")
            bucket = PRESSURE_ALERT

        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = client.write_api()
        write_api.write(bucket=bucket, org=INFLUXDB_ORG, record=point)

        return jsonify({"message": "Alert cleared"}), 200

    except Exception as e:
        print(f"Error clearing alert: {str(e)}") #debugg
        return jsonify({"error" : f"Error clearing alert: {str(e)}"}), 500
    
"""==========================================================================================================
==========================================================================================================
Generate the reports
==========================================================================================================
=========================================================================================================="""

@app.route('/generate-report', methods=['GET'])
def generate_report():
    """
    Generate a PDF report with database timestamps directly matching values.
    """
    try:
        hydrant_id = request.args.get('hydrant')
        data_type = request.args.get('type', 'pressure')

        if data_type == "flow":
            bucket = FLOW_BUCKET  # demo_bucket
            measurement = "flow_sensor"
            value_field = "flowValue"
        else:
            bucket = PRESSURE_BUCKET  # demo_2
            measurement = "pressure_sensor"
            value_field = "pressureValue"

        print(f"Generating report for: {hydrant_id}, Data Type: {data_type}, Bucket: {bucket}")

        # Fetch data from InfluxDB
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{bucket}")
        |> range(start: -2d)
        |> filter(fn: (r) => r["_measurement"] == "{measurement}")
        |> pivot (rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> keep(columns: ["_time", "{value_field}"])
        |>rename(columns:{{"{value_field}": "Value"}})
        '''

        print("Executing Query:", query)  # Debugging

        data = query_api.query(org=INFLUXDB_ORG, query=query)

        # Prepare table headers
        table_data = [["Date & Time", "Value", "Field"]]  # No "Measurement"
        record_count = 0

        for table in data:
            for record in table.records:

                timestamp = record.get_time()

                # Ensure timestamp is a datetime object before formatting
                if isinstance(timestamp, str):  # Convert string to datetime if needed
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
                    timestamp = utc.localize(timestamp)
            
                central_time = timestamp.astimezone(central)

                # Format time in 12-hour format
                formatted_time = central_time.strftime("%Y-%m-%d %I:%M:%S %p")

                # Append data to the table
                try:
                    formatted_value = round(float(record["Value"]), 2) 
                    table_data.append([
                    formatted_time,
                    formatted_value,
                    "PSI" if data_type == "pressure" else "GPM"])
                    record_count += 1
                
                except KeyError as e:
                    print(f"KeyError: {e} in record: {record}")  # Debugging
                except ValueError as e:
                    print(f"ValueError: {e} in record: {record}")  # Debugging

        print(f"Records retrieved: {record_count}")

        if record_count == 0:
            return jsonify({"error": "No data found for the selected parameters"}), 404

        # Create a PDF buffer
        pdf_buffer = BytesIO()
        pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)

        # Define the table and styles
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),  # Light grey table background
            ('GRID', (0, 0), (-1, -1), 1, colors.black)  # Grid lines
        ]))

        # Build the PDF
        pdf.build([table])
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"hydrant_{hydrant_id}_{data_type}_report.pdf"
        )
    except Exception as e:
        print("Error Generating Report:", str(e))  # Debugging
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500
    
"""==========================================================================================================
==========================================================================================================
Get the valve status
==========================================================================================================
=========================================================================================================="""    

@app.route('/valve-status', methods=['GET'])
def get_valve_status():
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "reed_switch")
        |> range(start: -10m)
        |> filter(fn: (r) => r["_measurement"] == "valve")
        |> filter(fn: (r) => r["_field"] == "value")
        |> last()
        '''

        result = query_api.query(org=INFLUXDB_ORG, query=query)

        if not result:
            return jsonify({"error": "No data found in reed_switch bucket"}), 404

        for table in result:
            for record in table.records:
                raw_value = record.get_value()  # Get the raw value from InfluxDB

                try:
                    value = int(raw_value)  # Convert to integer
                    if value not in [0, 1]:  
                        raise ValueError("Invalid value received from InfluxDB")
                except ValueError:
                    return jsonify({"error": f"Invalid valve status value: {raw_value}"}), 400

                # 🔄 Determine valve status
                valve_status = "CLOSED" if value == 1 else "OPEN"

                # ✅ Return JSON response
                return jsonify({"value": value, "status": valve_status})

        return jsonify({"error": "No data found"}), 404

    except Exception as e:
        return jsonify({"error": f"Error retrieving valve status: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)