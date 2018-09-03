import xmltodict
from .utils import *


class Question(object):
    def __init__(self, xml_question):
        if xml_question.endswith('.xml'):
            with open(xml_question) as f:
                self.xml = f.read()
        else:
            self.xml = xml_question

        temp = xmltodict.parse(self.xml)['graph_queries']['graph_query']
        self.query_id = temp['@id']

        self.edges = []
        self.entrypoints = []
        self.nodes = set()
        self.parse_an_edge(temp['graph']['edges']['edge'])
        self.parse_a_entrypoint(temp['entrypoints']['entrypoint'])

        # import json
        # print(json.dumps(self.edges, indent=2))
        # print(json.dumps(self.entrypoints, indent=2))
        # print(self.nodes)

    def parse_an_edge(self, edge: list or dict):
        if isinstance(edge, list):
            for an_edge in edge:
                self.parse_an_edge(an_edge)
        else:
            self.nodes.add(edge[SUBJECT])
            self.nodes.add('?' + edge['@id'])
            self.nodes.add(edge[OBJECT])
            self.edges.append({
                '?' + edge['@id']: [
                    (RDF_TYPE, RDF_STATEMENT),
                    (RDF_SUBJECT, edge[SUBJECT]),
                    (RDF_PREDICATE, ldcOnt + ':' + edge[PREDICATE]),
                    (RDF_OBJECT, edge[OBJECT])
                ]
            })

    def parse_a_entrypoint(self, entrypoint: list or dict):
        if isinstance(entrypoint, list):
            for a_entrypoint in entrypoint:
                self.parse_a_entrypoint(a_entrypoint)
        else:
            ep = {NODE: entrypoint[NODE]}
            node = ep[NODE]
            if ENTTYPE in entrypoint:
                ep[ENTTYPE] = {
                    node + '_type': [
                        (RDF_SUBJECT, node),
                        (RDF_PREDICATE, RDF_TYPE),
                        (RDF_OBJECT, ldcOnt + ':' + entrypoint[ENTTYPE])
                ]}
            ep[DESCRIPTORS] = []
            if STRING_DESCRIPTOR in entrypoint:
                if isinstance(entrypoint[STRING_DESCRIPTOR], dict):
                    ep[DESCRIPTORS].append({node: [(AIDA_HASNAME, self.quote(entrypoint[STRING_DESCRIPTOR][NAME_STRING]))]})
                else:
                    ep[DESCRIPTORS] += [{node: [(AIDA_HASNAME, self.quote(x[NAME_STRING]))]} for x in entrypoint[STRING_DESCRIPTOR]]
            for name_, type_ in ((TEXT_DESCRIPTOR, AIDA_TEXTJUSTIFICATION),
                                 (IMAGE_DESCRIPTOR, AIDA_IMAGEJUSTIFICATION),
                                 (VEDIO_DESCRIPTOR, AIDA_VIDEOJUSTIFICATION)):
                if name_ in entrypoint:
                    self.parse_a_descriptor(node, name_.rstrip('descriptor'), type_, 0, entrypoint[name_], ep[DESCRIPTORS])
            self.entrypoints.append(ep)

    def parse_a_descriptor(self, subject, name_, type_, cnt, descriptor_obj, descriptor_list):
        if isinstance(descriptor_obj, list):
            for i in range(len(descriptor_obj)):
                self.parse_a_descriptor(subject, name_, type_, i, descriptor_obj[i], descriptor_list)
        else:
            justi_var = '%s_%s%d' % (subject, name_, cnt)
            res = {
                subject: [(AIDA_JUSTIFIEDBY, justi_var)],
                justi_var: [(RDF_TYPE, type_)]
            }

            for tag_, ont_ in ((DOCEID, AIDA_SOURCE),
                               (KEYFRAMEID, AIDA_KEYFRAME)):
                if tag_ in descriptor_obj:
                    res[justi_var].append((ont_, self.quote(descriptor_obj[tag_])))

            for tag_, ont_ in ((START, AIDA_STARTOFFSET),
                               (END, AIDA_ENDOFFSETINCLUSIVE)):
                if tag_ in descriptor_obj:
                    res[justi_var].append((ont_, descriptor_obj[tag_]))

            if TOPLEFT in descriptor_obj or BOTTOMRIGHT in descriptor_obj:
                box_var = '%s_%s%d_box' % (subject, name_, cnt)
                res[justi_var].append((AIDA_BOUNDINGBOX, box_var))
                res[box_var] = []
                for tag_, ont_ in ((TOPLEFT, (AIDA_BOUNDINGBOXUPPERLEFTX, AIDA_BOUNDINGBOXUPPERLEFTY)),
                                   (BOTTOMRIGHT, (AIDA_BOUNDINGBOXLOWERRIGHTX, AIDA_BOUNDINGBOXLOWERRIGHTY))):
                    if tag_ in descriptor_obj:
                        values = descriptor_obj[tag_].split(',')
                        res[box_var].append((ont_[0], values[0]))
                        res[box_var].append((ont_[1], values[1]))
            descriptor_list.append(res)

    def serialize_strict_sparql(self):
        return Serializer(self).serialize_select_query()

    @staticmethod
    def quote(x):
        return '"%s"' % x


class Serializer(object):
    def __init__(self, question:Question):
        self.question = question

    def serialize_select_query(self):
        return '\nSELECT %s \n%s' % (self.serialize_vars(), self.serialize_where())

    def serialize_where(self):
        return '\nWHERE {\n%s\n}' % '\n'.join([self.serialize_edges(), self.serialize_entrypoints()])

    def serialize_vars(self):\
        return ' '.join(self.question.nodes)

    def serialize_edges(self):
        return self.serialize_list_of_triples(self.question.edges)

    def serialize_entrypoints(self):
        return '\n'.join([self.serialize_a_node(node)for node in self.question.entrypoints])

    def serialize_a_node(self, node_obj: dict):
        top_level = self.serialize_triples(node_obj.get(ENTTYPE))
        union_descriptors = self.serialize_list_of_triples(node_obj.get(DESCRIPTORS))
        return '{\n%s\n%s\n}' % (top_level, union_descriptors)

    def serialize_list_of_triples(self, list_of_triples: list(), joiner: str='\n'):
        if not list_of_triples:
            return ''
        return joiner.join([self.serialize_triples(triples) for triples in list_of_triples])

    @staticmethod
    def serialize_triples(triples: dict):
        '''
        :param triples: {SUBJECT_1 : [(PREDICATE_1_1, OBJECT_1_1), (PREDICATE_1_2, OBJECT_1_2)], SUBJECT_2: [(PREDICATE_2, OBJECT_2)]}
        :return: SPARQL string :
                SUBJECT_1 PREDIACTE_1_1 OBJECT_1_1 ;
                          PREDICATE_1_2 OBJECT_1_2 .
                SUBJECT_2 PREDICATE_1 OBJECT_2 .
        '''
        if not triples:
            return ''
        return '\t' + ('\n\t'.join(['\n'.join(
            [' '.join(('\t\t' if i else k, v[i][0], v[i][1], ';' if i < len(v)-1 else '.')) for i in range(len(v))]
            ) if not k.startswith('@') else v for k, v in triples.items()]))
