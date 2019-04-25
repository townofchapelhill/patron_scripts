# import libraries
import requests
import secrets
import csv
import json
import jsonpickle
import re
import os
from datetime import datetime
from datetime import date

# Object used to store data to aid in transformation
class Patron(object):
    def __init__(self, pType=None, strAddress=None, city=None, state=None, zip=None, expDate=None, bDate=None):
        self.pType = ''
        self.strAddress = ''
        self.city = ''
        self.state = ''
        self.zip = ''
        self.expDate = ''
        self.bDate = ''

# GETs all patron records from Sierra
def get_all_patrons():
    all_patrons = []
    iterator = 0
    active_patrons_token = get_token()

    # while loop to iterate through database, GET-ing 2000 records per query
    while True:
        get_header_text = {"Authorization": "Bearer " + active_patrons_token}
        get_request = requests.get("https://catalog.chapelhillpubliclibrary.org/iii/sierra-api/v5/patrons?offset=" + str(iterator) + "&limit=2000&fields=patronType,addresses,expirationDate,birthDate&deleted=false", headers=get_header_text)
        data = json.loads(get_request.text)
        try:
            for i in data['entries']:
                all_patrons.append(i)
        except:
            parse_data(all_patrons)
            break

# Function to parse and transform retrieved data as necessary
def parse_data(all_patrons):
    parsed_patrons = []
    for entry in all_patrons:
        # create new instance of "Patron" object to hold info from each record
        new_patron = Patron()
        new_patron.pType = entry['patronType']
        # try/catch prevents script failure from records with missing data
        try:
            new_patron.expDate = entry['expirationDate']
            new_patron.bDate = entry['birthDate']
            # address must be split into seperate columns to satisfy Open Data Geo-processors
            split_address = entry['addresses'][0]['lines'][1].split(' ')
            new_patron.strAddress = entry['addresses'][0]['lines'][0]
            # Conditional to handle "split_address" list differences caused by city name
            if split_address[0] == 'CHAPEL':
                city = split_address[0] + ' ' + split_address[1]
                new_patron.city = city
                new_patron.state = split_address[2]
                new_patron.zip = split_address[3]
            else:
                new_patron.city = split_address[0]
                new_patron.state = split_address[1]
                new_patron.zip = split_address[2]
        except:
            pass
        # store "Patron" as a dictionary
        parsed_patrons.append(new_patron.__dict__)
    
    # transforms expDate and bDate to requested values
    for patron in parsed_patrons:
        today = date.today()
        try:
            bYear = patron['bDate'][0:4]
            age = int(today.year) - int(bYear)
            if age >= 18:
                patron['bDate'] = "Adult"
            else:
                patron['bDate'] = "Juvenile"
        except:
            continue
        
        expYear = patron['expDate'][0:4]
        active = int(expYear) - int(today.year)
        if active <= 3:
            patron["expDate"] = "Active"
        else:
            patron["expDate"] = "Inactive"
    
    # call next function, pass "parsed_patrons"
    write_csv(parsed_patrons)

# writes the final csv
def write_csv(parsed_patrons):
    with open("all_patrons_new.csv", "w+") as update_patrons:
        fieldnames = parsed_patrons[0].keys()
        csv_writer = csv.DictWriter(update_patrons, fieldnames=fieldnames, extrasaction='ignore', delimiter=',')
        
        if os.stat('all_patrons_new.csv').st_size == 0:
            csv_writer.writeheader()
        
        for entry in parsed_patrons:
            if entry['state'] != 'NC':
                continue
            elif entry['zip'] == '':
                continue
            else:
                csv_writer.writerow(entry)

# requests access token from Sierra each time it's called
def get_token():
    url = "https://catalog.chapelhillpubliclibrary.org/iii/sierra-api/v5/token"

    # Get the API key from secrets file
    header = {"Authorization": "Basic " + str(secrets.sierra_api_2), "Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, headers=header)
    json_response = json.loads(response.text)
    # Create var to hold the response data
    active_patrons_token = json_response["access_token"]
    return active_patrons_token

# begin script
get_all_patrons()