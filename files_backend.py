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
from datetime import datetime
import pytz #this will put the timestamp into CT (pip install pytz)
app = Flask(__name__)
CORS(app)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import logging

PRESSURE_THRESH = 10
FLOW_THRESH = 5

sent_alerts = set()
# InfluxDB connection details
INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "u4qevo7QbZxbknS9-lpGklPOxMPg5pH7PPzRqFT7VxdPzCnLxqW0Y_h4k7oTyIiOr0cbMJ9GlcH_5JOK7O4z8Q=="
INFLUXDB_ORG = "Dev team"
PRESSURE_BUCKET = "demo_2" #pressure
FLOW_BUCKET = "demo_bucket" #flow 
PRESSURE_ALERTS_BUCKET = "alerts_filter2" #filters pressure
FLOW_ALERTS_BUCKET = "alerts_filter1" #filters flow
VALVE_BUCKET = "reed_switch" #reads valve status

#time zone declaration
utc = pytz.utc
central = pytz.timezone('America/Chicago')


# Email alert configuration
def send_email(subject, body, alert_key):
    sender_email = "hydrasense2025@gmail.com"  
    sender_password = "fycw zltn nror aycq"    
    recipient_email = "hydrasense2025@gmail.com"  

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    #check if alert email has been sent
    if alert_key in sent_alerts:
        print(f"Alert '{alert_key}' already sent. Skipping")
        return
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        sent_alerts.add(alert_key)
        print("Alert email sent successfully!")
    except smtplib.SMTPServerDisconnected as e:
        print(f"Connection unexpectedly closed: {e}")
        logging.error(f"Connection unexpectedly closed: {e}")
    except Exception as e:
        print("Error sending email:", e)
        logging.error(f"An error occurred: {e}")

# To keep track of sent alerts (in-memory)
sent_alerts = set()

# Function to reset sent_alerts every 24 hours
def reset_sent_alerts():
    while True:
        time.sleep(900)  # 86400 seconds = 24 hours | 120 seconds = 2 minutes | 900 = 15 minutes
        sent_alerts.clear()
        print("* Sent alerts have been reset.") #the check mark gave some problem

# Start the reset function in a background thread
reset_thread = threading.Thread(target=reset_sent_alerts, daemon=True)
reset_thread.start()



@app.route('/download-data', methods=['GET'])
def download_data():
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    
    query = f'''
    from(bucket: "{PRESSURE_BUCKET}")
    |> range(start: -1h)
    '''

    data = query_api.query(org=INFLUXDB_ORG, query=query)

    output = StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(["_time", "_value", "_field", "_measurement"])

    for table in data:
        for record in table.records:
            csv_writer.writerow([record.get_time(), record.get_value(), record.get_field(), record.get_measurement()])

    csv_content = output.getvalue()
    output.close()

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=sensor_data.csv"}
    )

"""@app.route('/get-alerts', methods=['GET']) 
def get_alerts():
    try:

        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{PRESSURE_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["_measurement"] == "Pilot2")
        |> filter(fn: (r) => r["_field"] == "pressure")
        |> last()
        '''

        result = query_api.query(org=INFLUXDB_ORG, query=query)

        alerts = []
        PRESSURE_THRESHOLD = 0.109

        for table in result:
            for record in table.records:
                alert_id = f"{record.get_time()}-{record.get_value()}"
                if record["_field"] == "pressure" and record["_value"] < PRESSURE_THRESHOLD:
                    #alerts.append(f"Temperature is below threshold: {record['_value']}")
                    alert_msg = f"Pressure is below threshold: {record['_value']}"
                    alerts.append(alert_msg)
                    # Send alert email
                    #send_email("Temperature Alert", alert_msg)
                    #alert key
                    alert_key = f"pressure_low_{record.get_time()}_{record.get_value}"
                    if alert_id not in sent_alerts:
                        send_email("Pressure Alert", alert_msg, alert_key)
                        #sent_alerts.add(alert_id)  # Mark alert as sent


        if not alerts:
            alerts.append("✅ All systems are normal.")
            #send_email("Temperature Alert", "Let's see if this work or not.")


        return jsonify({"alerts": alerts})

    except Exception as e:
        return jsonify({"alerts": [f"Error fetching data: {str(e)}"]}), 500
"""
""""
#Function to filter data and put into another bucket
def filter_and_store(PRESSURE_THRESH):
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        write_api = client.write_api()

        query = f'''
        from(bucket: "{PRESSURE_BUCKET}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["_measurement"] == "Pilot2")
        |> filter(fn: (r) => r["_field"] == "pressure")
        '''

        result = query_api.query(org=INFLUXDB_ORG, query=query)

        for table in result:
            for record in table.records:
                pressure_val = record.get_value()
                timestamp = record.get_time()

                if pressure_val < PRESSURE_THRESH:
                    print(f"Pressure below threshold : {pressure_val}. Storing in {PRESSURE_ALERTS_BUCKET}")

                    point = (
                        Point("Pilot2")
                        .field("pressure", pressure_val)
                        .time(timestamp)
                    )

                    write_api.write(bucket=PRESSURE_ALERTS_BUCKET, org=INFLUXDB_ORG, record=point)
        print("Filtering Complete")

    except Exception as e:
        print(f"Error Filtering : {str(e)}")

def run_peirodic(interval=60, threshold=PRESSURE_THRESH):
    while True:
        print("Running filtering")
        filter_and_store(threshold)
        time.sleep(interval)

filter_thread = threading.Thread(target=run_peirodic, args=(60,PRESSURE_THRESH), daemon=True) 
filter_thread.start()

@app.route('/run-filter', methods=['GET'])
def run_filter():

    filter_and_store()
    return jsonify({"message": "Filtering process triggered"})
"""
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
            measurement = "Pilot"
        else:
            bucket = PRESSURE_BUCKET  # demo_2
            measurement = "Pilot2"

        print(f"Generating report for: {hydrant_id}, Data Type: {data_type}, Bucket: {bucket}")

        # Fetch data from InfluxDB
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{bucket}")
        |> range(start: -1h)
        |> filter(fn: (r) => r["_measurement"] == "{measurement}")
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
                # Format time in 12-hour format
                formatted_time = timestamp.strftime("%Y-%m-%d %I:%M:%S %p")  
                
                central_time = timestamp.astimezone(central)

                # Format time in 12-hour format
                formatted_time = central_time.strftime("%Y-%m-%d %I:%M:%S %p")

                # Use the value directly from the database and round to 2 decimal places
                formatted_value = round(float(record.get_value()), 2)

                # Append data to the table
                table_data.append([
                    formatted_time,
                    formatted_value,
                    record.get_field()
                ])
                record_count += 1

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
    

@app.route('/valve-status', methods=['GET'])
def get_valve_status():
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "reed_switch")
        |> range(start: -1h)
        |> filter(fn: (r) => r["_measurement"] == "Status")
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
                valve_status = "CLOSED" if value == 0 else "OPEN"

                # ✅ Return JSON response
                return jsonify({"value": value, "status": valve_status})

        return jsonify({"error": "No data found"}), 404

    except Exception as e:
        return jsonify({"error": f"Error retrieving valve status: {str(e)}"}), 500



















if __name__ == '__main__':
    app.run(debug=True)