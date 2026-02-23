import pytest
from app.models import AccountWithDynamicBackend, BACKENDS


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("backend", "config", "result"),
    [
        (BACKENDS.FIRSTBACKEND, {"extra": "Alpha"}, "First Alpha"),
        (BACKENDS.SECONDBACKEND, {"other_extra": "Beta"}, "Second Beta"),
    ],
)
def test_dynamic_backend(backend, config, result):
    """
    Ensure that AccountWithDynamicBackend correctly instantiates and uses the
    configured backend class with its provided configuration.

    This allows you to have multiple different implementations for a
    functionality and switch based on the values in a database.

    The test parametrizes multiple backend implementations and verifies that:
    1. The model resolves the backend from `backend_class`.
    2. The backend receives the stored `backend_config`.
    3. Calling the backend returns the expected backend-specific result.
    """
    acc = AccountWithDynamicBackend.objects.create(
        owner="Nora", balance=0, backend_class=backend, backend_config=config
    )

    bknd = acc.backend
    assert bknd.call() == result
