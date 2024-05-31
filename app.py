from flask import Flask, request, jsonify
import logging
import redis
import json
from loguru import logger
import requests
from datetime import datetime
import uuid

app = Flask(__name__)
logger.add("app.log", rotation="500 MB", level="INFO")

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def is_valid_plate_num(plate_num):
    """
    Checks if the plate number is valid (alphanumeric, non-empty, and within length limit).
    """
    return plate_num and len(plate_num) <= 20 and plate_num.isalnum()

def is_valid_car_logo(car_logo):
    """
    Checks if the car logo string is valid (alphanumeric, non-empty, and within length limit).
    """
    return car_logo and len(car_logo) <= 50 and car_logo.isalnum()

def sanitize_input(input_str):
    """
    Sanitizes input string to prevent XSS (Cross-Site Scripting) attacks.
    Replaces '<' with '&lt;' and '>' with '&gt;'.
    """
    return input_str.replace('<', '&lt;').replace('>', '&gt;') if input_str else None

@app.errorhandler(Exception)
def handle_error(e):
    """
    Handles exceptions gracefully.
    Logs the error message and returns a JSON response with error details.
    """
    logger.error(f"An error occurred: {str(e)}")
    return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500

@app.route('/lpr', methods=['POST'])
def process_lpr():
    try:
        plate_num = request.form.get('plate_num')
        car_logo = request.form.get('car_logo')
        confidence_str = request.form.get('confidence')
        cam_ip = request.form.get('cam_ip')
        vehicle_brand = request.form.get('car_logo')
        vehicle_color = request.form.get('car_color')

        # Validate plate number
        if not is_valid_plate_num(plate_num):
            raise ValueError("Invalid or missing plate number")

        # Validate car logo
        if not is_valid_car_logo(car_logo):
            raise ValueError("Invalid or missing car logo")

        # Validate and convert confidence (optional)
        confidence = float(confidence_str) if confidence_str and confidence_str.replace('.', '', 1).isdigit() else None

        # Log sanitized data for security
        logger.info(f"Received license plate number: {sanitize_input(plate_num)}")
        logger.info(f"Detected car logo: {sanitize_input(car_logo)}")
        logger.info(f"Confidence level: {confidence}")
        logger.info(f"Camera IP: {sanitize_input(cam_ip)}")
        logger.info(f"Vehicle Brand: {sanitize_input(vehicle_brand)}")
        logger.info(f"Vehicle Color: {sanitize_input(vehicle_color)}")

        # Prepare data for Redis in a secure and efficient way
        lpr_data = {
            'plate_num': sanitize_input(plate_num),
            'car_logo': sanitize_input(car_logo),
            'confidence': confidence,
            'cam_ip': sanitize_input(cam_ip),
            'vehicle_brand': sanitize_input(vehicle_brand),
            'vehicle_color': sanitize_input(vehicle_color)
        }
        lpr_data_str = json.dumps(lpr_data)

        # Publish data to Redis channel
        redis_client.publish('lpr_data', lpr_data_str)

        # Prepare data for external endpoint
        external_data = {
            "eventTimestamp": datetime.utcnow().isoformat() + "Z",
            "cameraIp": cam_ip,
            "vehiclePlateNumber": plate_num,
            "imageUrl": f"snapshot/dummy_{plate_num}_{datetime.now().strftime('%Y%m%d')}.jpg",
            "systemName": "DAHUA",
            "vehicleType": "CAR",
            "vehicleBrand": vehicle_brand,
            "vehicleColor": vehicle_color,
            "vehiclePlateColor": "Black",
            "confidence": confidence,
            "executionTime": 100,
            "coordinates": "0,0,0,0",
            "vehicleModel": "dummy",
            "engineLprExternalId": str(uuid.uuid4()),
            "oldEngineLprExternalId": None
        }

        # Send data to external endpoint
        external_endpoint = "http://110.0.100.80:8888/engine-lpr/v1/trigger/lpr/local/async"
        response = requests.post(external_endpoint, json=external_data, headers={"Content-Type": "application/json"})
        if response.status_code != 200:
            raise ValueError(f"Failed to send data to external endpoint: {response.text}")

        return jsonify({'status': 'success'}), 200

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({'status': 'error', 'message': str(ve)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)