import unittest
import warnings

from src.driver.neo4j import Neo4j
from src.driver.solr import Solr
import src.utils.config_loader as cfg_loader
from src.service.entity_service import EntityService


class TestEntityService(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore', category=ImportWarning)
        cfg = cfg_loader.load_yaml_cfg('../../config.yml')
        self.neo4j = Neo4j(cfg['neo4j']['bolt'], cfg['neo4j']['user'], cfg['neo4j']['psw'])
        self.neo4j.connect()
        self.solr = Solr(cfg)
        self.entity_service = EntityService(self.neo4j, self.solr)

    def test_get_entity(self):
        entity_id = 48484848486748
        entity_text = 'Robert Aggas'
        entity = self.entity_service.get_entity(entity_id)
        self.assertEqual(entity_id, entity['node_id'])
        self.assertEqual(entity_text, entity['node_text'])

    def tearDown(self):
        self.neo4j.disconnect()


if __name__ == '__main__':
    unittest.main()
