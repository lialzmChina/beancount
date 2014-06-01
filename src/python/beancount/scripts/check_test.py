import re

from beancount.utils import test_utils
from beancount.scripts import check


class TestScriptCheck(test_utils.TestCase):

    @test_utils.docfile
    def test_success(self, filename):
        """
        2013-01-01 open Expenses:Restaurant
        2013-01-01 open Assets:Cash

        2014-03-02 * "Something"
          Expenses:Restaurant   50.02 USD
          Assets:Cash
        """
        with test_utils.capture() as stdout:
            test_utils.run_with_args(check.main, [filename])
        r = self.assertLines("", stdout.getvalue())

    @test_utils.docfile
    def test_fail(self, filename):
        """
        2013-01-01 open Expenses:Restaurant
        2013-01-01 open Assets:Cash

        2014-03-02 * "Something"
          Expenses:Restaurant   50.02 USD
          Assets:Cash

        2014-03-07 balance Assets:Cash  100 USD
        """
        with test_utils.capture() as stdout:
            test_utils.run_with_args(check.main, [filename])
        self.assertTrue(re.search("Balance failed", stdout.getvalue()))
        self.assertTrue(re.search("Assets:Cash", stdout.getvalue()))
