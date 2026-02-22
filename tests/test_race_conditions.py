import threading
import time

import pytest
from django.db import transaction
from django.db.models import F

from app.models import Account

"""
A race condition occurs when multiple threads or processes access and modify 
shared resource concurrently, leading to unpredictable or incorrect results
due to timing dependencies. These bugs are often hard to reproduce because
they depend on the execution order of threads.

These tests show what NOT to do and how to properly guard against this 
problem.

These tests require PostgreSQL or similar database to have proper 
transaction handling across database connections.
"""


def deposit_naive(account_id, amount=100, delay=1):
    """
    This will reliably trigger a race condition on the update of the balance
    attribute when called multiple times simultaneously.
    """
    acc = Account.objects.get(id=account_id)

    time.sleep(delay)

    acc.balance = acc.balance + amount
    acc.save()


def deposit_select_related(account_id, amount=100, delay=1):
    """
    This examples shows that select_related does not help you ;)
    """

    acc = Account.objects.select_related().get(id=account_id)

    time.sleep(delay)

    acc.balance = acc.balance + amount
    acc.save()


def deposit_select_for_update_slow(account_id, amount=100, delay=1):
    """
    This function acquires an exclusive lock on the account row in a
    transaction, ensuring that no other transaction can read or modify it
    until the current transaction is complete.

    Because of this, slow operations - like the sleep in this example - makes
    it very slow with high concurrency.
    Always try to keep these kind of transactions as fast as possible.

    See deposit_select_for_update_fast
    """

    with transaction.atomic():
        acc = Account.objects.select_for_update().get(id=account_id)

        time.sleep(delay)

        acc.balance = acc.balance + amount
        acc.save()


def deposit_select_for_update_fast(account_id, amount=100, delay=1):
    """
    Same as deposit_select_for_update_slow but the slow operation is not part
    of the transaction. This improves overall execution time dramatically.

    See deposit_select_for_update_slow
    """

    time.sleep(delay)

    with transaction.atomic():
        acc = Account.objects.select_for_update().get(id=account_id)
        acc.balance = acc.balance + amount
        acc.save()


def deposit_atomic(account_id, amount=100, delay=1):
    """
    The update (balance = balance + amount) happens entirely in the database,
    not in Python. With F(), the database handles the math, ensuring atomicit
    even with high concurrency.

    In the real world, you often can not use this shortcut to guard against
    race conditions and must rely on other methods like select_for_update.

    See deposit_select_for_update_fast
    """
    time.sleep(delay)
    Account.objects.filter(id=account_id).update(balance=F("balance") + amount)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("f", "min_time", "max_time", "fail_reason"),
    [
        (
            deposit_naive,
            1,
            2,
            "Race condition during parallel execution found because nothing was done to prevent it.",
        ),
        (
            deposit_select_related,
            1,
            2,
            "Race condition during parallel execution found because select_related does not protect against it.",
        ),
        (deposit_select_for_update_slow, 10, 11, ""),
        (deposit_select_for_update_fast, 1, 2, ""),
        (deposit_atomic, 1, 2, ""),
    ],
)
def test_raceconditions(f, min_time, max_time, fail_reason):
    # Test setup
    number_of_threads = 10
    balance_increment = 100

    acc = Account.objects.create(owner="Nora", balance=0)

    # Prepare and start all the threads
    threads = [
        threading.Thread(target=f, args=(acc.id, balance_increment, 1))
        for _ in range(number_of_threads)
    ]

    time_start = time.perf_counter()
    for t in threads:
        t.start()

    for t in threads:
        t.join()
    time_end = time.perf_counter()

    # Making sure that the execution time is in the limits we assume
    # This makes sure we actually run into race conditions
    elapsed = time_end - time_start

    assert elapsed > min_time
    assert elapsed < max_time

    # Making sure to get the latest version from the database for the assert
    acc.refresh_from_db()

    if fail_reason:
        with pytest.raises(AssertionError):
            assert acc.balance == balance_increment * number_of_threads, (
                fail_reason
            )
    else:
        assert acc.balance == balance_increment * number_of_threads
