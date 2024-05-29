from flask import Flask, request, jsonify
import logging
import redis
import json
from loguru import logger

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

        # Prepare data for Redis in a secure and efficient way
        lpr_data = {
            'plate_num': sanitize_input(plate_num),
            'car_logo': sanitize_input(car_logo),
            'confidence': confidence
        }
        lpr_data_str = json.dumps(lpr_data)

        # Publish data to Redis channel
        redis_client.publish('lpr_data', lpr_data_str)

        return jsonify({'status': 'success'}), 200

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({'status': 'error', 'message': str(ve)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
