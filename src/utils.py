from SPARQLWrapper import SPARQLWrapper
import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

ENDPOINT = 'http://gaiadev01.isi.edu:3030/latest_rpi_en/query'

prefix = {
    "aida": "https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/InterchangeOntology#",
    "ldcOnt": "https://tac.nist.gov/tracks/SM-KBP/2018/ontologies/SeedlingOntology#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
}

PREFIX = '\n'.join(['PREFIX %s: <%s>' % (k, v) for k, v in prefix.items()])


def select_query(query_string):
    sw = SPARQLWrapper(ENDPOINT)
    sw.setQuery(PREFIX + query_string)
    sw.setReturnFormat('json')
    return sw.query().convert()['results']['bindings']


def aug_dict_list(target_dict, key1, key2, value_to_append):
    if key1 in target_dict:
        if key2 in target_dict[key1]:
            target_dict[key1][key2].append(value_to_append)
        else:
            target_dict[key1][key2] = [value_to_append]
    else:
        target_dict[key1] = {key2: [value_to_append]}


# TODO: where to put confidence, in the sample response, confidence is of a node not of a single justification span

def query_text_justification(uri, res):
    q = '''
    SELECT DISTINCT ?doceid ?start ?end ?confidence 
    WHERE {
        <%s> aida:justifiedBy ?j .
        ?j a aida:TextJustification ;
            aida:source ?doceid ;
            aida:startOffset ?start ;
            aida:endOffsetInclusive ?end ;
            aida:confidence ?conf .
        ?conf aida:confidenceValue ?confidence .
    }
    ''' % uri
    justi = select_query(q)
    for j in justi:
        cur = {START: j[START]['value'], END: j[END]['value']}
        doceid = j[DOCEID]['value']
        aug_dict_list(res, doceid, TEXT_SPAN, cur)


def query_video_justification(uri, res):
    q = '''
    SELECT DISTINCT ?doceid ?keyframeid ?topleftX ?topleftY ?bottomrightX ?bottomrightY ?confidence 
    WHERE {
        <%s> aida:justifiedBy ?j .
        ?j a aida:KeyframeVideoJustification ;
            aida:keyFrame ?keyframeid ;
            aida:boundingBox ?b;
            aida:confidence ?conf .
        ?conf aida:confidenceValue ?confidence .
        ?b aida:boundingBoxUpperLeftX ?topleftX ;
           aida:boundingBoxUpperLeftX ?topleftY ;
           aida:boundingBoxLowerRightX ?bottomrightX ;
           aida:boundingBoxLowerRightX ?bottomrightY .
    }
    ''' % uri
    justi = select_query(q)
    for j in justi:
        cur = {
            KEYFRAMEID: j[KEYFRAMEID]['value'],
            TOPLEFT: '%s,%s' % (j[TOPLEFT+'X']['value'], j[TOPLEFT+'Y']['value']),
            BOTTOMRIGHT: '%s,%s' % (j[BOTTOMRIGHT+'X']['value'], j[BOTTOMRIGHT+'Y']['value'])
        }
        doceid = j[DOCEID]['value']
        aug_dict_list(res, doceid, VIDEO_SPAN, cur)


def query_image_justification(uri, res):
    q = '''
    SELECT DISTINCT ?doceid ?topleftX ?topleftY ?bottomrightX ?bottomrightY ?confidence 
    WHERE {
        <%s> aida:justifiedBy ?j .
        ?j a aida:ImageJustification ;
            aida:boundingBox ?b ;
            aida:confidence ?conf .
        ?conf aida:confidenceValue ?confidence .
        ?b aida:boundingBoxUpperLeftX ?topleftX ;
           aida:boundingBoxUpperLeftX ?topleftY ;
           aida:boundingBoxLowerRightX ?bottomrightX ;
           aida:boundingBoxLowerRightX ?bottomrightY .
    }
    ''' % uri
    justi = select_query(q)
    for j in justi:
        cur = {
            TOPLEFT: '%s,%s' % (j[TOPLEFT+'X']['value'], j[TOPLEFT+'Y']['value']),
            BOTTOMRIGHT: '%s,%s' % (j[BOTTOMRIGHT+'X']['value'], j[BOTTOMRIGHT+'Y']['value'])
        }
        doceid = j[DOCEID]['value']
        aug_dict_list(res, doceid, IMAGE_SPAN, cur)


