import csv
#pip install flask
from flask import Flask, Response, jsonify, send_file
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
app = Flask(__name__)
CORS(app)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import time
import logging

sent_alerts = set()
# InfluxDB connection details
INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "u4qevo7QbZxbknS9-lpGklPOxMPg5pH7PPzRqFT7VxdPzCnLxqW0Y_h4k7oTyIiOr0cbMJ9GlcH_5JOK7O4z8Q=="
INFLUXDB_ORG = "Dev team"
INFLUXDB_BUCKET = "demo_2"

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
    from(bucket: "{INFLUXDB_BUCKET}")
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

@app.route('/get-alerts', methods=['GET'])
def get_alerts():
    try:

        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
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

@app.route('/generate-report', methods=['GET'])
def generate_report():
    """
    Generate a PDF report with data formatted as a table.
    """
    try:
        # Fetch data from InfluxDB
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -1h)
        '''

        data = query_api.query(org=INFLUXDB_ORG, query=query)

        # Prepare data for the table
        table_data = [["Time", "Value", "Field", "Measurement"]]  # Table header
        for table in data:
            for record in table.records:
                table_data.append([
                    record.get_time(),
                    record.get_value(),
                    record.get_field(),
                    record.get_measurement()
                ])

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
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Table body background
            ('GRID', (0, 0), (-1, -1), 1, colors.black)  # Grid lines
        ]))

        # Build the PDF
        pdf.build([table])
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="hydrant_report.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)