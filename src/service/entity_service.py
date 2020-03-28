import src.utils.string_utils as string_utils

class EntityService:
    def __init__(self, neo4j, solr):
        self.neo4j = neo4j
        self.solr = solr

    def neo4j_record_to_dict(self, neo4j_node, only_id=False):
        dict_node = {}
        for (field_name, field_value) in neo4j_node.items():
            dict_node[field_name] = str(field_value)

        if only_id:
            return dict_node['node_id']
        else:
            return dict_node

    def get_entity(self, entity_id):
        # neo4j_node = self.neo4j.run_query("MATCH (n:CommonNode) WHERE n.node_id={} RETURN n".format(entity_id)).single().get('n')
        # return self.neo4j_node_to_dict(neo4j_node)

        node_solr = self.solr.send_query('kb_node', 'node_id:"{}"'.format(entity_id))[0]
        return {'node_id': int(node_solr['node_id']), 'node_text': node_solr['node_text']}

    def search_entities(self, entity_name, only_id=False, strict=True):
        if len(entity_name) > 300:
            return []

        nodes_solr = self.solr.send_query('kb_node', 'node_text:"{}"'.format(entity_name))

        # if entity_name=='mx279h':
        #     print(nodes_solr)

        if strict:
            # get only entities where node_text ~= text
            nodes_solr = list(filter(lambda node: string_utils.compare_string(node['node_text'], entity_name), nodes_solr))

        if only_id:
            return [node['node_id'] for node in nodes_solr]
        else:
            return [{'node_id': node['node_id'], 'node_text': node['node_text']} for node in nodes_solr]

    def get_related_objects(self, entity_id):
        result = self.neo4j.run_query("MATCH (n:CommonNode)-[r:CommonRelation]->(t:CommonNode) WHERE n.node_id={} RETURN r, t".format(entity_id))

        dict_nodes = {}
        for record in result.records():
            record_items = record.items()

            neo4j_edge = record.items()[0][1]
            neo4j_node = record.items()[1][1]

            dict_edge = self.neo4j_record_to_dict(neo4j_edge)
            dict_node = self.neo4j_record_to_dict(neo4j_node)

            if not dict_node['node_id'] in dict_nodes:
                dict_nodes[dict_node['node_id']] = {'obj_text': dict_node['node_text'], 'rel_types': {}}

            dict_nodes[dict_node['node_id']]['rel_types'][dict_edge['edge_type_id']] = dict_edge['edge_type_text']

        return dict_nodes

    def get_relations_between(self, entity1, entity2):
        result = self.neo4j.run_query("MATCH (s:CommonNode)-[r:CommonRelation]->(d:CommonNode) WHERE s.node_id={} AND d.node_id={} RETURN r limit 10".format(entity1, entity2))

        dict_edges = []
        for record in result.records():
            neo4j_edge = record.items()[0][1]
            dict_edge = self.neo4j_record_to_dict(neo4j_edge)
            dict_edges.append(dict_edge)

        return dict_edges

