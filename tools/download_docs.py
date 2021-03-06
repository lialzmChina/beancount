#!/usr/bin/python3
"""Download all the Beancount docs from Google Drive and bake a nice PDF with it.
"""
__copyright__ = "Copyright (C) 2015-2016  Martin Blais"
__license__ = "GNU GPLv2"

import argparse
import datetime
import logging
import os
import shutil
import tempfile
import subprocess
import re
from os import path

from apiclient import discovery
import httplib2
from oauth2client import service_account


def find_index_document(service):
    """Find the the document of Beancount index.

    Args:
      service: An API client object with Google Drive scope.
    Returns:
      A string, the document id.
    """
    query = "name = 'Beancount - Index'"
    listing = service.files().list(q=query).execute()
    files = listing['files']
    if len(files) != 1:
        raise ValueError("Could not find the index file: "
                         "{} files matched".format(len(files)))
    for file in files:
        return file['id']


def enumerate_linked_documents(service, indexid):
    """Given a document id, enumerate the links within it.

    Args:
      service: An API client object with Google Drive scope.
      indexid: A string, a document id.
    Returns:
      A list of link strins.
    """
    doc = service.files().export(fileId=indexid,
                                 mimeType='text/html').execute()
    contents = doc.decode('utf8')
    docids = [indexid]
    for match in re.finditer('https?://docs.google.com/document/d/([^/";&]+)', contents):
        docid = match.group(1)
        if docid not in docids:
            docids.append(docid)
    return docids


def download_docs(service, docids, outdir, mime_type):
    """Download all the Beancount documents to a temporary directory.

    Args:
      service: A googleapiclient Service stub.
      docids: A list of string, the document ids to download.
      outdir: A string, the name of the directory where to store the filess.
      mime_type: A string, the MIME format of the requested documents.
    Returns:
      A list of string, the names of the downloaded files.
    """
    extension = {
        'application/pdf': 'pdf',
        'application/vnd.oasis.opendocument.text': 'odt',
    }[mime_type]

    filenames = []
    for index, docid in enumerate(docids, 1):
        # Get the document metadata.
        metadata = service.files().get(fileId=docid).execute()
        name = metadata['name']

        # Retrieve to a file.
        clean_name = re.sub('_-_', '-',
                            re.sub('_+', '_',
                                   re.sub('[^A-Za-z0-9=-]', '_', name)))
        filename = path.join(outdir, '{}.{}'.format(clean_name, extension))
        if path.exists(filename):
            logging.info('File "{}" already downloaded'.format(filename))
        else:
            logging.info('Exporting "{}" ({}) to {}'.format(name, docid, filename))
            with open(filename, 'wb') as outfile:
                exported = service.files().export(fileId=docid,
                                                  mimeType=mime_type).execute()
                outfile.write(exported)

        # Check if the downloaded succeeded.
        if path.getsize(filename) == 0:
            logging.error("Invalid download, skipping file for '{}'.".format(docid))
            continue
        filenames.append(filename)

    return filenames


def convert_pdf(filenames, output):
    """Process downloaded PDF files.

    Args:
      filenames: A list of filename strings.
      output_filename: A string, the name of the output file.
    """
    collate_pdf_filenames(filenames, output)


def collate_pdf_filenames(filenames, output_filename):
    """Combine the list of PDF filenames together into a single file.

    Args:
      filenames: A list of filename strings.
      output_filename: A string, the name of the output file.
    Raises:
      IOError: If we could not produce the merged filename.
    """
    command = ['pdftk'] + filenames + ['cat', 'output', output_filename]
    try:
        pipe = subprocess.Popen(command, shell=False)
        pipe.communicate()
    except FileNotFoundError as exc:
        raise SystemExit('pdftk is probably not installed: {}'.format(exc))
    if pipe.returncode != 0:
        raise IOError("Could not produce output '{}'".format(output_filename))


SERVICE_ACCOUNT_FILE = path.join(os.environ['HOME'],
                                 '.google-apis-service-account.json')

def get_auth_via_service_account(scopes):
    """Get an authenticated http object via a service account.

    Args:
      scopes: A string or a list of strings, the scopes to get credentials for.
    Returns:
      A pair or (credentials, http) objects, where 'http' is an authenticated
      http client object, from which you can use the Google APIs.
    """
    credentials = service_account.ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, scopes)
    http = httplib2.Http()
    credentials.authorize(http)
    return credentials, http


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())

    conversion_map = {
        'pdf': ('application/pdf', convert_pdf),
        'odt': ('application/vnd.oasis.opendocument.text', None),
    }
    parser.add_argument('conversion', action='store',
                        default='pdf', choices=list(conversion_map.keys()),
                        help="The format of the desired output.")

    #default_path = path.abspath(datetime.date.today().strftime('beancount.%Y-%m-%d.pdf'))
    parser.add_argument('output', action='store',
                        default=None,
                        help="Where to write out the output files")

    args = parser.parse_args()

    # Connect, with authentication.
    scopes = ['https://www.googleapis.com/auth/drive']
    _, http = get_auth_via_service_account(scopes)
    service = discovery.build('drive', 'v3', http=http)

    # Get the ids of the documents listed in the index page.
    indexid = find_index_document(service)
    assert indexid
    docids = enumerate_linked_documents(service, indexid)

    # Figure out which format to download.
    mime_type, convert = conversion_map[args.conversion]

    # Allocate a temporary directory.
    os.makedirs(args.output, exist_ok=True)

    # Download the docs.
    filenames = download_docs(service, docids, args.output, mime_type)

    # Post-process the files.
    if convert is not None:
        convert(filenames, args.output)

    logging.info("Output produced in {}".format(args.output))


if __name__ == '__main__':
    main()
