__author__ = "Martin Blais <blais@furius.ca>"

import io
from datetime import date
import unittest
import re
import textwrap

from beancount.parser import printer
from beancount.parser import cmptest
from beancount.core import data
from beancount.core import interpolate
from beancount.utils import test_utils
from beancount import loader


META = data.new_metadata('beancount/core/testing.beancount', 12345)

class TestPrinter(unittest.TestCase):

    def test_methods_coverage(self):
        for klass in data.ALL_DIRECTIVES:
            self.assertTrue(hasattr(printer.EntryPrinter, klass.__name__))

    def test_render_source(self):
        source_str = printer.render_source(META)
        self.assertTrue(isinstance(source_str, str))
        self.assertTrue(re.search('12345', source_str))
        self.assertTrue(re.search(META['filename'], source_str))

    def test_format_and_print_error(self):
        entry = data.Open(META, date(2014, 1, 15), 'Assets:Bank:Checking', [], None)
        error = interpolate.BalanceError(META, "Example balance error", entry)
        error_str = printer.format_error(error)
        self.assertTrue(isinstance(error_str, str))

        oss = io.StringIO()
        printer.print_error(error, oss)
        self.assertTrue(isinstance(oss.getvalue(), str))

        oss = io.StringIO()
        printer.print_errors([error], oss)
        self.assertTrue(isinstance(oss.getvalue(), str))


