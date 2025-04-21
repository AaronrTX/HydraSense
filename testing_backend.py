import csv
from flask import Flask, Response, jsonify, send_file, request
from influxdb_client import InfluxDBClient, Point
from flask_cors import CORS
from io import BytesIO, StringIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime, timezone
import pytz # type: ignore
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import logging

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5500"])

startup_time = datetime.now(timezone.utc)
sent_alerts = set()

INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "u4qevo7QbZxbknS9-lpGklPOxMPg5pH7PPzRqFT7VxdPzCnLxqW0Y_h4k7oTyIiOr0cbMJ9GlcH_5JOK7O4z8Q=="
INFLUXDB_ORG = "Dev team"
FLOW_BUCKET = "test_data_bucket"
FLOW_ALERT = "test_filter_bucket"
PRESSURE_BUCKET = "demo_2"
PRESSURE_ALERT = "alerts_filter1"

utc = pytz.utc
central = pytz.timezone('America/Chicago')

def send_email(subject, body, alert_key):
    sender_email = "hydrasense2025@gmail.com"
    sender_password = "fycw zltn nror aycq"
    recipient_email = "hydrasense2025@gmail.com"

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


def reset_sent_alerts():
    while True:
        time.sleep(900)
        sent_alerts.clear()
        print("* Sent alerts have been reset.")

threading.Thread(target=reset_sent_alerts, daemon=True).start()

@app.route('/download-data', methods=['GET'])
def download_data():
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()
    query = f'''
    from(bucket: "{FLOW_BUCKET}")
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

@app.route('/get-alerts', methods=['GET'])
def get_alerts():
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()
        all_alerts = []

        def is_alert_cleared(alert_key,bucket):
            query = f'''
            from(bucket: "{bucket}")
            |> range(start: -15m)
            |> filter(fn: (r) => r["alert_key"] == "{alert_key}")
            |> filter(fn: (r) => r["cleared"] == "true")
            '''
            result = query_api.query(org=INFLUXDB_ORG, query=query)
            return any(record for table in result for record in table.records)

        flow_query = f'''
        from(bucket: "{FLOW_ALERT}")
        |> range(start: -15m)
        |> filter(fn: (r) => r["_field"] == "flowValue")
        '''

        flow_result = query_api.query(org=INFLUXDB_ORG, query=flow_query)

        for table in flow_result:
            for record in table.records:
                flow_value = record.get_value()
                alert_time = record.get_time()

                if alert_time <= startup_time:
                    #print(f"[SKIPPED] Old alert from {alert_time}, startup was {startup_time}")
                    continue

                dt_central = alert_time.astimezone(central)
                formatted_time = dt_central.strftime("%Y-%m-%d %I:%M:%S %p")

                alert_msg = f"Flow Alert: Value = {flow_value}. At the time: {formatted_time}"
                alert_key = f"flow_alert|{formatted_time}|{flow_value}"

                if not is_alert_cleared(alert_key, FLOW_ALERT):
                    if alert_key not in sent_alerts:
                        send_email("Flow Alert", alert_msg, alert_key)
                    all_alerts.append({"message": alert_msg, "key": alert_key})

        pressure_query = f'''
        from(bucket: "{PRESSURE_ALERT}")
        |> range(start: -15m)
        |> filter(fn: (r) => r["_field"] == "pressureValue")
        '''

        pressure_result = query_api.query(org=INFLUXDB_ORG, query=pressure_query)

        for table in pressure_result:
            for record in table.records:
                pressure_value = record.get_value()
                alert_time = record.get_time()

                if alert_time <= startup_time:
                    #print(f"[SKIPPED] Old alert from {alert_time}, startup was {startup_time}")
                    continue

                dt_central = alert_time.astimezone(central)
                formatted_time = dt_central.strftime("%Y-%m-%d %I:%M:%S %p")

                alert_msg = f"Pressure Alert: Value = {pressure_value}. At the time: {formatted_time}"
                alert_key = f"pressure_alert|{formatted_time}|{pressure_value}"

                if not is_alert_cleared(alert_key, PRESSURE_ALERT):
                    if alert_key not in sent_alerts:
                        send_email("Pressure Alert", alert_msg, alert_key)
                    all_alerts.append({"message": alert_msg, "key": alert_key})

        if not all_alerts:
            all_alerts.append("✅ All systems are normal.")

        return jsonify({"alerts": all_alerts})

    except Exception as e:
        logging.error(f"[ERROR in get-alerts] {e}")
        return jsonify({"alerts": [f"Error fetching data: {str(e)}"]}), 500

@app.route('/clear-alert', methods=['POST', 'OPTIONS'])
def clear_alert():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        alert_key = request.json.get('alert_key')
        if not alert_key:
            return jsonify({"error": "alert_key is required"}), 400

        print(f"Received alert key: {alert_key}")

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
        print(f"Error clearing alert: {str(e)}")
        return jsonify({"error": f"Error clearing alert: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
