from quantrocket_utils import Asset, initialize
from .base import QRTestCase


class AssetTestCase(QRTestCase):

    def __init__(self, *args, **kwargs):
        initialize("../data/listings.csv")
        super().__init__(*args, **kwargs)

    def test_asset(self):

        spy = Asset("SPY", "NYSE")

        self.assertEqual(spy.selected_exchange, "NYSE")
