#!/usr/bin/python3

from xml.dom import minidom
from CLARIAH_CMDI.xml2dict.processor import CMDI # load, xmldom2dict
import json
from config import cmdifile
from Semaf import Semaf
from jGraph import jGraph
import sys

sm = Semaf()
cmdifile = sys.argv[1:] 
s = sm.loadcmdi(cmdifile[0])

cmdigraph = jGraph(sm.json, "https://dataverse.org/schema/cmdi")
cmdigraph.rotate(cmdigraph.context, False)
cmdigraph.g.serialize(format='json-ld', destination='/tmp/Xcmdi.jsonld')
cmdigraph.g.serialize(format='n3', destination='/tmp/Xcmdi.nt')

