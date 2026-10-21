from flask import Flask, jsonify
import socket

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify(status="healthy", service="employee-service")

@app.get("/employees")
def employees():
    return jsonify(
        service="employee-service",
        version="1.0",
        hostname=socket.gethostname(),
        employees=[
            {"id": 1, "name": "Vibhor Dewangan", "department_id": 1},
            {"id": 2, "name": "Rahul Sharma", "department_id": 2}
        ]
    )
