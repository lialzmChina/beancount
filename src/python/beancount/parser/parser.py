"""Beancount syntax parser.

IMPORTANT: The parser (and its grammar builder) produces "incomplete"
Transaction objects. This means that some of the data can be found missing from
the output of the parser and some of the data types vary slightly. Missing
components are replaced not by None, but by a special constant 'NA' which helps
diagnose problems if a user inadvertently attempts to work on an incomplete
posting instead of a complete one. Those incomplete entries are then run through
the "booking" routines which do two things simultaneously:

1. They find matching lots for reducing inventory positions, and
2. They interpolate missing numbers.

In doing so they normalize the entries to "complete" entries by converting a
position/lot's "cost" attribute from a CostSpec to a Cost. A Cost is similar to
an Amount in that it shares "number" and "currency" attributes, but also has a
label and a lot date. A CostSpec is similar to a Cost, but has all optional
data; it consists in a specification for matching against a particular inventory
lot.

Other parts of a posting may also be missing, not just parts of the cost.
Leaving out some parts of the input is used to invoke interpolation, to tell
Beancount to automatically compute the missing numbers (if possible).

Missing components will be set to the special value
"beancount.core.number.MISSING" until inventory booking and number interpolation
has been completed. The "MISSING" value should never appear in completed, loaded
transaction postings.

For instance, all of the units may be missing:

  INPUT: Assets:Account
  posting.position.units = MISSING

Or just the number of the units:

  INPUT: Assets:Account                    USD
  posting.position.units = Amount(MISSING, "USD")

You must always specify the currency.

If a price annotation is simply absent, it appears as None:

  INPUT: Assets:Account                 2 MXN
  posting.price = None

However, you may indicate that there is a price but have Beancount compute it
automatically:

  INPUT: Assets:Account                 2 MXN @
  posting.position.price = Amount(MISSING, MISSING)

Indicating the conversion currency is also possible (and recommended):

  INPUT: Assets:Account                 2 MXN @ USD
  posting.position.price = Amount(MISSING, "USD")

If a cost specification is provided, a "cost" attribute it set but it does not
refer to a Cost instance (as in complete entries) but rather to a CostSpec
instance. Some of the fields of a CostSpec may be MISSING if they were not
specified in the input. For exammple:

  INPUT: Assets:Account  1 GOOG {100 # 5 USD}
  posting.position.cost = CostSpec(Decimal("100"), Decimal("5"), "USD", None, None, False))

Note how we never consider the label of date override to be MISSING; this is
because those inputs are optional: A missing label is simply left unset in the
computed Cost, and a missing date override uses the date of the transaction
that contains the posting.

You can indicate that there is a total number to be filled in like this:

  INPUT: Assets:Account  1 GOOG {100 # USD}
  posting.position.cost = CostSpec(Decimal("100"), MISSING, "USD", None, None, False))

This is in contrast to the total value simple not being used:

  INPUT: Assets:Account  1 GOOG {100 USD}
  posting.position.cost = CostSpec(Decimal("100"), None, "USD", None, None, False))

Both per-unit and total numbers may be omitted as well, in which case, only the
number-per-unit portion of the CostSpec will appear as MISSING:

  INPUT: Assets:Account  1 GOOG {USD}
  posting.position.cost = CostSpec(MISSING, None, "USD", None, None, False))

And furthermore, all the cost basis may be missing:

  INPUT: Assets:Account  1 GOOG {}
  posting.position.cost = CostSpec(MISSING, None, MISSING, None, None, False))

If you ask for the lots to be merged, you get this:

  INPUT: Assets:Account  1 GOOG {*}
  posting.position.cost = CostSpec(MISSING, None, MISSING, None, None, True))

The numbers have to be computed by Beancount, so we output this with MISSING
values.

Of course, you can provide only the non-basis informations, like just the date
or label:

  INPUT: Assets:Account  1 GOOG {2015-09-21}
  posting.position.cost = CostSpec(MISSING, None, MISSING, date(2015, 9, 21), None, True)

See the test beancount.parser.grammar_test.TestIncompleteInputs for examples and
corresponding expected values.
"""
__author__ = "Martin Blais <blais@furius.ca>"

import functools
import inspect
import textwrap
import io
import warnings
from os import path

from beancount.parser import _parser
from beancount.parser import grammar
from beancount.parser import printer
from beancount.parser import hashsrc
from beancount.core import data
from beancount.core.number import MISSING

from beancount.parser.grammar import ParserError
from beancount.parser.grammar import ParserSyntaxError
from beancount.parser.grammar import DeprecatedError
# pylint: disable=unused-import
ParserError, ParserSyntaxError, DeprecatedError # pyflakes


