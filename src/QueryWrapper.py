import json
from xml.etree import ElementTree
from SPARQLWrapper import SPARQLWrapper
from dicttoxml import dicttoxml
from src.Question import Question, Serializer
from src.utils import write_file, pretty_xml


class QueryWrapper(object):
    def __init__(self, endpoint, xml_mapping):
        self.sw = SPARQLWrapper(endpoint)
        if isinstance(xml_mapping, str):
            with open(xml_mapping) as f:
                self.xml_mapping = json.load(f)
        else:
            self.xml_mapping = xml_mapping
        self.prefix = ''

    def ask(self, question: Question):
        self.prefix = Serializer.prefix(question.prefix)
        query_str = question.serialize_to_sparql('select')
        self.sw.setQuery(query_str)
        self.sw.setReturnFormat('json')
        res = self.sw.query().convert()
        with_justification = self.get_justifications(res['results']['bindings'])
        xml_response = self.construct_xml(question.question_id, with_justification, question.edges)
        return xml_response

    def get_justifications(self, bindings):
        ret = {}
        for x in bindings:
            for k, v in x.items():
                if k not in ret:
                    ret[k] = {'label': k, 'uri': [], 'justifications': []}
                if v.get('type') == 'uri':
                    ret[k]['uri'].append(v['value'])
                    describe_justification = self.query_justification(v['value'])
                    ret[k]['justifications'].append(self.parse_single_justification(describe_justification))
        return ret

    def query_justification(self, uri):
        q = '%s \nDESCRIBE ?j WHERE { <%s> aida:justifiedBy ?j . }' % (self.prefix, uri)
        self.sw.setQuery(q)
        self.sw.setReturnFormat('json-ld')
        return self.sw.query().convert().serialize(format='text/n3').decode('utf-8')

    def parse_single_justification(self, n3text):
        texts = [x.strip() for x in n3text.split('\n\n') if not x.strip().startswith('@')]
        res = {}
        for t in texts:
            ret = {}
            lines = [l.strip().rstrip(';').rstrip('.').strip() for l in t.splitlines()]
            if not lines:
                break
            ret[lines[0].split(' ')[1]] = lines[0].split(' ')[2]
            sub = None
            for x in lines[1:]:
                p, o = x.split(' ', 1)
                o = o.strip('\"')
                p = p.split(':')[-1]
                if o[0] == '[':
                    p_, o_ = o.lstrip('[ ').rstrip().split(' ', 1)
                    ret[p] = {p_: o_}
                    sub = ret[p]
                elif sub:
                    if o[-1] == ']':
                        sub[p] = o.rstrip(' ]')
                        sub = None
                    else:
                        sub[p] = o
                else:
                    ret[p] = o
            span = '%s_span' % ret['a'].split(':')[-1].rsplit('Justification', 1)[0].lower()
            ans = {span: {
                'system_nodeid': ret['system'].lstrip('<').rstrip('>'),
                'confidence': float(ret['confidence']['confidenceValue'])
            }}
            for x in ret:
                if x not in {'confidence', 'system', 'privateData', 'a'}:
                    ans[span][self.xml_mapping[x]] = ret[x]
            if ret['source'] in res:
                res[ret['source']].append(ans)
            else:
                res[ret['source']] = [ans]
        return res

    @staticmethod
    def construct_xml(question_id, results, edges):
        def to_xml(objs):
            return [dicttoxml(obj, attr_type=False, root=False) for obj in objs]
        ret = ElementTree.Element('queryresponses', attrib={'id': question_id})
        root = ElementTree.Element('response')
        for edge in edges:
            edge_root = ElementTree.Element('edge', attrib={'id': edge})
            justifications = ElementTree.Element('justifications')
            all_just = {}
            for role, k in (('edge', edge), ('subject', edges[edge][0]), ('object', edges[edge][1])):
                for just_from_a_uri in results[k.lstrip('?')]['justifications']:
                    for docid, just_list in just_from_a_uri.items():
                        if docid in all_just:
                            if role in all_just[docid]:
                                all_just[docid][role] += to_xml(just_list)
                            else:
                                all_just[docid][role] = to_xml(just_list)
                        else:
                            all_just[docid] = {role: to_xml(just_list)}
            for docid, child in all_just.items():
                doc_root = ElementTree.Element('justification', attrib={'id': docid})
                for role, children in child.items():
                    role_root = ElementTree.Element('%s_justification' % role)
                    for c in children:
                        role_root.append(ElementTree.fromstring(c))
                    doc_root.append(role_root)
                justifications.append(doc_root)
            edge_root.append(justifications)
            root.append(edge_root)
            ret.append(root)
        return pretty_xml(ret)

