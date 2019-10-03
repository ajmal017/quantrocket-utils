from unittest import TestCase


class QRTestCase(TestCase):

    def assertManyResults(self, function, args, results):
        """Goes through a list of arguments and makes sure that function called
        upon them lists a similarly ordered list of results.  If more than one
        argument is required, each position in args may be a tuple."""
        for arg, result in zip(args, results):
            if isinstance(arg, tuple):
                self.assertEqual(function(*arg), result)
            else:
                self.assertEqual(function(arg), result)
