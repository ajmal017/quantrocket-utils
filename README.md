# QuantRocket Utility Library
Utility methods for common tasks in QuantRocket.

## Installation
`quantrocket-utils` can be installed via `pip`:
```bash
$ pip install quantrocket-utils
```

## Development

This project uses [poetry](https://poetry.eustace.io/) for development and release management.
```
$ git clone git@github.com:boosting-alpha-bv/quantrocket-utils.git
$ cd quantrocket-utils/
$ poetry install
```

### Running Tests
```bash
$ poetry run coverage run --branch --source quantrocket_utils -m pytest
```

### Generating Coverage Reports
```bash
$ poetry run coverage html
```

### Running flake8
```bash
$ poetry run flake8 quantrocket_utils tests
```

### Deploying
```bash
$ poetry publish --build --username "${PYPI_USERNAME}" --password "${PYPI_PASSWORD}" --no-interaction
```

## Usage
This library requires an external file that contains the listing information for the stocks it should translate.
This is typically exported from QuantRocket and then supplied at initialization time of the library.
Work is currently under way to remove the dependency on QuantRocket for obtaining this listings file.

```python
# Import the library and initialize the ConID resolution
from quantrocket_utils import initialize as assets_init, Asset
assets_init("<path>/<to>/listings.csv")

# Create an Asset using the symbol name
spy = Asset("SPY")
# The exchange is optional, unless two symbols of the same name exist on different exchanges
spy = Asset("SPY", "ARCA")

# Create an Asset using the ConID
# In this case the exchange can be inferred from the ConID, so it is always otpional
spy = Asset(756733)
# ConID's can be strings as well, so don't worry about type conversion
spy = Asset("756733")

# Access data on the object
spy.conid
>> 756733
spy.symbol
>> "SPY"
spy.exchange
>> "ARCA"

# Check trading times
spy.can_trade("2019-03-04", "10:34:02")
>> True

# Assets also support equality and comparison operations based on the ConID
# However, this is mostly just useful for guaranteeing sorting order
# Assets are also hashable and can thus be utilized in set operations
Asset("SPY") < Asset("AAPL")
>> True
```
