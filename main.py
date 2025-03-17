from kafka import KafkaConsumer, KafkaProducer
import json
import time

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"
INPUT_TOPIC = "event_stream"  # Topic from which events are consumed
RETRY_TOPIC = "retry_events"  # Topic to send events for retrying
DLQ_TOPIC = "dead_letter_queue"  # Dead Letter Queue for permanently failed events

# Initialize Kafka Consumer to listen to the input topic
consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset='earliest',  # Start reading from the earliest available message
    enable_auto_commit=False,  # Manually committing offsets for better control
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))  # Deserialize JSON messages
)

# Initialize Kafka Producer to send messages to retry and DLQ topics
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda x: json.dumps(x).encode('utf-8')  # Serialize messages to JSON format
)

# Maximum number of retry attempts before sending to DLQ
MAX_RETRIES = 3
retry_counts = {}  # Dictionary to track retry attempts per event

def process_event(event):
    """
    Process incoming events. If an event has not been successfully processed,
    it will be retried up to MAX_RETRIES times. If it still fails, it will be
    sent to the Dead Letter Queue (DLQ).
    """
    event_id = event.get("id", "unknown")  # Extract event ID or assign "unknown" if missing

    if event.get("status") != "processed":  # Check if the event was not processed successfully
        if retry_counts.get(event_id, 0) < MAX_RETRIES:
            # Increment retry count and send event to the retry topic
            retry_counts[event_id] = retry_counts.get(event_id, 0) + 1
            producer.send(RETRY_TOPIC, event)
            print(f"Retrying Event (Attempt {retry_counts[event_id]}): {event}")
        else:
            # If max retries are exceeded, send event to Dead Letter Queue
            send_to_dlq(event)

def send_to_dlq(event):
    """
    Send the event to the Dead Letter Queue (DLQ) after exhausting all retries.
    """
    producer.send(DLQ_TOPIC, event)
    print(f"Event moved to Dead Letter Queue: {event}")

# Consume messages from Kafka and process them
for message in consumer:
    process_event(message.value)  # Process the event message
    consumer.commit()  # Commit offset after processing to prevent reprocessing the same message
    time.sleep(0.1)  # Add a small delay to prevent overwhelming Kafka with requests