class TestEntryPrinter(cmptest.TestCase):

    def assertRoundTrip(self, entries1, errors1):
        self.assertFalse(errors1)

        # Print out the entries and parse them back in.
        oss1 = io.StringIO()
        oss1.write('option "plugin_processing_mode" "raw"\n')
        oss1.write('option "experiment_query_directive" "TRUE"\n')
        printer.print_entries(entries1, file=oss1)
        entries2, errors, __ = loader.load_string(oss1.getvalue())

        self.assertEqualEntries(entries1, entries2)
        self.assertFalse(errors)

        # Print out those reparsed and parse them back in.
        oss2 = io.StringIO()
        oss2.write('option "plugin_processing_mode" "raw"\n')
        oss2.write('option "experiment_query_directive" "TRUE"\n')
        printer.print_entries(entries2, file=oss2)
        entries3, errors, __ = loader.load_string(oss2.getvalue())

        self.assertEqualEntries(entries1, entries3)
        self.assertFalse(errors)

        # Compare the two output texts.
        self.assertEqual(oss2.getvalue(), oss1.getvalue())

    @loader.load_doc()
    def test_Transaction(self, entries, errors, __):
        """
        2014-01-01 open Assets:Account1
        2014-01-01 open Assets:Account2
        2014-01-01 open Assets:Account3
        2014-01-01 open Assets:Account4
        2014-01-01 open Assets:Cash

        2014-06-08 *
          Assets:Account1       111.00 BEAN
          Assets:Cash          -111.00 BEAN

        2014-06-08 * "Narration"
          Assets:Account1       111.00 BEAN
          Assets:Cash          -111.00 BEAN

        2014-06-08 * "Payee" | "Narration"
          Assets:Account1       111.00 BEAN
          Assets:Cash          -111.00 BEAN

        2014-06-08 * "Payee" "Narration" ^link1 ^link2 #tag1 #tag2
          Assets:Account1       111.00 BEAN
          Assets:Cash          -111.00 BEAN

        2014-06-08 * "Narration"
          Assets:Account1       111.00 BEAN {53.24 USD}
          Assets:Cash         -5909.64 USD

        2014-06-08 !
          Assets:Account1       111.00 BEAN {53.24 USD} @ 55.02 USD
          Assets:Account2       111.00 BEAN {53.24 USD}
          Assets:Account3       111.00 BEAN @ 55.02 USD
          Assets:Account4       111.00 BEAN
          Assets:Cash          -111.00 BEAN
          Assets:Cash         -17926.5 USD

        2014-06-08 *
          Assets:Account1         111.00 BEAN
          ! Assets:Account2       111.00 BEAN
          * Assets:Account3       111.00 BEAN
          ? Assets:Account4      -333.00 BEAN

        2014-06-09 * "An entry like a conversion entry"
          Assets:Account1         1 USD @ 0 OTHER
          Assets:Account2         1 CAD @ 0 OTHER
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Balance(self, entries, errors, __):
        """
        2014-06-01 open Assets:Account1
        2014-06-08 balance Assets:Account1     0.00 USD
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Note(self, entries, errors, __):
        """
        2014-06-01 open Assets:Account1
        2014-06-08 note Assets:Account1 "Note"
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Document(self, entries, errors, __):
        """
        option "plugin_processing_mode" "raw"
        2014-06-01 open Assets:Account1
        2014-06-08 document Assets:Account1 "/path/to/document.pdf"
        2014-06-08 document Assets:Account1 "path/to/document.csv"
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Query(self, entries, errors, __):
        """
        option "plugin_processing_mode" "raw"
        2014-06-08 query "cash" "SELECT sum(position) WHERE currency = 'USD'"
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Pad(self, entries, errors, __):
        """
        2014-01-01 open Assets:Account1
        2014-01-01 open Assets:Account2
        2014-06-08 pad Assets:Account1 Assets:Account2
        2014-10-01 balance Assets:Account1  1 USD
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Open(self, entries, errors, __):
        """
        2014-06-08 open Assets:Account1
        2014-06-08 open Assets:Account2  USD
        2014-06-08 open Assets:Account3  USD,CAD,EUR
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Close(self, entries, errors, __):
        """
        2014-01-01 open  Assets:Account1
        2014-06-08 close Assets:Account1
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Price(self, entries, errors, __):
        """
        2014-06-08 price  BEAN   53.24 USD
        2014-06-08 price  USD   1.09 CAD
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Event(self, entries, errors, __):
        """
        2014-06-08 event "location" "New York, NY, USA"
        2014-06-08 event "employer" "Four Square"
        """
        self.assertRoundTrip(entries, errors)

    @loader.load_doc()
    def test_Query(self, entries, errors, __):
        """
        option "experiment_query_directive" "TRUE"
        2014-06-08 query "cash" "SELECT SUM(position) WHERE currency = 'USD'"
        """
        self.assertRoundTrip(entries, errors)


def characterize_spaces(text):
    """Classify each line to a particular type.

    Args:
      text: A string, the text to classify.
    Returns:
      A list of line types, one for each line.
    """
    lines = []
    for line in text.splitlines():
        if re.match(r'\d\d\d\d-\d\d-\d\d open', line):
            linecls = 'open'
        elif re.match(r'\d\d\d\d-\d\d-\d\d price', line):
            linecls = 'price'
        elif re.match(r'\d\d\d\d-\d\d-\d\d', line):
            linecls = 'txn'
        elif re.match(r'[ \t]$', line):
            linecls = 'empty'
        else:
            linecls = None
        lines.append(linecls)
    return lines


class TestPrinterSpacing(unittest.TestCase):

    maxDiff = 8192

    def test_interline_spacing(self):
        input_text = textwrap.dedent("""\
        2014-01-01 open Assets:Account1
        2014-01-01 open Assets:Account2
        2014-01-01 open Assets:Cash

        2014-06-08 *
          Assets:Account1       111.00 BEAN
          Assets:Cash

        2014-06-08 * "Narration"
          Assets:Account1       111.00 BEAN
          Assets:Cash

        2014-06-08 * "Payee" | "Narration"
          Assets:Account2       111.00 BEAN
          Assets:Cash

        2014-10-01 close Assets:Account2

        2014-10-11 price BEAN   10 USD
        2014-10-12 price BEAN   11 USD
        2014-10-13 price BEAN   11 USD
        """)
        entries, _, __ = loader.load_string(input_text)

        oss = io.StringIO()
        printer.print_entries(entries, file=oss)

        expected_classes = characterize_spaces(input_text)
        actual_classes = characterize_spaces(oss.getvalue())

        self.assertEqual(expected_classes, actual_classes)


class TestDisplayContext(test_utils.TestCase):

    maxDiff = 2048

    @loader.load_doc()
    def test_precision(self, entries, errors, options_map):
        """
        2014-01-01 open Assets:Account
        2014-01-01 open Assets:Cash

        2014-07-01 *
          Assets:Account              1 INT
          Assets:Account            1.1 FP1
          Assets:Account          22.22 FP2
          Assets:Account        333.333 FP3
          Assets:Account      4444.4444 FP4
          Assets:Account    55555.55555 FP5
          Assets:Cash               -1 INT
          Assets:Cash             -1.1 FP1
          Assets:Cash           -22.22 FP2
          Assets:Cash         -333.333 FP3
          Assets:Cash       -4444.4444 FP4
          Assets:Cash     -55555.55555 FP5
        """
        dcontext = options_map['dcontext']
        oss = io.StringIO()
        printer.print_entries(entries, dcontext, file=oss)

        expected_str = textwrap.dedent("""
        2014-01-01 open Assets:Account
        2014-01-01 open Assets:Cash

        2014-07-01 *
          Assets:Account             1 INT
          Assets:Account           1.1 FP1
          Assets:Account         22.22 FP2
          Assets:Account       333.333 FP3
          Assets:Account     4444.4444 FP4
          Assets:Account   55555.55555 FP5
          Assets:Cash               -1 INT
          Assets:Cash             -1.1 FP1
          Assets:Cash           -22.22 FP2
          Assets:Cash         -333.333 FP3
          Assets:Cash       -4444.4444 FP4
          Assets:Cash     -55555.55555 FP5
        """)
        self.assertLines(expected_str, oss.getvalue())


class TestPrinterAlignment(test_utils.TestCase):

    maxDiff = None

    def test_align_position_strings(self):
        aligned_strings, width = printer.align_position_strings([
            '45 HOOL {504.30 USD}',
            '4 HOOL {504.30 USD / 2014-11-11}',
            '9.9505 USD',
            '',
            '-22473.32 CAD @ 1.10 USD',
            'UNKNOWN',
            '76400.203',
        ])
        self.assertEqual(40, width)
        self.assertEqual([
            '       45 HOOL {504.30 USD}             ',
            '        4 HOOL {504.30 USD / 2014-11-11}',
            '   9.9505 USD                           ',
            '                                        ',
            '-22473.32 CAD @ 1.10 USD                ',
            'UNKNOWN                                 ',
            '76400.203                               ',
            ], aligned_strings)

    @loader.load_doc()
    def test_align(self, entries, errors, options_map):
        """
        2014-01-01 open Expenses:Commissions

        2014-07-01 * "Something"
          Expenses:Commissions  20000 USD
          Expenses:Commissions  9.9505 USD
          Expenses:Commissions  -20009.9505 USD
        """
        dcontext = options_map['dcontext']
        oss = io.StringIO()
        printer.print_entries(entries, dcontext, file=oss)
        expected_str = textwrap.dedent("""\
        2014-01-01 open Expenses:Commissions

        2014-07-01 * "Something"
          Expenses:Commissions   20000.0000 USD
          Expenses:Commissions       9.9505 USD
          Expenses:Commissions  -20009.9505 USD
        """)
        self.assertEqual(expected_str, oss.getvalue())

    @loader.load_doc()
    def test_align_min_width_account(self, entries, errors, options_map):
        """
        2014-01-01 open Expenses:Commissions

        2014-07-01 * "Something"
          Expenses:Commissions  20000 USD
          Expenses:Commissions  9.9505 USD
          Expenses:Commissions  -20009.9505 USD
        """
        dcontext = options_map['dcontext']
        oss = io.StringIO()
        eprinter = printer.EntryPrinter(dcontext, min_width_account=40)
        oss.write(eprinter(entries[1]))
        expected_str = textwrap.dedent("""\
        2014-07-01 * "Something"
          Expenses:Commissions                       20000.0000 USD
          Expenses:Commissions                           9.9505 USD
          Expenses:Commissions                      -20009.9505 USD
        """)
        self.assertEqual(expected_str, oss.getvalue())

    @loader.load_doc()
    def test_align_with_weight(self, entries, errors, options_map):
        """
        2014-01-01 open Assets:US:Investments:HOOL
        2014-01-01 open Expenses:Commissions
        2014-01-01 open Assets:US:Investments:Cash

        2014-07-01 * "Something"
          Assets:US:Investments:HOOL          45 HOOL {504.30 USD}
          Assets:US:Investments:HOOL           4 HOOL {504.30 USD, 2014-11-11}
          Expenses:Commissions            9.9520 USD
          Assets:US:Investments:Cash   -22473.32 CAD @ 1.10 USD
        """
        self.assertFalse(errors)
        dcontext = options_map['dcontext']

        oss = io.StringIO()
        printer.print_entries(entries, dcontext, render_weights=False, file=oss)
        expected_str = ''.join([
            '2014-01-01 open Assets:US:Investments:HOOL\n',
            '2014-01-01 open Expenses:Commissions\n',
            '2014-01-01 open Assets:US:Investments:Cash\n',
            '\n',
            '2014-07-01 * "Something"\n',
            '  Assets:US:Investments:HOOL         45 HOOL {504.30 USD}            \n',
            '  Assets:US:Investments:HOOL          4 HOOL {504.30 USD, 2014-11-11}\n',
            '  Expenses:Commissions             9.95 USD                          \n',
            '  Assets:US:Investments:Cash  -22473.32 CAD @ 1.1000 USD             \n',
            ])
        self.assertEqual(expected_str, oss.getvalue())

        oss = io.StringIO()
        printer.print_entries(entries, dcontext, render_weights=True, file=oss)
        expected_str = textwrap.dedent("""\
        2014-01-01 open Assets:US:Investments:HOOL
        2014-01-01 open Expenses:Commissions
        2014-01-01 open Assets:US:Investments:Cash

        2014-07-01 * "Something"
          Assets:US:Investments:HOOL         45 HOOL {504.30 USD}              ;    22693.50 USD
          Assets:US:Investments:HOOL          4 HOOL {504.30 USD, 2014-11-11}  ;     2017.20 USD
          Expenses:Commissions             9.95 USD                            ;      9.9520 USD
          Assets:US:Investments:Cash  -22473.32 CAD @ 1.1000 USD               ; -24720.6520 USD
        """)
        self.assertEqual(expected_str, oss.getvalue())


class TestPrinterMisc(test_utils.TestCase):

    @loader.load_doc(expect_errors=True)
    def test_no_valid_account(self, entries, errors, options_map):
        """
        2000-01-01 * "Test"
          Assets:Foo

        2000-01-01 * "Test"
          Assets:Foo
          Assets:Bar
        """
        oss = io.StringIO()
        printer.print_entries(entries, file=oss)

    def test_metadata(self):
        input_string = textwrap.dedent("""

        2000-01-01 open Assets:US:Investments:Cash
          name: "Investment account"
        2000-01-01 open Assets:US:Investments:HOOL

        2000-01-02 commodity VHT
          asset-class: "Stocks"
          name: "Vanguard Health Care ETF"

        2000-01-03 * "Something"
          doc: "some-statement.pdf"
          Assets:US:Investments:Cash  -23.45 USD
            note: "No commission"
          Assets:US:Investments:HOOL    1 HOOL {23.45 USD}
            settlement: 2000-01-05

        """)
        entries, errors, options_map = loader.load_string(input_string)
        self.assertFalse(errors)
        oss = io.StringIO()
        printer.print_entries(entries, file=oss)
        self.assertLines(input_string, oss.getvalue())
