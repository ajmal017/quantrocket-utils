### System ###
import os
import csv
import pickle
from time import time
from collections import defaultdict
from functools import total_ordering
from contextlib import contextmanager

### Date Handling ###
import arrow

### Display ###
from termcolor import colored
from colorama import init as colorama_init

### QuantRocket ###
import trading_calendars as tc1
import ib_trading_calendars as tc2


LISTINGS_FILE = None
CONID_SYMBOL_MAP = defaultdict(dict)
SYMBOL_CONID_MAP = defaultdict(list)
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
        print("{}  finished in {} ms".format(colored("\u2713", "green"),
                                             int(elapsed * 1000)))
    elif elapsed < 60:
        print("{}  finished in {:0.2f} sec".format(colored("\u2713", "green"),
                                                   elapsed))
    else:
        print("{}  finished in {:0.2f} min".format(colored("\u2713", "green"),
                                                   elapsed / 60))


def is_quantrocket():
    try:
        from quantrocket.houston import Houston
        return Houston().get("/").status_code == 200
    except:  # noqa: E722
        return False

###


def initialize(listings_file):
    global LISTINGS_FILE, CACHE_FILE, CONID_SYMBOL_MAP
    global SYMBOL_CONID_MAP, CONID_TIMEZONE_MAP
    colorama_init()

    LISTINGS_FILE = listings_file
    CACHE_FILE = "{}.bin".format(os.path.splitext(listings_file)[0])

    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
            CONID_SYMBOL_MAP, SYMBOL_CONID_MAP, CONID_TIMEZONE_MAP = data
    else:
        with open(LISTINGS_FILE, "r") as f:
            reader = csv.reader(f)
            next(reader)
            for line in reader:
                conid, symbol, primary_exchange = (int(line[0]), line[1], line[4])
                timezone, valid_exchanges = (line[10], line[11].split(","))
                CONID_SYMBOL_MAP[str(conid)] = (symbol, primary_exchange,
                                                valid_exchanges)
                SYMBOL_CONID_MAP[symbol].append((conid, primary_exchange,
                                                 valid_exchanges))
                CONID_TIMEZONE_MAP[conid] = timezone

        data = (CONID_SYMBOL_MAP, SYMBOL_CONID_MAP, CONID_TIMEZONE_MAP)
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    for asset in Asset:
        if not asset._initialized:
            asset.initialize()


class IterRegistry(type):

    def __iter__(cls):
        return iter(cls._registry)


