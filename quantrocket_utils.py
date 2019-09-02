### System ###
import csv
from time import time
from collections import defaultdict
from functools import total_ordering
from contextlib import contextmanager

### Display ###
from termcolor import colored
from colorama import init as colorama_init

### QuantRocket ###
import trading_calendars as tc


LISTINGS_FILE = None
CONID_SYMBOL_MAP = defaultdict(dict)
SYMBOL_CONID_MAP = defaultdict(dict)
CONID_TIMEZONE_MAP = defaultdict(dict)


### Utilities ###

@contextmanager
def timeit(title=None):
    if title:
        print(title)
    start = time()
    yield
    elapsed = time() - start
    if elapsed < 1:
        print("{}  finished in {} ms".format(colored("\u2713", "green"), int(elapsed * 1000)))
    elif elapsed < 60:
        print("{}  finished in {:0.2f} sec".format(colored("\u2713", "green"), elapsed))
    else:
        print("{}  finished in {:0.2f} min".format(colored("\u2713", "green"), elapsed / 60))

###


def initialize(listings_file):
    global LISTINGS_FILE, CONID_SYMBOL_MAP, SYMBOL_CONID_MAP, CONID_TIMEZONE_MAP
    colorama_init()

    LISTINGS_FILE = listings_file

    with open(LISTINGS_FILE, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for line in reader:
            conid, symbol, primary_exchange, timezone = int(line[0]), line[1], line[4], line[10]
            # CONID_SYMBOL_MAP[conid] = (primary_exchange, symbol)
            CONID_SYMBOL_MAP[str(conid)] = (primary_exchange, symbol)
            SYMBOL_CONID_MAP[symbol][primary_exchange] = conid
            CONID_TIMEZONE_MAP[conid] = timezone


@total_ordering
class Asset():

    def __init__(self, conid_or_symbol, exchange=None):
        conid_or_symbol = str(conid_or_symbol)
        if not LISTINGS_FILE:
            raise Exception("Listings file is not set. Did you forget to call initialize()?")
        if conid_or_symbol in CONID_SYMBOL_MAP:
            # Input is a ConId
            self.conid = int(conid_or_symbol)
            self.exchange, self.symbol = CONID_SYMBOL_MAP[conid_or_symbol]
        elif conid_or_symbol in SYMBOL_CONID_MAP:
            # Input is a Symbol
            if exchange and exchange not in SYMBOL_CONID_MAP[conid_or_symbol]:
                raise Exception("{} is not a valid exchange for symbol {}."
                                "\nValid exchanges are: {}".format(exchange, conid_or_symbol, ", ".join(list(SYMBOL_CONID_MAP[conid_or_symbol].keys()))))
            if len(SYMBOL_CONID_MAP[conid_or_symbol]) > 1:
                if exchange:
                    self.conid = SYMBOL_CONID_MAP[conid_or_symbol][exchange]
                    self.symbol = conid_or_symbol
                    self.exchange = exchange
                else:
                    raise Exception("Multiple symbols found. Please specify an exchange."
                                    "\nValid exchanges are: {}".format(", ".join(list(SYMBOL_CONID_MAP[conid_or_symbol].keys()))))
            else:
                self.exchange, self.conid = list(SYMBOL_CONID_MAP[conid_or_symbol].items())[0]
                self.symbol = conid_or_symbol
        else:
            raise Exception("{} is neither a valid symbol nor a valid ConId".format(conid_or_symbol))

        self.timezone = CONID_TIMEZONE_MAP[self.conid]

        available_calendars = set(tc.calendar_utils._default_calendar_aliases.keys()) | \
            set(tc.calendar_utils._default_calendar_aliases.values())
        self.calendar = tc.get_calendar(self.exchange) if self.exchange in available_calendars else None

    def can_trade(self, date, time=None):
        """Given a date and optional time, returns whether the asset can be traded at that time.

        This will check dates and times in the timezone of the exchange the asset is traded in.
        If no calendar could be determined for the asset, the result is always 'True'.
        """
        if not self.calendar:
            return True
        if time:
            datetime = arrow.get("{} {}".format(date, time), "YYYY-MM-DD HH:mm:ss")
        else:
            datetime = arrow.get(date, "YYYY-MM-DD")
        datetime = datetime.replace(tzinfo=self.calendar.tz).to("UTC")
        if datetime.date() in self.calendar.schedule.index:
            # Exchange is open
            if time:
                market_open, market_close = self.calendar.schedule.loc[datetime.date()]
                if not market_open.time() <= datetime.time() <= market_close.time():
                    # Current time is not in open range, either too early or too late
                    return False
            else:
                return True
            return True
        else:
            # Exchange is closed
            return False

    def __eq__(self, other):
        return self.conid == other.conid

    def __lt__(self, other):
        return (self.conid < other.conid)

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        calendar_name = self.calendar.name if self.calendar else None
        return "Asset(ConId={}, Symbol={}, Exchange={}, Timezone={}, calendar={})".format(self.conid,
                                                                                          self.symbol,
                                                                                          self.exchange,
                                                                                          self.timezone,
                                                                                          calendar_name)
