# streaming-pipeline


# **Отчёт по проекту потоковой аналитики**

## **1. Цель проекта**

Основная цель проекта — построить потоковый пайплайн для обработки событий кликов на продукты, с последующей агрегацией и хранением данных для аналитики.

Проект решает следующие задачи:

* Генерация событий кликов (Click Generator)
* Потоковая обработка и агрегация событий (Window Aggregation)
* Хранение агрегированных данных в ClickHouse
* Оркестрация пайплайна с помощью Airflow

---

## **2. Архитектура проекта**

Проект использует микросервисную архитектуру, все сервисы запускаются в контейнерах Docker:

```bash
rais/
├─ airflow/               # Airflow DAGs
│   └─ dags/
│       └─ streaming_pipeline.py
├─ click_generator.py     # Скрипт генерации кликов
├─ window_aggregation.py  # Скрипт агрегации данных
├─ docker-compose.yml     # Определение всех сервисов
```

### **Сервисы Docker Compose**

| Сервис     | Назначение                         | Порт      |
| ---------- | ---------------------------------- | --------- |
| Zookeeper  | Сервис координации Kafka           | 2181      |
| Kafka      | Потоковая платформа                | 9092      |
| Redis      | Кэш для Airflow (если понадобится) | 6379      |
| ClickHouse | Хранилище агрегированных данных    | 9000/8123 |
| Airflow    | Оркестрация DAG’ов                 | 8080      |

---

## **3. Поднятие Docker-стека**

### **3.1 Подготовка**

1. Перейти в корень проекта:

```bash
cd /путь/к/rais
```

2. Проверить наличие Docker и Docker Compose:

```bash
docker --version
docker compose version
```

---

### **3.2 Полная остановка и очистка старых контейнеров**

Если VM перезапускалась, старые контейнеры могли зависнуть. Чтобы начать с чистого состояния:

```bash
docker compose down -v
```

* `-v` удаляет тома, чтобы очистить старые данные Kafka и ClickHouse.

---

### **3.3 Запуск всех сервисов**

```bash
docker compose up -d
```

* Сервисы запускаются в фоне: Kafka, Zookeeper, Redis, ClickHouse, Airflow.
* Подождать 30–40 секунд для полной инициализации всех сервисов.

Проверка статуса контейнеров:

```bash
docker compose ps
```

* Все сервисы должны быть **Up**.

---

### **3.4 Настройка ClickHouse**

1. Заходим в ClickHouse:

```bash
docker compose exec clickhouse clickhouse-client
```

2. Создаём базу и таблицу для агрегатов:

```sql
CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE analytics.product_clicks (
    product_id UInt32,
    count UInt32,
    timestamp UInt64
) ENGINE = MergeTree()
ORDER BY (product_id, timestamp);
```

---

### **3.5 Настройка Kafka**

1. Создаём топики для событий и агрегатов:

```bash
docker compose exec kafka kafka-topics --create --topic clicks --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1

docker compose exec kafka kafka-topics --create --topic aggregation_clicks --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
```

2. Проверяем список топиков:

```bash
docker compose exec kafka kafka-topics --list --bootstrap-server kafka:9092
```

---

### **3.6 Инициализация Airflow**

1. Заходим в контейнер Airflow:

```bash
docker compose exec airflow bash
```

2. Инициализируем базу Airflow:

```bash
airflow db init
```

3. Создаём пользователя для UI:

```bash
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

4. Запуск webserver и scheduler:

```bash
airflow webserver &
airflow scheduler
```

* После этого Airflow UI доступен по адресу: [http://localhost:8080](http://localhost:8080)

---

### **3.7 Проверка работы пайплайна**

1. В Airflow UI включаем DAG `streaming_pipeline`.
2. Триггерим DAG вручную.
3. Проверяем логи задач и данные:

* **ClickHouse:**

```bash
SELECT * FROM analytics.product_clicks;
```

* **Kafka:**

```bash
docker compose exec kafka kafka-console-consumer --topic aggregation_clicks --bootstrap-server kafka:9092 --from-beginning
```

* Данные должны появляться и в Kafka, и в ClickHouse.

---

## **4. Реализация пайплайна**

* `click_generator.py` → создаёт события кликов и пишет в Kafka `clicks`.
* `window_aggregation.py` → агрегирует события и пишет результат в Kafka `aggregation_clicks` и ClickHouse.
* DAG Airflow управляет последовательностью задач, запускает их вручную или автоматически каждую минуту.

---

## **5. Результаты**

* **Airflow DAG** виден в UI, задачи успешно выполняются (`success`).
* **Kafka топики** созданы, консьюмер получает агрегаты.
* **ClickHouse** хранит агрегированные клики по продуктам.
* Пайплайн полностью потоковый, данные проходят от генерации до хранилища.

---

## **6. Выводы**

1. Потоковая архитектура успешно реализована: Kafka → Airflow → ClickHouse.
2. Пайплайн полностью автоматизирован и устойчив к перезапуску VM.
3. Airflow DAG позволяет отслеживать выполнение, ошибки и логи.
4. Архитектура легко расширяется: новые DAG’и, новые топики, новые таблицы ClickHouse.

