from flask import Flask, Response, jsonify
from influxdb_client import InfluxDBClient
import csv
from io import StringIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# InfluxDB connection details
INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "u4qevo7QbZxbknS9-lpGklPOxMPg5pH7PPzRqFT7VxdPzCnLxqW0Y_h4k7oTyIiOr0cbMJ9GlcH_5JOK7O4z8Q=="
INFLUXDB_ORG = "Dev team"
INFLUXDB_BUCKET = "demo_bucket"

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
        |> filter(fn: (r) => r["_measurement"] == "Pilot")
        |> filter(fn: (r) => r["_field"] == "temperature")
        |> last()
        '''

        result = query_api.query(org=INFLUXDB_ORG, query=query)

        alerts = []
        TEMPERATURE_THRESHOLD = 0.5

        for table in result:
            for record in table.records:
                if record["_field"] == "temperature" and record["_value"] < TEMPERATURE_THRESHOLD:
                    alerts.append(f"Temperature is below threshold: {record['_value']}")

        if not alerts:
            alerts.append("✅ All systems are normal.")

        return jsonify({"alerts": alerts})

    except Exception as e:
        return jsonify({"alerts": [f"Error fetching data: {str(e)}"]}), 500

if __name__ == '__main__':
    app.run(debug=True)
