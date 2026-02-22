import threading
import time

import pytest
from django.db import transaction
from django.db.models import F

from app.models import Account


def deposit_naive(account_id, amount=100, delay=0):
    acc = Account.objects.get(id=account_id)

    if delay:
        time.sleep(delay)

    acc.balance = acc.balance + amount
    acc.save()


def deposit_select_related(account_id, amount=100, delay=0):
    acc = Account.objects.select_related().get(id=account_id)

    if delay:
        time.sleep(delay)

    acc.balance = acc.balance + amount
    acc.save()


def deposit_select_for_update_slow(account_id, amount=100, delay=0):
    with transaction.atomic():
        acc = Account.objects.select_for_update().get(id=account_id)

        if delay:
            # TODO: Add note why long running tasks are bad in a transaction
            time.sleep(delay)

        acc.balance = acc.balance + amount
        acc.save()


def deposit_select_for_update_fast(account_id, amount=100, delay=0):
    if delay:
        time.sleep(delay)

    with transaction.atomic():
        acc = Account.objects.select_for_update().get(id=account_id)
        acc.balance = acc.balance + amount
        acc.save()


def deposit_atomic(account_id, amount=100, delay=0):
    Account.objects.filter(id=account_id).update(balance=F("balance") + amount)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("f", "fail_reason"),
    [
        (
            deposit_naive,
            "Race condition during parallel execution found because nothing was done to prevent it.",
        ),
        (
            deposit_select_related,
            "Race condition during parallel execution found because select_related does not protect against it.",
        ),
        (deposit_select_for_update_slow, ""),
        (deposit_select_for_update_fast, ""),
        (deposit_atomic, ""),
    ],
)
def test_raceconditions(f, fail_reason):
    acc = Account.objects.create(owner="carol", balance=0)

    number_of_threads = 10
    balance_increment = 100

    threads = [
        threading.Thread(target=f, args=(acc.id, balance_increment, 1))
        for _ in range(number_of_threads)
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    acc.refresh_from_db()

    if fail_reason:
        with pytest.raises(AssertionError):
            assert acc.balance == balance_increment * number_of_threads, (
                fail_reason
            )
    else:
        assert acc.balance == balance_increment * number_of_threads
