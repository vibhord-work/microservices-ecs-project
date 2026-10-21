from flask import Flask, jsonify
import socket

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify(status="healthy", service="department-service")

@app.get("/departments")
def departments():
    return jsonify(
        service="department-service",
        version="1.0",
        hostname=socket.gethostname(),
        departments=[
            {"id": 1, "name": "DevOps"},
            {"id": 2, "name": "Engineering"}
        ]
    )
