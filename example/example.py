import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from src.QueryWrapper import QueryWrapper
from src.Question import Question

ont = './ontology_mapping.json'
map_xml = './xml_mapping.json'
xml = './question1.xml'
endpoint = 'http://gaiadev01.isi.edu:3030/dryrun_all/query'

question = Question(ont, xml)
query_wrapper = QueryWrapper(endpoint, map_xml)

print(query_wrapper.ask(question))
