"""Print out a list of current holdings, relative or absolute.

This is to share my portfolio with others, or to compute its daily changes.
"""
import argparse
import sys
import textwrap
import io
import logging

from beancount import loader
from beancount.ops import validation
from beancount.reports import rselect
from beancount.reports import table
from beancount.utils import file_utils
from beancount.utils import misc_utils


def get_list_report_string(only_report=None):
    """Return a formatted string for the list of supported reports.

    Args:
      only_report: A string, the name of a single report to produce the help
        for. If not specified, list all the available reports.
    Returns:
      A help string, or None, if 'only_report' was provided and is not a valid
      report name.
    """
    oss = io.StringIO()
    if not only_report:
        oss.write("Available Reports:\n")
    else:
        oss.write("Report:\n")
    num_reports = 0
    for name, args, rclass, formats, description in rselect.get_report_types():
        if only_report and name != only_report:
            continue
        synopsys = ('{}:{}'.format(name, ','.join(arg.upper() for arg in args))
                    if args
                    else name)
        oss.write("  '{}' [{}]:\n".format(synopsys, ', '.join(formats)))
        oss.write(textwrap.fill(description,
                                initial_indent="    ",
                                subsequent_indent="    "
                            ))
        oss.write("\n\n")
        num_reports += 1
    if not num_reports:
        return None
    return oss.getvalue()


class ListReportsAction(argparse.Action):
    """An argparse action that just prints the list of reports and exits."""

    def __call__(self, parser, namespace, values, option_string=None):
        help_string = get_list_report_string(values)
        if values and help_string is None:
            sys.stderr.write("Error: Invalid report name '{}'\n".format(values))
            sys.exit(1)
        else:
            print(help_string)
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('--help-reports', '--list-reports',
                        nargs='?',
                        default=None,
                        action=ListReportsAction,
                        help="Special: Print the full list of supported reports and exit.")

    parser.add_argument('filename',
                        help='The Beancout input filename to load.')

    parser.add_argument('report', nargs='?',
                        help='Name/specification of the desired report.')

    parser.add_argument('-f', '--format', default=None,
                        choices=['text', 'csv', 'html', 'beancount'],
                        help="Output format.")

    parser.add_argument('-o', '--output', action='store',
                        help=("Output filename. If not specified, the output goes "
                              "to stdout. The filename is inspected to select a "
                              "sensible default format, if one is not requested."))

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print timings.')

    opts = parser.parse_args()

    # Handle special commands.
    if opts.help_reports:
        print(get_list_report_string())
        return

    # Open output file and guess file format.
    outfile = open(opts.output, 'w') if opts.output else sys.stdout
    opts.format = opts.format or file_utils.guess_file_format(opts.output)

    # Dispatch on which report to generate.
    report_function = rselect.get_report_generator(opts.report, opts.format)
    if report_function is None:
        parser.error("Unknown report.")
    is_check = report_function is rselect.report_validate

    # Force hardcore validations, just for check.
    if is_check:
        validation.VALIDATIONS.extend(validation.HARDCORE_VALIDATIONS)

    if opts.verbose:
        logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')

    # Parse the input file.
    with misc_utils.log_time('beancount.loader (total)', logging.info):
        entries, errors, options_map = loader.load(opts.filename,
                                                   log_timings=logging.info,
                                                   log_errors=sys.stderr)

    # Create holdings list.
    result = report_function(entries, options_map)

    try:
        if isinstance(result, str):
            outfile.write(result)

        elif isinstance(result, table.TableReport):
            # Create the table report.
            table.render_table(result, outfile, opts.format)
    except NotImplementedError as exc:
        print(exc)
        sys.exit(1)


if __name__ == '__main__':
    main()
