"""Load an input file: open the file and parse it, pad, check and validate it.

This file provides convenience routines that do all that's necessary to obtain a
list of entries ready for realization and working with them. This is the most
common entry point.
"""
import os
import re
import datetime
from os import path

from beancount import utils
from beancount.parser import parser
from beancount.parser import documents
from beancount.core.data import Document
from beancount.core import data
from beancount.core import realization
from beancount.core import validation
from beancount.core import prices


def load(filename,
         add_unrealized_gains=False,
         do_print_errors=False,
         quiet=False):
    """Parse the input file, pad the entries, check and validate it.
    This also prints out the error messages."""

    # Parse the input file.
    with utils.print_time('parse', quiet):
        entries, parse_errors, options = parser.parse(filename)

    # Pad the resulting entries (create synthetic Pad entries to balance checks
    # where desired).
    with utils.print_time('pad', quiet):
        entries, pad_errors = realization.pad(entries)

    with utils.print_time('check', quiet):
        entries, check_errors = realization.check(entries)

    # Process the document entries and find documents automatically.
    with utils.print_time('documents', quiet):
        entries, doc_errors = documents.process_documents(entries,
                                                          filename,
                                                          options['documents'])

    # Validate the list of entries.
    with utils.print_time('validate', quiet):
        valid_errors = validation.validate(entries)

    # Add unrealized gains.
    with utils.print_time('unrealized', quiet):
        entries = prices.unrealized_gains(entries, options['account_unrealized'])

    # Print out the list of errors.
    errors = parse_errors + pad_errors + check_errors + valid_errors + doc_errors
    if do_print_errors:
        data.print_errors(errors)

    return entries, errors, options