import requests
import json
import os
from shutil import copyfile
import argparse
import sys
import time

def ensure_that_domain_file_exists_and_is_valid_json():
    '''
    Make sure that we pass EAL nicely formatted data and that the file exists.
    '''
    file_exists = os.path.exists("blacklists/domains.json")
    if not file_exists:
        create_file = open("blacklists/domains.json", 'w')
        create_file.close()
    try:
        domains = open("blacklists/domains.json", 'r')
        contents = domains.read()
        domains.close()
        json_contents = json.loads(contents)
        return json_contents
    except:
        #Create a backup of the current domains file, then place and empty
        #json file there.
        print ('''
        The domains file was not json compliant, making a backup and then
        replacing the domain file with empty json array.
        ''')
        copyfile("blacklists/domains.json", "blacklists/domains.json.bak")
        create_file = open("blacklists/domains.json", 'w')
        create_file.write("[]\n")
        create_file.close()
        return False

def preprocess_domain(domain):
    '''
    Tidy up the domain for processing.

    :param domain: domain to clean
    :return: cleaned up domain
    '''
    #Lets ensure that it's in an nice string format for idna

    try:
        domain = domain.strip("*.").strip(".").strip().lower().strip("www.")
        domain = domain.encode("idna").decode("utf-8")
    except Exception as e:
        print (e)
        print ("[x] Error converting domain {} to idna, skipping adding...".format(domain))
        return False

    return domain

def get_existing_blacklists():
    '''
    Fetch the existing EAL blacklist and ensure that we do not duplicate entries.
    '''
    try:
        r = requests.get("https://api.infura.io/v2/blacklist")
        blacklist = r.json()['blacklist']
        return set(blacklist)
    except:
        print ("[x] Error fetching blacklist, please ensure that you are able to reach the EAL endpoint.")
        return False

def extend_json_array_file(filename, contents):
    f = open(filename, 'r')
    old_contents = f.read()
    f.close()
    array = set(json.loads(old_contents) + list(contents))
    f = open(filename, 'w')
    f.write(json.dumps(list(array), indent=4, sort_keys=True))
    f.close()

def extend_json_dict_file(filename, contents):
    try:
        f = open(filename, 'r')
        old_contents = f.read()
        f.close()
    except:
        old_contents = "{}"
    combined_dict = {**json.loads(old_contents), **contents}
    f = open(filename, 'w')
    f.write(json.dumps(combined_dict,indent=4, sort_keys=True))
    f.close()

def load_file():
    ensure_that_domain_file_exists_and_is_valid_json()
    f = open(args.blacklist_file, 'r')
    contents = f.readlines()
    f.close()
    if len(contents) == 0:
        print ("[x] Error - the blacklist file provided is empty")
        sys.exit()


    blacklist = get_existing_blacklists()
    print ("[+] Currently {} entries in EAL blacklist...".format(len(blacklist)))
    if not blacklist:
        sys.exit()

    #New entries set
    new_entries = set()

    #Let's store an internal record of when we reported this. We can also used
    #this date to clean out old domains from the blacklist.
    internal_record = {}

    #Loop through each of the entries
    for entry in contents:
        clean_entry = preprocess_domain(entry)
        if not clean_entry:
            continue
        if entry in blacklist:
            print ("\t[-] Found {} but it is already present in the blacklist.")
            continue
        print ("\t[+] Added {}".format(clean_entry))
        new_entries.add(clean_entry)
        internal_record[clean_entry] = str(time.time())
    print ("[+] Found {} new entries...".format(len(new_entries)))

    extend_json_array_file("blacklists/domains.json", new_entries)
    extend_json_dict_file("internal_domain_tracking.json", internal_record)

    ensure_that_domain_file_exists_and_is_valid_json()

parser = argparse.ArgumentParser(description='Tool for storing and commiting blacklist to git.')
parser.add_argument('--blacklist-file', metavar='N',type=str,nargs="?", const="blacklist", required=True,
                    help='The new blacklist file to add')
args = parser.parse_args()

if __name__ == "__main__":
    load_file()