@total_ordering
class Asset(metaclass=IterRegistry):
    _registry = []

    def __init__(self, conid_or_symbol, exchange=None, ignore_exchange=False):
        self._registry.append(self)
        self._init_conid_or_symbol = conid_or_symbol
        self._init_exchange = exchange
        self._initialized = False
        self.conid = None
        self.primary_exchange = None
        self.ignore_exchange = ignore_exchange
        if LISTINGS_FILE:
            self.initialize()

    def initialize(self):
        self._init_conid_or_symbol = str(self._init_conid_or_symbol)
        if not LISTINGS_FILE:
            raise Exception("Listings file is not set.\
                             Did you forget to call initialize()?")
        if self._init_conid_or_symbol in CONID_SYMBOL_MAP:
            # Input is a ConId
            self.conid = int(self._init_conid_or_symbol)
            self.symbol, self.primary_exchange, self.valid_exchanges = CONID_SYMBOL_MAP[self._init_conid_or_symbol]  # noqa:E501
        elif self._init_conid_or_symbol in SYMBOL_CONID_MAP:
            # Input is a Symbol
            if not self._init_exchange:
                if len(SYMBOL_CONID_MAP[self._init_conid_or_symbol]) == 1:
                    conid, primary_exchange, valid_exchanges = SYMBOL_CONID_MAP[self._init_conid_or_symbol][0]  # noqa:E501
                    self.conid = int(conid)
                    self.symbol = self._init_conid_or_symbol
                    self.primary_exchange = primary_exchange
                    self.valid_exchanges = valid_exchanges
                elif not self.ignore_exchange:
                    all_exchanges = []
                    for item in SYMBOL_CONID_MAP[self._init_conid_or_symbol]:
                        all_exchanges.extend(item[2])
                    raise Exception("Multiple symbols found. Please specify an exchange."  # noqa:E501
                                    "\nValid exchanges are: {}".format(", ".join(sorted(set(all_exchanges)))))  # noqa:E501
                else:
                    self.symbol = self._init_conid_or_symbol
            else:
                for conid, primary_exchange, valid_exchanges in SYMBOL_CONID_MAP[self._init_conid_or_symbol]:  # noqa:E501
                    if self._init_exchange == primary_exchange or \
                       self._init_exchange in valid_exchanges:
                        self.conid = int(conid)
                        self.symbol = self._init_conid_or_symbol
                        self.primary_exchange = primary_exchange
                        self.valid_exchanges = valid_exchanges
                        break
                else:
                    all_exchanges = []
                    for item in SYMBOL_CONID_MAP[self._init_conid_or_symbol]:
                        all_exchanges.extend(item[2])
                    raise Exception("{} is not a valid exchange."
                                    "\nValid exchanges are: {}".format(self._init_exchange, ", ".join(sorted(set(all_exchanges)))))  # noqa:E501
        else:
            raise Exception("{} is neither a valid symbol nor a valid ConId".format(self._init_conid_or_symbol))  # noqa:E501

        self.timezone = CONID_TIMEZONE_MAP[self.conid]
        self.selected_exchange = self._init_exchange or self.primary_exchange

        if not self.ignore_exchange:
            s1 = set(tc1.calendar_utils._default_calendar_aliases.keys())
            s2 = set(tc1.calendar_utils._default_calendar_aliases.values())
            available_calendars_1 = s1 | s2
            available_calendars_2 = set(tc2.ib_calendar_names)
            self.calendar = None
            if self.selected_exchange in available_calendars_2:
                self.calendar = tc1.get_calendar(self.selected_exchange)
            elif self.selected_exchange in available_calendars_1:
                self.calendar = tc2.get_calendar(self.selected_exchange)

        self._initialized = True

    def can_trade(self, date, time=None):
        """Given a date and optional time, returns whether the asset can be traded.

        This will check dates and times in the timezone
        of the exchange the asset is traded in.
        If no calendar could be determined for the asset,
        the result is always 'True'.
        """
        if not self.calendar:
            return True
        if time:
            datetime = arrow.get("{} {}".format(date, time), "YYYY-MM-DD HH:mm:ss")  # noqa:E501
        else:
            datetime = arrow.get(date, "YYYY-MM-DD")
        datetime = datetime.replace(tzinfo=self.calendar.tz).to("UTC")
        if datetime.date() in self.calendar.schedule.index:
            # Exchange is open
            if time:
                market_open, market_close = self.calendar.schedule.loc[datetime.date()]  # noqa:E501
                if not market_open.time() <= datetime.time() <= market_close.time():  # noqa:E501
                    # Current time is not in open range,
                    # either too early or too late
                    return False
            else:
                return True
            return True
        else:
            # Exchange is closed
            return False

    def __eq__(self, other):
        if self.ignore_exchange or other.ignore_exchange:
            return self.symbol == other.symbol
        return self.conid == other.conid

    def __lt__(self, other):
        if self.ignore_exchange or other.ignore_exchange:
            return self.symbol < other.symbol
        return self.conid < other.conid

    def __hash__(self):
        if self.ignore_exchange:
            return hash(self.symbol)
        return hash(self.conid)

    def __repr__(self):
        if not self._initialized:
            return "Asset(uninitialized)"
        if self.ignore_exchange:
            return "Asset(Symbol={})".format(self.symbol)
        else:
            calendar_name = self.calendar.name if self.calendar else None
            return "Asset(ConId={}, Symbol={}, Exchange={}, Timezone={}, calendar={})".format(self.conid,  # noqa:E501
                                                                                              self.symbol,  # noqa:E501
                                                                                              self.selected_exchange,  # noqa:E501
                                                                                              self.timezone,  # noqa:E501
                                                                                              calendar_name)  # noqa:E501
