import unittest

from . import account


class TestAccount(unittest.TestCase):

    def test_account_join(self):
        account_name = account.join("Expenses", "Toys", "Computer")
        self.assertEqual("Expenses:Toys:Computer", account_name)

        account_name = account.join("Expenses")
        self.assertEqual("Expenses", account_name)

        account_name = account.join()
        self.assertEqual("", account_name)

    def test_account_name_parent(self):
        self.assertEqual("Expenses:Toys",
                         account.account_name_parent("Expenses:Toys:Computer"))
        self.assertEqual("Expenses", account.account_name_parent("Expenses:Toys"))
        self.assertEqual("", account.account_name_parent("Expenses"))
        self.assertEqual(None, account.account_name_parent(""))

    def test_account_name_leaf(self):
        self.assertEqual("Computer", account.account_name_leaf("Expenses:Toys:Computer"))
        self.assertEqual("Toys", account.account_name_leaf("Expenses:Toys"))
        self.assertEqual("Expenses", account.account_name_leaf("Expenses"))
        self.assertEqual(None, account.account_name_leaf(""))
