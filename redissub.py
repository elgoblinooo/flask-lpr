import redis
import json
import datetime  # Import datetime module for timestamp

def process_message(message):
    try:
        # Get the current timestamp
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Parse the JSON message
        data = json.loads(message['data'])

        # Extract data fields
        plate_num = data.get('plate_num')
        car_logo = data.get('car_logo')

        # Log the received data with timestamp
        if plate_num and car_logo:
            print(f"Redis LPR Received {current_time} - Plate Number: {plate_num}, Car Logo: {car_logo}")
        else:
            print(f"Received incomplete LPR data at {current_time}")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON message: {e}")
    except Exception as e:
        print(f"Error processing message: {e}")

def main():
    # Initialize Redis connection
    redis_client = redis.Redis(host='localhost', port=6379, db=0)

    # Subscribe to the 'lpr_data' channel
    pubsub = redis_client.pubsub()
    pubsub.subscribe('lpr_data')
    print("Subscribed to lpr_data channel. Waiting for messages...")

    # Start listening for messages
    for message in pubsub.listen():
        if message['type'] == 'message':
            process_message(message)

if __name__ == '__main__':
    main()
