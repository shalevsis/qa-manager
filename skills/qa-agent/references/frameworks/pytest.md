# Pytest Reference

## Test structure

```python
import pytest
from mymodule import my_function

def test_basic_case():
    assert my_function(5) == 10

def test_raises_on_invalid_input():
    with pytest.raises(ValueError, match="must be positive"):
        my_function(-1)
```

## Fixtures

```python
@pytest.fixture
def sample_user():
    return {"id": 1, "name": "Alice"}

@pytest.fixture
def db_connection():
    conn = create_test_db()
    yield conn      # test runs here
    conn.close()    # teardown
```

## Parametrize

```python
@pytest.mark.parametrize("input,expected", [(0, 0), (1, 2), (-5, -10)])
def test_doubles(input, expected):
    assert double(input) == expected
```

## Mocking

```python
from unittest.mock import patch

def test_calls_api():
    with patch("mymodule.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}
        result = my_function()
    mock_get.assert_called_once()

# With pytest-mock
def test_sends_email(mocker):
    mock_send = mocker.patch("mymodule.send_email")
    process_order(42)
    mock_send.assert_called_once()
```

## Running

```bash
pytest -v --tb=short
pytest --cov=src --cov-report=term-missing
pytest -x                   # stop on first failure
pytest --lf                 # re-run last failed
```
