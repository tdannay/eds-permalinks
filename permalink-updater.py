'''
This script takes a csv export from EDSAdmin Holdings Manager and produces
a new csv with updated URLs that replace the old Aleph doc number with the
new FOLIO instance ID. It also generates an error log to capture URLs
that were not changed by this process.

Accompany with config.py that includes the following variables:
    filename
    tenant
    connection_url
    token
    eds_profile_id
    eds_group_id
    eds_customer_id
    eds_catalog_id
    school_code #refers to the string at the beginning of the accession number.
                #e.g. "mhf" for Mount Holyoke
'''

import csv
import requests
import config

def main():
    '''
    Read the CSV and for each URL, find the doc number, use that doc number
    to query the FOLIO API for the associated FOLIO instance ID, and then
    build a new permalink with that ID.
    '''
    updated_holding_list = []
    error_list = []

    with open(config.filename, 'r', encoding='utf-8') as eds_holding_list:
        reader = csv.DictReader(eds_holding_list)
        for holding in reader:
            try:
                doc_number = get_doc_number(holding['URL'])
            except IndexError:
                error_list.append(f"Could not find doc_number for {holding['Title']}")
                continue
            try:
                folio_id = get_folio_id(doc_number)
            except IndexError:
                error_list.append("Could not find FOLIO ID "\
                                  f"for {holding['Title']} - {doc_number}")
                continue
            holding['UserDefinedField2'] = holding['URL'] #Moves the old URL to another field for posterity
            holding['URL'] = build_permalink(folio_id)
            print('Updating ' + holding['Title'])
            updated_holding_list.append(holding)

    #Generate new CSV for upload to EDS Admin
    with open('output.csv', 'w', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames = reader.fieldnames, lineterminator = '\n')
        writer.writeheader()
        writer.writerows(updated_holding_list)

    #Generate error log
    with open('error_log.txt', 'w') as error_log:
        for error in error_list:
            error_log.write(error + '\n')

def get_doc_number(url):
    '''
    Parameters
    ----------
    url : string
        URL from list exported from EDS Admin

    Raises
    ------
    IndexError
        If the doc number is not present in the URL, raises an error that
        will be handled in main() by adding an entry to the error log and
        skipping to the next row of the CSV

    Returns
    -------
    string
        The doc number that appears after 'doc_number=' in the URL, if found
    '''
    #Extract Aleph bib number from URL
    doc_num_index = url.find("doc_number=")
    if doc_num_index == -1:
        raise IndexError("doc_number not found")
    return url[doc_num_index + len("doc_number="):]

def get_folio_id(doc_number):
    '''
    Parameters
    ----------
    doc_number : string
        The doc number that had been extracted from the URL via get_doc_number()

    Returns
    -------
    folio_id : string
        The FOLIO ID acquired via the FOLIO API, based on the given doc number.
        Will throw IndexError if the doc number is not found in API GET call.
    '''
    #Make API call to get FOLIO ID number based on Aleph doc number
    url_ext = 'inventory/instances'
    query = '?query=identifiers=' + doc_number
    headers = {'Content-Type': 'application/json',
               'x-okapi-tenant': config.tenant, 'x-okapi-token': config.token}
    request = requests.get(config.connection_url + url_ext + query, headers=headers)
    request_body = request.json()
    folio_id = request_body['instances'][0]['id']
    return folio_id

def build_permalink(folio_id):
    '''
    Parameters
    ----------
    folio_id : string
        The FOLIO ID that had been acquired via get_folio_id()

    Returns
    -------
    string
        The updated permalink URL
    '''
    cleaned_folio_id = str(folio_id.replace('-','.'))
    new_url = 'https://search.ebscohost.com/login.aspx?'\
    'authtype=ip,guest&'\
    f'custid={config.eds_customer_id}&'\
    f'groupid={config.eds_group_id}&'\
    f'profid={config.eds_profile_id}&'\
    f'db={config.eds_catalog_id}&'\
    'direct=true&'\
    'site=eds-live&'\
    'scope=site&'\
    f'AN={config.school_code}.'\
    f'oai.edge.fivecolleges.folio.ebsco.com.fs00001006.{cleaned_folio_id}'\

    return new_url

if __name__ == '__main__':
    main()