SUBJECT = 'subject'
PREDICATE = 'predicate'
OBJECT = 'object'

NODE = 'node'
ENTTYPE = 'enttype'

DESCRIPTORS = 'descriptors'

STRING_DESCRIPTOR = 'string_descriptor'
NAME_STRING = 'name_string'

TEXT_DESCRIPTOR = 'text_descriptor'
DOCEID = 'doceid'
START = 'start'
END = 'end'

VEDIO_DESCRIPTOR = 'video_descriptor'
KEYFRAMEID = 'keyframeid'
TOPLEFT = 'topleft'
BOTTOMRIGHT = 'bottomright'

IMAGE_DESCRIPTOR = 'image_descriptor'

ldcOnt = 'ldcOnt'
RDF_TYPE = 'rdf:type'

RDF_STATEMENT = 'rdf:Statement'
RDF_SUBJECT = 'rdf:subject'
RDF_PREDICATE = 'rdf:predicate'
RDF_OBJECT = 'rdf:object'

AIDA_HASNAME = 'aida:hasName'

AIDA_JUSTIFIEDBY = 'aida:justifiedBy'
AIDA_TEXTJUSTIFICATION = 'aida:TextJustification'
AIDA_IMAGEJUSTIFICATION = 'aida:ImageJustification'
AIDA_VIDEOJUSTIFICATION = 'aida:KeyframeVideoJustification'

AIDA_SOURCE = 'aida:source'
AIDA_STARTOFFSET = 'aida:startOffset'
AIDA_ENDOFFSETINCLUSIVE = 'aida:endOffsetInclusive'
AIDA_KEYFRAME = 'aida:keyFrame'

AIDA_BOUNDINGBOX = 'aida:BoundingBox'
AIDA_BOUNDINGBOXUPPERLEFTX = 'aida:boundingBoxUpperLeftX'
AIDA_BOUNDINGBOXUPPERLEFTY = 'aida:boundingBoxUpperLeftY'
AIDA_BOUNDINGBOXLOWERRIGHTX = 'aida:boundingBoxLowerRightX'
AIDA_BOUNDINGBOXLOWERRIGHTY = 'aida:boundingBoxLowerRightY'


TEXT_SPAN = 'text_span'
VIDEO_SPAN = 'video_span'
IMAGE_SPAN = 'image_span'


def pprint(x):
    if not x:
        print('Empty')
    if isinstance(x, dict):
        print(json.dumps(x, indent=2))
    elif isinstance(x, list):
        for ele in x:
            pprint(ele)
    elif isinstance(x, ET.ElementTree):
        print(minidom.parseString(ET.tostring(x.getroot())).toprettyxml())
    else:
        if isinstance(x, bytes):
            x = x.decode('utf-8')
        try:
            print(minidom.parseString(x).toprettyxml())
        except:
            print(x)


def write_file(x, output):
    filename = output
    if len(output.rsplit('/', 1)) == 2:
        dirpath, filename = output.rsplit('/', 1)
        if dirpath and dirpath != '.':
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
    with open(output, 'w') as f:
        if isinstance(x, dict) or isinstance(x, list):
            json.dump(x, f, indent=2)
        elif isinstance(x, ET.ElementTree):
            str_xml = ET.tostring(x.getroot())
            f.write(minidom.parseString(str_xml).toprettyxml())
        else:
            if isinstance(x, bytes):
                x = x.decode('utf-8')
            try:
                f.write(minidom.parseString(x).toprettyxml())
            except:
                f.write(x)
