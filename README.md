# 📌 Linq Data Engineering Take-Home Test

## Problem Statement
Imagine you're working in an event-driven system where messages are constantly flowing through an event bus. A worker service processes these events in real time, but due to an error, **some events were either missed or processed incorrectly**.

Since we **don’t have a traditional database** to store historical event data, we need a way to **recalculate and recover the correct state** efficiently.

---

## ✅ Solution Approach
Given the lack of a database, our approach needs to:
- Reprocess or reconstruct missing/corrupt events.
- Ensure accuracy and consistency while replaying events.
- Scale efficiently to handle **millions of events per hour**.
- Minimize storage dependency.

### 🔍 **Step 1: Identifying Missing or Incorrect Events**
To detect events that need reprocessing, we can use:
- **Event logs (if available):** Checking system logs or error reports for anomalies.
- **Gaps in event sequences:** Analyzing timestamps to spot missing events.
- **Downstream inconsistencies:** If aggregate metrics don’t add up, it’s a sign something is off.
- **ML-based detection:** Using a model to flag unusual patterns in event data.
- **Status checks:** If an event isn’t marked as `processed`, we assume it needs to be replayed.

### 🔄 **Step 2: Replaying and Recomputing Events**
Depending on the setup, we can use different recovery strategies:

#### ✅ **Kafka-Based Event Replay (Best for Real-Time Systems)**
- If the system uses **Kafka**, we can rewind and reprocess past messages.
- Kafka stores past events for a configurable period, allowing us to fetch and replay messages.
- **Approach:**
  - Read old messages from Kafka.
  - Identify missing or incorrect events.
  - Reproduce and send them back into the stream.

#### ✅ **State Reconstruction from Derived Data**
- If we don’t have access to past event logs, we can infer missing states using aggregated results.
- Example: If a financial system only stores total balances but not individual transactions, we can estimate the missing transactions based on snapshots.

#### ✅ **In-Memory Processing for Quick Recovery**
- For smaller datasets, **in-memory caching (e.g., Redis)** can temporarily hold and replay events.

---

## 🚦 Error Handling & Ensuring Consistency
To keep things running smoothly:
- **Retries:** We attempt up to **3 retries** before marking an event as permanently failed.
- **Dead Letter Queue (DLQ):** Events that still fail after retries are stored in `dead_letter_queue` for manual inspection.
- **Scalability:**
  - **Kafka partitions** distribute event replay across multiple workers.
  - For large-scale recovery, **Apache Spark** could be used for batch reprocessing instead of real-time replay.

---

## 🛠️ **Implementation**
We assume a Kafka-based system and implement a Python script that:
- Reads past events.
- Detects and replays missing or incorrect messages.
- Uses retries and a DLQ to handle failures.

### **📋 Key Assumptions**
1. The system is built on Kafka.
2. Events have a `status` field (`processed` or `error`).
3. Some errors (e.g., network issues) can be fixed by retrying.
4. Events failing **3 times** are sent to a **Dead Letter Queue (DLQ)**.
5. Kafka’s retention period lets us access past messages.

### **📌 Python Code**
```python
from kafka import KafkaConsumer, KafkaProducer
import json
import time

# Kafka Config
KAFKA_BROKER = "localhost:9092"
INPUT_TOPIC = "event_stream"
REPLAY_TOPIC = "replay_events"
DLQ_TOPIC = "dead_letter_queue"

# Kafka Consumer
consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Retry Tracking
MAX_RETRIES = 3
retry_counts = {}

# Process each event
def process_event(event):
    event_id = event.get("id", "unknown")

    if event.get("status") != "processed":
        if retry_counts.get(event_id, 0) < MAX_RETRIES:
            retry_counts[event_id] = retry_counts.get(event_id, 0) + 1
            replay_event(event)
        else:
            send_to_dlq(event)

# Replay event
def replay_event(event):
    try:
        corrected_event = event.copy()
        corrected_event["status"] = "reprocessed"
        producer.send(REPLAY_TOPIC, corrected_event)
        print(f"Replayed Event: {corrected_event}")
    except Exception as e:
        print(f"Failed to replay event: {event}, sending to DLQ")
        send_to_dlq(event)

# Handle events that fail too many times
def send_to_dlq(event):
    producer.send(DLQ_TOPIC, event)
    print(f"Event moved to Dead Letter Queue: {event}")

# Read messages from Kafka
for message in consumer:
    process_event(message.value)
    consumer.commit()
    time.sleep(0.1)  # Prevent overwhelming Kafka
```

---

## ⚖️ **Trade-offs & Limitations**
### **Trade-offs**
- **Kafka Dependency:** This assumes we have access to Kafka logs. Without it, alternative recovery methods would be needed.
- **Limited Historical Recovery:** Kafka only retains messages for a set period, so older missing events might not be recoverable.

### 🛠️ How the Approach Would Change with More Tools  

Depending on the available infrastructure, additional tools can enhance or simplify the process of detecting and replaying missing events. Here’s how different tools could improve the solution:  

| **Tool**  | **How It Helps** |
|----------|---------------------------|
| **Database (SQL or NoSQL)** | If a traditional database were available, we could store a **historical record of events**, making it easier to query and reconstruct missing data. This would enable **point-in-time recovery**, allowing us to identify and replay only the missing events. Additionally, indexing event IDs and timestamps would improve lookup efficiency. |
| **Event Logs** | If structured logs of past events exist (e.g., application logs, audit logs), we could analyze them to identify patterns of missing or incorrectly processed messages. By scanning logs, we might also find **error messages or stack traces** related to failed events, helping diagnose the root cause. These logs could then be used to generate replayable events. |
| **Data Lake (S3, HDFS, BigQuery, Snowflake, etc.)** | A data lake could store raw event data **for long-term retention**, enabling batch reprocessing when needed. This would be useful for **historical backfill operations**, where we need to recover large amounts of lost or corrupted data beyond Kafka’s retention period. With tools like **Apache Spark or Presto**, we could efficiently analyze and extract missing event information. |

By leveraging these tools, we could enhance the robustness of our event replay system, reduce reliance on real-time Kafka retention, and provide a more **scalable and resilient** approach to event recovery. 🚀  


**Alternative Persistence Mechanisms**
- **Kafka Compacted Topics:** Retain a deduplicated version of key events, reducing storage needs while allowing replays.

---

## 📊 **Scalability Considerations**
For high-volume systems, we can optimize performance by:
- **Using Kafka partitions** to distribute event reprocessing across multiple workers.
- **Batch reprocessing** with **Apache Spark**, rather than handling events one by one.
- **Using Redis or RocksDB** for state recovery instead of depending on Kafka’s retention period.

---

## 🎯 **Final Thoughts**
This approach provides a **scalable and efficient** way to recover from missing or incorrect events in an event-driven system. The key steps are:
1. **Detect** missing/corrupt events.
2. **Reprocess** them using Kafka replay or inferred data.
3. **Retry up to 3 times** before moving to the Dead Letter Queue.
4. **Ensure scalability** to handle large-scale event replay.

By leveraging Kafka's built-in capabilities and keeping the system flexible, we can maintain **data consistency and correctness** without relying on traditional storage. 🚀

