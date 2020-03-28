from neo4j import GraphDatabase
import src.utils.docker as docker
import time


class Neo4j():
    def __init__(self, uri, user, password):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def connect(self):
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def disconnect(self):
        self._driver.close()

    def wait_and_connect(self, max_retry=10):
        print('connecting to neo4j... [.', end='')
        count = 0
        while True:
            try:
                count += 1
                if count > max_retry:
                    break
                self.connect()
                break
            except Exception:
                print('.', end='')
                time.sleep(2)
        print('] done')

    def restart_neo4j(self, max_retry=10):
        self.disconnect()
        docker.docker_compose('restart neo4j', './docker')
        self.wait_and_connect(max_retry=max_retry)

    def run_query(self, query, query_type='read'):
        """

        :param query:
        :param type: 'no':no_transaction, 'read':transaction_read, 'write':transaction_write
        :return:
        """
        with self._driver.session() as session:
            if query_type is 'no':
                result = session.run(query)
            elif query_type is 'read':
                result = session.read_transaction(self._run_query, query)
            elif query_type is 'write':
                result = session.write_transaction(self._run_query, query)
            else:
                raise ValueError("wrong parameter query_type")

            return result

    @staticmethod
    def _run_query(tx, query):
        result = tx.run(query)
        return result

    def clean_db(self):
        self.run_query("MATCH (n) DETACH DELETE n", query_type='no')

    def import_vertices_csv(self, csv_name):
        self.run_query("USING PERIODIC COMMIT 500 "
                       "LOAD CSV WITH HEADERS FROM 'file:///freebase_data/%s.csv' AS line	"
                       "CREATE (:Entity{node_id:line.node_id, text:line.node_text})" % (csv_name), query_type='no')
        
    def import_edges_csv(self, csv_name):
        self.run_query("USING PERIODIC COMMIT 500 "
                       "LOAD CSV WITH HEADERS FROM 'file:///freebase_data/%s.csv' AS line "
                       "MATCH (a:Entity), (b:Entity) "
                       "WHERE a.node_id = line.source_node_id AND b.node_id = line.dest_node_id "
                       "CREATE (a)-[r:Relation {edge_id:line.edge_type_id, text:line.edge_type_text}]->(b)" % (csv_name), query_type='no')
    
    def create_index(self, label, attribute, wait_finish=True):
        print('creating graphdb index on {}:{}...'.format(label, attribute))
        self.run_query("CREATE INDEX ON :{}({})".format(label, attribute), query_type='no')

        if wait_finish:
            self.run_query("CALL db.awaitIndexes(120)", query_type='no')
        print('   done')

    def create_node(self, properties, label='CommonNode'):
        properties_query = "{"
        for property_key, property_value in properties.items():
            if isinstance(property_value, int):
                properties_query += '{}:{}, '.format(property_key, property_value)
            else:
                properties_query += '{}:"{}", '.format(property_key, property_value)
        properties_query = properties_query[:-2]
        properties_query += "}"

        query = "CREATE(:%s %s)" % (label, properties_query)
        self.run_query(query, query_type='no')

    def create_edge(self, source_node_id, dest_node_id, properties, label='CommonRelation'):
        properties_query = "{"
        for property_key, property_value in properties.items():
            if isinstance(property_value, int):
                properties_query += '{}:{}, '.format(property_key, property_value)
            else:
                properties_query += '{}:"{}", '.format(property_key, property_value)
        properties_query = properties_query[:-2]
        properties_query += "}"

        query = """MATCH (a:CommonNode), (b:CommonNode)
                   WHERE a.node_id = {} AND b.node_id = {}
                   CREATE (a)-[r:{} {} ]->(b)
                   RETURN r""".format(source_node_id, dest_node_id, label, properties_query)
        self.run_query(query, query_type='no')

    def get_max_node_property_value(self, edge_property):
        query = "MATCH (n) RETURN MAX(n.{})".format(edge_property)
        return self.run_query(query, query_type='no')

    def get_max_edge_property_value(self, edge_property):
        query = "MATCH (n:CommonNode)-[r:CommonRelation]->(t:CommonNode) RETURN MAX(r.{})".format(edge_property)
        return self.run_query(query, query_type='no')



