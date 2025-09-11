import pytest
# ✅ Correct (since kafka_producer.py is inside core/)
from core.producers import publish_margin_request, publish_forced_sell, KafkaProducerWrapper


@pytest.mark.django_db
def test_publish_margin_request():
    result = publish_margin_request(client_id=1, amount=5000.0)
    assert result is True


@pytest.mark.django_db
def test_publish_forced_sell():
    result = publish_forced_sell(client_id=2, portfolio_id=10, reason="Margin call")
    assert result is True


def test_producer_singleton():
    # Ensure singleton producer
    producer1 = KafkaProducerWrapper.get_producer()
    producer2 = KafkaProducerWrapper.get_producer()
    assert producer1 is producer2

    KafkaProducerWrapper.close()
    producer3 = KafkaProducerWrapper.get_producer()
    assert producer1 is not producer3  # new producer created
