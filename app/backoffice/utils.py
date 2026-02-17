from datetime import time
from django.utils import timezone


def is_market_open():
    now = timezone.localtime().time()
    return time(9, 30) <= now <= time(15, 30)
