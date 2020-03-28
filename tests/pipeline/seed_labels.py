import os
os.chdir('../../')

import unittest
import warnings

from src.driver.mongodb import MongoDB
import src.utils.config_loader as cfg_loader
from src.service.webpage_service import WebpageService
from src.html.webpage_lxml import ParsedPage
from src.html.webpage_selenium import SeleniumDriver
from src.driver.neo4j import Neo4j
from src.driver.solr import Solr
from src.indexes.webpage_index import WebPageIndex
from src.service.entity_service import EntityService
import src.utils.files as file

import src.pipeline.page_entities as page_entities
from collections import defaultdict
import src.pipeline.seed_labels.seed_labels as seed_labels


cfg = cfg_loader.load_yaml_cfg('config.yml')

mongodb = MongoDB(cfg['mongodb']['host'], cfg['mongodb']['user'], cfg['mongodb']['psw'], cfg['mongodb']['db_name'])
mongodb.wait_and_connect()
neo4j = Neo4j(cfg['neo4j']['bolt'], cfg['neo4j']['user'], cfg['neo4j']['psw'])
neo4j.wait_and_connect()
solr = Solr(cfg)

entity_service = EntityService(neo4j, solr)
page_service = WebpageService(mongodb, cfg['swde']['collection'])
webpage_index = WebPageIndex(page_service, mongodb)
selenium_driver = SeleniumDriver(cfg['selenium']['load_page_timeout'])


def ignore_warnings(test_func):
    def do_test(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            test_func(self, *args, **kwargs)
    return do_test


class TestPageEntities(unittest.TestCase):
    @ignore_warnings
    def test_get_best_parameter(self):
        parameter = 'redundancy_against_distance'
        range = (0.1, 0.3)
        step = 0.01

        cfg['seed_labels']['debug'] = False

        results = []
        curr_value = range[0]
        while curr_value <= range[1]:
            cfg['seed_labels'][parameter] = curr_value
            result = seed_labels.compute_seed_labels(page_service, entity_service, webpage_index, selenium_driver, cfg)
            result['value'] = curr_value
            results.append(result)
            curr_value += step

        results.sort(key=lambda r: r['f1'], reverse=True)

        print('results: [{}]'.format(parameter))
        for result in results:
            print('   {}'.format(result))




if __name__ == '__main__':
    unittest.main()
    mongodb.disconnect()
    neo4j.disconnect()
