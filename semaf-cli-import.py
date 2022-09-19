from xml.dom import minidom
import os
import tempfile
#from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json

from requests.structures import CaseInsensitiveDict

from SchemaLOD import Schema, GraphBuilder
from SemafCLI import SemafUtils
from config import default_crosswalks_location, crosswalks_location, cbs_default_crosswalks
from rdflib import Graph, URIRef, Literal, BNode, plugin, Namespace
from rdflib.serializer import Serializer
from rdflib.namespace import RDF, RDFS
#from config import cmdifile, ROOT, DATAVERSE_ID, API_TOKEN, schemaURL, cv_server, cwfile
from config import *
from Semaf import Semaf
from jGraph import jGraph
import sys
import re
import requests
from datetime import datetime
from pathlib import Path


def retrieve_license(license_string):
    dataset_lic = ''
    if re.search(r'creativecommons', license_string):
        if re.search(r'/by/4\.0', license_string):
            dataset_lic = "CC BY 4.0"
        elif re.search(r'/by-nc/4\.0', license_string):
            dataset_lic = "CC BY-NC 4.0"
        elif re.search(r'/by-sa/4\.0', license_string):
            dataset_lic = "CC BY-SA 4.0"
        elif re.search(r'/by-nc-sa/4\.0', license_string):
            dataset_lic = "CC BY-NC-SA 4.0"
        elif re.search(r'zero/1\.0', license_string):
            dataset_lic = "CC0 1.0"
    elif re.search(r'DANSLicence', license_string):
        dataset_lic = "DANS Licence"
    return dataset_lic


def is_lower_level_liss_study(metadata):
    title = metadata['datasetVersion']['metadataBlocks']['citation']['fields'][0]['value']
    print("Title is", title)
    square_bracket_amount = title.count('>')
    if square_bracket_amount == 0:
        print('no square brackets')
        return False, title
    if square_bracket_amount == 1:
        liss_match = re.search(r'L[iI]SS [Pp]anel', title)
        immigrant_match = re.search(r'Immigrant [Pp]anel', title)
        if liss_match or immigrant_match:
            if liss_match:
                print("Matched on liss panel")
                return False, title
            if immigrant_match:
                print("Matched on immigrant panel")
                return False, title
        else:
            return True, title
    if square_bracket_amount >= 2:
        return True, title


outputdir = tempfile.mkdtemp(suffix=None, prefix="semafoutput")

UPLOAD = False
if len(sys.argv) > 1:
    cmdifile = sys.argv[1]
    print(cmdifile)
    output_file_name = os.path.basename(cmdifile)
    if len(sys.argv) > 2:
        UPLOAD = True
else:
    print("XML file required as input parameter")
    exit()
    #cmdifile = '0b01e4108004e49d_INV_REG_REPARATIE_CONSUMENTENARTIKELEN_HANDEL_2008-01-01.dsc'


# Load citation block
Path(outputdir + "/citation").mkdir(parents=False, exist_ok=True)
semafcli = SemafUtils(cbs_default_crosswalks, crosswalks_location)
semafcli.set_nt_filename(outputdir + "/citation/" + "%s.nt" % output_file_name)
semafcli.set_semaf_filename(outputdir + "/citation/" + "%s.json" % output_file_name)
semafcli.set_semaf_filename_orig(outputdir + "/citation/" + "%s-orig.json" % output_file_name)
semafcli.set_schema(schema_name='citation', schema_URL=schemaURL)
semafcli.transformation(cmdifile, UPLOAD=UPLOAD)
metadata = semafcli.cmdigraph.dataset

# Load all other blocks
for schema_name in schemes:    
    Path(outputdir + "/" + schema_name).mkdir(parents=False, exist_ok=True)
    custom_semafcli = SemafUtils(cbs_default_crosswalks, crosswalks_location)
    custom_semafcli.set_nt_filename(outputdir + "/" + schema_name +"/" + "%s.nt" % output_file_name)
    custom_semafcli.set_semaf_filename(outputdir + "/" + schema_name +"/" + "%s.json" % output_file_name)
    custom_semafcli.set_semaf_filename_orig(outputdir + "/" + schema_name +"/" + "%s-orig.json" % output_file_name)
    custom_semafcli.set_schema(schema_name=schema_name, schema_URL=schemes[schema_name])
    custom_semafcli.transformation(cmdifile, UPLOAD=UPLOAD)
    if custom_semafcli.cmdigraph.dataset:
        metadata['datasetVersion']['metadataBlocks'][schema_name] = custom_semafcli.cmdigraph.dataset[schema_name]

semafcli.set_deposit_type('original')
semafcli.set_dataverse(ROOT, DATAVERSE_ID, API_TOKEN)

# EASY licensing
if DATAVERSE_ID == 'dans-easy':
    license_string = next(filter(lambda x: x['mapping'] == 'license', semafcli.cmdigraph.exportrecords), 0)
    if license_string:
        dataset_license = retrieve_license(license_string['value'])
        metadata['datasetVersion']['license'] = dataset_license
        print(dataset_license)

if DATAVERSE_ID == 'cbs':
    metadata['datasetVersion']['license'] = 'DANS MA KA Licence'

if DATAVERSE_ID == 'liss_dc':
    metadata['datasetVersion']['license'] = 'DANS MA KI Licence'

metadatafile = outputdir + output_file_name + "-output.json"
with open(metadatafile, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=4)
if DATAVERSE_ID != 'liss_dc' or is_lower_level_liss_study(metadata)[0] is False:
    #if DATAVERSE_ID == 'cbs':
    #    json_string = json.dumps(metadata)
    #    url = "http://0.0.0.0:8566/submit-to-datacite"

    #    headers = CaseInsensitiveDict()
#         headers = {
#             'Content-Type': 'application/json',
#             'Authorization': 'Bearer @km1-10122004-lamA',
#             'Content-Type': 'application/x-www-form-urlencoded',
#         }
#         resp = requests.post(url, headers=headers, data=json_string)
#         doi_pid = resp.text.replace('"', '').replace('{', '').replace('}', '')

    if DATAVERSE_ID == 'liss_dc' or DATAVERSE_ID == 'dans-easy':
        pid_field = next(filter(lambda x: x['mapping'] == 'doi' and 'doi' in x['value'], semafcli.cmdigraph.exportrecords))
        doi_pid = 'doi:' + pid_field['value'].split("/", 3)[3]

    status = semafcli.dataset_upload(metadatafile, doi_pid)
    print(status)
