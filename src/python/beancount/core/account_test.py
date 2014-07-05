import unittest

from . import account


class TestAccount(unittest.TestCase):

    def test_is_valid(self):
        self.assertTrue(account.is_valid("Assets:US:RBS:Checking"))
        self.assertTrue(account.is_valid("Equity:OpeningBalances"))
        self.assertTrue(account.is_valid("Income:US:ETrade:Dividends-USD"))
        self.assertTrue(account.is_valid("Assets:US:RBS"))
        self.assertTrue(account.is_valid("Assets:US"))
        self.assertFalse(account.is_valid("Assets"))
        self.assertFalse(account.is_valid("Invalid"))
        self.assertFalse(account.is_valid("Other"))
        self.assertFalse(account.is_valid("Assets:US:RBS*Checking"))
        self.assertFalse(account.is_valid("Assets:US:RBS:Checking&"))
        self.assertFalse(account.is_valid("Assets:US:RBS:checking"))
        self.assertFalse(account.is_valid("Assets:us:RBS:checking"))

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

    def test_account_sans_root(self):
        self.assertEqual("Toys:Computer",
                         account.account_name_sans_root("Expenses:Toys:Computer"))
        self.assertEqual("US:BofA:Checking",
                         account.account_name_sans_root("Assets:US:BofA:Checking"))
        self.assertEqual("", account.account_name_sans_root("Assets"))

    def test_has_component(self):
        self.assertTrue(account.has_component('Liabilities:US:Credit-Card', 'US'))
        self.assertFalse(account.has_component('Liabilities:US:Credit-Card', 'CA'))
        self.assertTrue(account.has_component('Liabilities:US:Credit-Card', 'Credit-Card'))
        self.assertTrue(account.has_component('Liabilities:US:Credit-Card', 'Liabilities'))
        self.assertFalse(account.has_component('Liabilities:US:Credit-Card', 'Credit'))
        self.assertFalse(account.has_component('Liabilities:US:Credit-Card', 'Card'))

    def test_commonprefix(self):
        self.assertEqual('Assets:US:TD',
                         account.commonprefix(['Assets:US:TD:Checking',
                                               'Assets:US:TD:Savings']))
        self.assertEqual('Assets:US',
                         account.commonprefix(['Assets:US:TD:Checking',
                                               'Assets:US:BofA:Checking']))
        self.assertEqual('Assets',
                         account.commonprefix(['Assets:US:TD:Checking',
                                               'Assets:CA:RBC:Savings']))
        self.assertEqual('',
                         account.commonprefix(['Assets:US:TD:Checking',
                                               'Liabilities:US:CreditCard']))
        self.assertEqual('',
                         account.commonprefix(['']))
