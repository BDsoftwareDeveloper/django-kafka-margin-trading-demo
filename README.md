# Django Kafka Margin Trading Demo

A demo **Order Management System (OMS)** showcasing **margin trading** with  
**Django + Kafka + PostgreSQL**.  
This project simulates **margin loan requests, portfolio updates, and forced sell events**  
using event-driven microservice patterns.

---

## 🔑 Features
- **Django ORM** with PostgreSQL for persistence
- **Kafka Producers & Consumers** for event streaming
- **Margin Loan Requests** → published to Kafka
- **Portfolio Updates** → consumed and processed
- **Forced Sell Logic** when margin breaches occur
- **Audit Logging** for all trading events
- **Dockerized** for easy setup

---

## 📂 Project Structure
django-kafka-margin-trading-demo/
    app/
        │── core/ # Kafka producers & consumers
        │── oms_margin_demo/ # Django project
        │── manage.py # Django CLI
        │── docker-compose.yml # Multi-service orchestration
        │── Dockerfile # Django app container
        │── requirements.txt # Dependencies
        │── README.md # Project docs
        │── .gitignore # Git ignores



---

## 🚀 Getting Started

### 1️⃣ Clone Repo
```bash
git clone https://github.com/YOUR_USERNAME/django-kafka-margin-trading-demo.git
cd django-kafka-margin-trading-demo


### 2. Environment Setup

Create .env file in project root:

```
POSTGRES_DB=omsdb
POSTGRES_USER=omsuser
POSTGRES_PASSWORD=omspassword
POSTGRES_HOST=db
POSTGRES_PORT=5432
KAFKA_BROKER=kafka:9092
```


### 3. Start Services

```docker-compose up -d --build```

### 4. Run Migrations

```docker-compose exec django python manage.py makemigrations
docker-compose exec django python manage.py migrate
```
### 5. Create Superuser (optional)
```bash
docker-compose exec django python manage.py createsuperuser



🔄 Migrations Note

Migration files are excluded from git (see .gitignore).

Each developer should generate migrations locally after pulling changes:


```bash
docker-compose exec django python manage.py makemigrations
docker-compose exec django python manage.py migrate

🗄️ Database Persistence
Postgres data is stored in postgres_data/ (Docker volume).

This folder is gitignored to prevent large binary files being tracked.

📝 Audit Logging
Every margin-related event (loan request, approval, rejection, forced sell) is logged via AuditLog model.
Example:
```python
AuditLog.log_event(
    event_type="MARGIN_REQUEST",
    client=client,
    details={"amount": 2000}
)


🧑‍💻 Development Notes

Consumers run inside Docker and auto-connect to Kafka.

Restart consumers if code changes:

```bash
docker-compose restart margin_consumer portfolio_consumer


✅ Next Steps

Add unit tests for consumer logic

Extend portfolio valuation rules

Add a dashboard to view margin logs in real time

```yml

---

Would you like me to also **add a `makefile`** (with shortcuts for `up`, `down`, `migrate`, etc.) so your team doesn’t need to type long `docker-compose` commands?



 Run Tests
 ```bash
 docker-compose exec web pytest -q -s

📌 Example Usage
```bash
docker-compose exec web python manage.py shell


Create client & margin loan:

```python
from core.models import Client, MarginLoan

client = Client.objects.create(name="Alice")
loan = MarginLoan.objects.create(client=client, loan_amount=2000)

