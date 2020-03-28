import unittest
import warnings

from src.driver.solr import Solr
import src.utils.config_loader as cfg_loader


class TestEntityService(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore', category=ImportWarning)
        cfg = cfg_loader.load_yaml_cfg('../../config.yml')
        self.solr = Solr(cfg)

    def test_send_query(self):
        node_text = 'Pulp Fiction'
        nodes_solr = self.solr.send_query('freebase_node', 'node_text:"{}"'.format(node_text))

        nodes_id = []
        for node_solr in nodes_solr:
            nodes_id.append(node_solr['node_id'])

        self.assertIn('67758281745248', nodes_id)


if __name__ == '__main__':
    unittest.main()
