import requests
import json
import time
from collections import defaultdict, deque
from kafka import KafkaConsumer, KafkaProducer

WINDOW_SIZE = 300        # 5 минут
PUBLISH_INTERVAL = 10    # отправка каждые 10 секунд
import requests
import json
import time
from collections import defaultdict, deque
from kafka import KafkaConsumer, KafkaProducer

WINDOW_SIZE = 300        # 5 минут
PUBLISH_INTERVAL = 10    # публикация каждые 10 секунд

CLICKHOUSE_URL = "http://localhost:8123"

# Kafka consumer (читаем клики)
consumer = KafkaConsumer(
    "clicks",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=True,
)

# Kafka producer (отправляем агрегаты)
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

# Храним события в памяти
events = deque()

print(f"Окно: {WINDOW_SIZE} сек, публикация каждые {PUBLISH_INTERVAL} сек")

last_publish = time.time()

while True:
    # Читаем новые события
    for message_batch in consumer.poll(timeout_ms=1000).values():
        for record in message_batch:
            event = record.value
            events.append((event["timestamp"] / 1000, event["product_id"]))

    current_time = time.time()

    # Удаляем устаревшие события (старше 5 минут)
    while events and current_time - events[0][0] > WINDOW_SIZE:
        events.popleft()

    # Каждые 10 секунд публикуем агрегаты
    if current_time - last_publish >= PUBLISH_INTERVAL:

        counts = defaultdict(int)

        for _, product_id in events:
            counts[product_id] += 1

        for product_id, count in counts.items():

            result = {
                "product_id": product_id,
                "count": count,
                "timestamp": int(current_time * 1000)
            }

            # Отправляем в Kafka aggregated_clicks
            producer.send("aggregated_clicks", value=result)

            # Пишем в ClickHouse
            query = f"""
            INSERT INTO analytics.product_clicks (product_id, count, timestamp)
            VALUES ({product_id}, {count}, {int(current_time * 1000)})
            """

            try:
                requests.post(CLICKHOUSE_URL, data=query)
            except Exception as e:
                print("Ошибка записи в ClickHouse:", e)

            print(f"Агрегат: product_id={product_id}, count={count}")

        last_publish = current_time
consumer = KafkaConsumer(
    "clicks",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=True,
)

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

# Храним клики как (timestamp, product_id)
events = deque()

print(f"Окно: {WINDOW_SIZE} сек, публикация каждые {PUBLISH_INTERVAL} сек")

last_publish = time.time()

while True:
    # Читаем новые сообщения
    for message in consumer.poll(timeout_ms=1000).values():
        for record in message:
            event = record.value
            events.append((event["timestamp"] / 1000, event["product_id"]))

    current_time = time.time()

    # Удаляем устаревшие события
    while events and current_time - events[0][0] > WINDOW_SIZE:
        events.popleft()

    # Каждые 10 секунд публикуем агрегаты
    if current_time - last_publish >= PUBLISH_INTERVAL:
        counts = defaultdict(int)
        for _, product_id in events:
            counts[product_id] += 1

        for product_id, count in counts.items():
            result = {
                "product_id": product_id,
                "count": count,
                "timestamp": int(current_time * 1000)
            }
            producer.send("aggregated_clicks", value=result)
            print(f"Агрегат: product_id={product_id}, count={count}")

        last_publish = current_time
