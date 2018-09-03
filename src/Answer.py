
import xml.etree.ElementTree as ET
from xml.dom import minidom
from .Question import Question
from .utils import *


class Answer(object):
    def __init__(self, question: Question):
        self.question = question
        self.node_uri = {}
        # {'?attackt_event': ['http://example.com/event/111']}
        for node in question.nodes:
            self.node_uri[node] = []
        self.asked_uri = False
        self.node_justification = {}

    def ask(self):
        self.ask_uri()
        self.ask_justifications()
        return self.construct_xml_response()

    def ask_uri(self):
        bindings = select_query(self.question.serialize_strict_sparql())
        for x in bindings:
            for node in self.question.nodes:
                self.node_uri[node].append(x[node.lstrip('?')]['value'])
        self.asked_uri = True

    def ask_justifications(self):
        if not self.asked_uri:
            self.ask_uri()

        for node, uri_list in self.node_uri.items():
            justi = {}
            for uri in uri_list:
                query_text_justification(uri, justi)
                query_image_justification(uri, justi)
                query_video_justification(uri, justi)
            self.node_justification[node] = justi

    def construct_xml_response(self):
        root = ET.Element('graphquery_responses', attrib={'id': self.question.query_id})
        for edge in self.question.edges:
            for k, pairs in edge.items():
                justifications = ET.SubElement(ET.SubElement(root, 'edge', id=k.lstrip('?')), 'justifications')
                docs = {}
                for node_key, justi_key in ((pairs[1][1], 'subject_justification'),
                                            (pairs[3][1], 'object_justification'),
                                            (k, 'edge_justification')):
                    for doceid, spans in self.node_justification[node_key].items():
                        if doceid not in docs:
                            docs[doceid] = {}
                            for x in ('subject', 'object', 'edge'):
                                docs[doceid][x+'_justification'] = {'system_nodeid': '', 'confidence': ''}
                        docs[doceid][justi_key].update(spans)

                for doc, justi in docs.items():
                    self.update_xml(ET.SubElement(justifications, 'justification', docid=doc), justi)
        return minidom.parseString(ET.tostring(root)).toprettyxml()

    def update_xml(self, root, obj):
        if isinstance(obj, str):
            root.text = obj
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, list):
                    for v_ in v:
                        self.update_xml(ET.SubElement(root, k), v_)
                else:
                    self.update_xml(ET.SubElement(root, k), v)