# When importing the module, always check that the compiled source matched the
# installed source.
hashsrc.check_parser_source_files()


def is_posting_incomplete(posting):
    """Detect the presence of any elided amounts in a Posting.

    If any of the possible amounts are missing, this returns True.

    Args:
      entries: A directive.
    Returns:
      A boolean, true if there are some missing portions of any postings found.
    """
    pos = posting.position
    if (pos is None or pos is MISSING):
        return True
    units = pos.units
    if (units.number is MISSING or
        units.currency is MISSING):
        return True
    price = posting.price
    if (price is MISSING or
        price is not None and (price.number is MISSING or
                               price.currency is MISSING)):
        return True
    cost = pos.cost
    if cost is not None and (cost.number_per is MISSING or
                             cost.number_total is MISSING or
                             cost.currency is MISSING):
        return True
    return False


def is_entry_incomplete(entry):
    """Detect the presence of elided amounts in Transactions.

    Args:
      entries: A directive.
    Returns:
      A boolean, true if there are some missing portions of any postings found.
    """
    if isinstance(entry, data.Transaction):
        if any(is_posting_incomplete(posting) for posting in entry.postings):
            return True
    return False


def parse_file(filename, **kw):
    """Parse a beancount input file and return Ledger with the list of
    transactions and tree of accounts.

    Args:
      filename: the name of the file to be parsed.
      kw: a dict of keywords to be applied to the C parser.
    Returns:
      A tuple of (
        list of entries parsed in the file,
        list of errors that were encountered during parsing, and
        a dict of the option values that were parsed from the file.)
    """
    abs_filename = path.abspath(filename) if filename else None
    builder = grammar.Builder(abs_filename)
    _parser.parse_file(filename, builder, **kw)
    return builder.finalize()

# Alias, for compatibility.
# pylint: disable=invalid-name
parse = parse_file


def parse_string(string, **kw):
    """Parse a beancount input file and return Ledger with the list of
    transactions and tree of accounts.

    Args:
      string: a str, the contents to be parsed instead of a file's.
      **kw: See parse.c. This function parses out 'dedent' which removes
        whitespace from the front of the text (default is False).
    Return:
      Same as the output of parse_file().
    """
    if kw.pop('dedent', None):
        string = textwrap.dedent(string)
    builder = grammar.Builder(None)
    _parser.parse_string(string, builder, **kw)
    builder.options['filename'] = '<string>'
    return builder.finalize()


# FIXME: Deprecate this eventually.
def parsedoc(*args, **kw):
    warnings.warn("parsedoc() is obsolete; use parse_doc() instead.")
    return parse_doc(*args, **kw)

def parse_doc(expect_errors=False, allow_incomplete=False):
    """Factory of decorators that parse the function's docstring as an argument.

    Note that the decorators thus generated only run the parser on the tests,
    not the loader, so is no validation, balance checks, nor plugins applied to
    the parsed text.

    Args:
      expect_errors: A boolean or None, with the following semantics,
        True: Expect errors and fail if there are none.
        False: Expect no errors and fail if there are some.
        None: Do nothing, no check.
      allow_incomplete: A boolean, if true, allow incomplete input. Otherwise
        barf if the input would require interpolation. The default value is set
        not to allow it because we want to minimize the features tests depend on.
    Returns:
      A decorator for test functions.
    """
    def decorator(fun):
        """A decorator that parses the function's docstring as an argument.

        Args:
          fun: the function object to be decorated.
        Returns:
          A decorated test function.
        """
        filename = inspect.getfile(fun)
        lines, lineno = inspect.getsourcelines(fun)

        # decorator line + function definition line (I realize this is largely
        # imperfect, but it's only for reporting in our tests) - empty first line
        # stripped away.
        lineno += 1

        @functools.wraps(fun)
        def wrapper(self):
            assert fun.__doc__ is not None, (
                "You need to insert a docstring on {}".format(fun.__name__))
            entries, errors, options_map = parse_string(fun.__doc__,
                                                        report_filename=filename,
                                                        report_firstline=lineno,
                                                        dedent=True)

            if not allow_incomplete and any(is_entry_incomplete(entry)
                                            for entry in entries):
                self.fail("parse_doc() may not use interpolation.")

            if expect_errors is not None:
                if expect_errors is False and errors:
                    oss = io.StringIO()
                    printer.print_errors(errors, file=oss)
                    self.fail("Unexpected errors found:\n{}".format(oss.getvalue()))
                elif expect_errors is True and not errors:
                    self.fail("Expected errors, none found:")

            return fun(self, entries, errors, options_map)

        wrapper.__input__ = wrapper.__doc__
        wrapper.__doc__ = None
        return wrapper

    return decorator
