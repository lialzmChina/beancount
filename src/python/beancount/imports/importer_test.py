import unittest
import re

from beancount.imports import importer


class TestAccount(unittest.TestCase):

    def test_accountify_dict(self):
        accvalue_dict = {"b6edc1bf714a": "Assets:US:RBS:Savings",
                         "21a4647fe535": "Liabilities:US:RBS:MortgageLoan",
                         "6d17539d6c32": "Equity:OpeningBalances",
                         "421833fa2cb9": "Income:US:Intel",
                         "391bb475127e": "Expenses:Toys:Computer"}
        newdict = importer.accountify_dict(accvalue_dict)
        self.assertTrue(isinstance(newdict, dict))
        self.assertEqual("Income:US:Intel", newdict["421833fa2cb9"].name)


__incomplete__ = True  ## You need to update the tests for new changes in account.py
