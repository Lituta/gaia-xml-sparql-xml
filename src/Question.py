import json, xmltodict


class Serializer(object):
    @staticmethod
    def triples(triples):
        return '\n\t'.join(['\n'.join(
            [' '.join(('\t\t' if i else k, v[i][0], v[i][1], ';' if i < len(v)-1 else '.')) for i in range(len(v))]
            ) if not k.startswith('@') else v for k, v in triples.items()])

    @staticmethod
    def prefix(prefix):
        return '\n'.join(['PREFIX %s: <%s>' % (k, v) for k, v in prefix.items()])

    @staticmethod
    def union(clauses):
        return '\t{\n\t%s\n\t}' % '\n\t}\n\tUNION\n\t{\n\t'.join(clauses)

    @staticmethod
    def sparql(prefix, edges, others, mode='construct', variables=set()):
        if mode == 'construct':
            return '%s\n\nCONSTRUCT {\n\t%s\n}\nWHERE {\n\t%s\n\n%s\n}' % (prefix, edges, edges, others)
        else:
            return '%s\n\n%s DISTINCT %s \nWHERE {\n\t%s\n\n%s\n}' % (prefix, mode.upper(), ' '.join(variables), edges, others)


class Question(object):
    def __init__(self, ont_path: str, xml_question) -> None:
        """
        init a question parser with ontology mapping from xml tags to valid sparql uri
        :param ont_path: file path of the ontology mapping json
        """

        self.ont = self.load_ont(ont_path)

        if xml_question.endswith('.xml'):
            with open(xml_question) as f:
                self.q_xml = f.read()
        else:
            self.q_xml = xml_question

        self.ranges = {
            'string': lambda x: '"%s"' % x,
            'uri': lambda x: self.get_path(self.ont, ['class', x, 'path']),
            'number': lambda x: x
        }

        self.JUSTIFIEDBY = 'aida:justifiedBy'
        self.ENTITY_RELATION = 'aida:Relation'
        self.STATEMENT = lambda s, p, o: [('a', 'rdf:Statement'),
                                     ('rdf:subject', s),
                                     ('rdf:predicate', p),
                                     ('rdf:object', o)]
        self._edges = {}
        self._prefix = self.ont.get('prefix')
        self._question_id = ''
        self._query = self.parse_question()

    @property
    def edges(self):
        return self._edges

    @property
    def prefix(self):
        return self._prefix

    @property
    def question_id(self):
        return self._question_id

    def parse_question(self) -> dict:
        """
        parse a xml question to a json representation with valid ontology in sparql
        :param xml: file path of the question in xml, or the xml question text
        :return: a Question instance with json representation of the question
        """

        ori = xmltodict.parse(self.q_xml).get('query', {})
        self._question_id = ori.get('@id', 'unknown')
        edges = self.parse_edges(self.get_path(ori, ['graph', 'edges', 'edge']))
        entrypoints = self.parse_entrypoints(self.get_path(ori, ['entrypoints']))

        return {
            '@id': ori.get('@id', ''),
            'edges': edges,
            'entrypoints': entrypoints
        }

    def parse_edges(self, edge: list or dict) -> dict:
        ret = {}
        if isinstance(edge, list):
            for e in edge:
                ret.update(self.parse_edges(e))
        else:
            key, s, p, o = edge.values()
            predicate = self.get_path(self.ont, ['predicate', p, 'path'])[0]
            domain_ = self.get_path(self.ont, ['predicate', p, 'domain'])
            range_ = self.get_path(self.ont, ['predicate', p, 'range'])
            super_edge = '?%s' % key
            self._edges[super_edge] = (s, o)
            if domain_ == 'Entity' and range_ == 'Entity':
                ret[super_edge] = [('a', self.ENTITY_RELATION)]
                ret[super_edge+'_s'] = self.STATEMENT(super_edge, super_edge+'_ps', s)
                ret[super_edge+'_p'] = self.STATEMENT(super_edge, 'rdf:type', predicate)
                ret[super_edge+'_o'] = self.STATEMENT(super_edge, super_edge+'_po', o)
                ret['@filter'] = 'FILTER(REGEX(STR(%s), "subject$") && REGEX(STR(%s), "object$"))' % (super_edge+'_ps', super_edge+'_po')
            else:
                ret[super_edge] = self.STATEMENT(s, predicate, o)
        return ret

    def parse_entrypoints(self, entrypoints: dict) -> dict:
        ret = {}
        for k, v in entrypoints.items():
            if isinstance(v, list):
                for v_ in v:
                    key_node = v_['node']
                    if key_node not in ret:
                        ret[key_node] = {k: []}
                    else:
                        if k not in ret[key_node]:
                            ret[key_node][k] = []
                    ret[key_node][k].append(self.parse_entrypoint(k, v_))
            else:
                key_node = v['node']
                if key_node not in ret:
                    ret[key_node] = {k: []}
                else:
                    if k not in ret[key_node]:
                        ret[key_node][k] = []
                ret[key_node][k].append(self.parse_entrypoint(k, v))
        return ret

    def parse_entrypoint(self, ep_type: str, children: dict or list) -> dict:
        triples = {}
        if isinstance(children, list):
            for child in children:
                triples.update(self.parse_entrypoint(ep_type, child))
        else:
            s, exists = children.get('node'), {}
            for k, v in children.items():
                predicate = self.get_path(self.ont, ['predicate', k])
                if 'splitter' in predicate:
                    values = v.split(predicate.get('splitter'))
                    predicates = predicate.get('split_to', [])
                    for i in range(len(values)):
                        self.parse_triple(s, predicates[i], values[i], exists, triples)
                elif predicate:
                    self.parse_triple(s, predicate, v, exists, triples)

            justify_type = self.get_path(self.ont, ['class', ep_type, 'path'])
            if justify_type and self.JUSTIFIEDBY in exists:
                self.add_triple(exists[self.JUSTIFIEDBY], 'a', justify_type, triples)
        return triples

    def parse_triple(self, s: str, predicate: dict, value: str, exists: dict, triples: dict) -> None:
        path = predicate.get('path')
        o = self.ranges.get(predicate.get('range'), lambda x: x)(value)
        if predicate.get('statement') and len(path) == 1:
            ss = '%s_var_%s' % (s, path[0].replace(':', '_'))
            for pp, oo in self.STATEMENT(s, path[0], o):
                self.add_triple(ss, pp, oo, triples)
        else:
            for i in range(len(path)):
                if i < len(path) - 1:
                    if path[i] not in exists:
                        self.add_triple(s, path[i], '%s_var%d' % (s, i), triples)
                        exists[path[i]] = s = '%s_var%d' % (s, i)
                    else:
                        s = exists[path[i]]
                else:
                    self.add_triple(s, path[i], o, triples)

    def serialize_to_sparql(self, mode):
        clauses = '\n'.join([Serializer.union([Serializer.triples(ep) for eps in group.values() for ep in eps]) for group in self._query['entrypoints'].values()])
        return Serializer.sparql(Serializer.prefix(self._prefix),
                                 Serializer.triples(self._query['edges']),
                                 clauses,
                                 mode=mode,
                                 variables=set([item for sub in [(k, v[0], v[1]) for k, v in self._edges.items()] for item in sub]))

    @staticmethod
    def get_path(target: dict, path: list):
        for i in range(len(path)):
            target = target.get(path[i], {})
        return target

    @staticmethod
    def add_triple(s, p, o, triples):
        if s in triples:
            triples[s].append((p, o))
        else:
            triples[s] = [(p, o)]

    @staticmethod
    def load_ont(ont_path: str) -> dict:
        try:
            with open(ont_path) as ont_file:
                return json.load(ont_file)
        except Exception as e:
            print('failed to load ontology, %s' % str(e))
        return {}
