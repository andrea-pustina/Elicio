from src.driver.neo4j import Neo4j
from src.driver.solr import Solr
from src.driver.mongodb import MongoDB
import src.utils.config_loader as cfg_loader
import src.utils.docker as docker
import src.dataset.swde as swde
import src.dataset.monitor as monitor
import src.pipeline.topic_identification as topic_identification
from src.service.webpage_service import WebpageService
from src.service.entity_service import EntityService
from src.indexes.webpage_index import WebPageIndex
import src.knowledge_base.kb_preprocessor as kb_preprocessor

import src.knowledge_base.neo4j_importer as neo4j_importer
import src.knowledge_base.solr_importer as kb_solr_importer
import src.pipeline.seed_labels.seed_labels as seed_labels
import src.pipeline.page_entities as page_entities
import src.pipeline.candidate_pred_obj_pairs as candidate_pred_obj_pairs
import src.pipeline.label_propagation_clustering as label_propagation
import src.pipeline.new_labels_kb_saver as new_labels_saver
import src.pipeline.crowdsourcing as crowdsourcing
from src.html.webpage_selenium import SeleniumDriver


if __name__ == "__main__":
    cfg = cfg_loader.load_yaml_cfg('config.yml')

    if cfg['main']['manage_docker']:
        docker.docker_compose('down', './docker')
        docker.docker_compose('up -d', './docker')

    neo4j = Neo4j(cfg['neo4j']['bolt'], cfg['neo4j']['user'], cfg['neo4j']['psw'])
    solr = Solr(cfg)
    mongodb = MongoDB(cfg['mongodb']['host'], cfg['mongodb']['user'], cfg['mongodb']['psw'], cfg['mongodb']['db_name'])

    neo4j.wait_and_connect()
    mongodb.wait_and_connect()

    if cfg['main']['preprocess_kb']:
        kb_preprocessor.preprocess_kb(cfg)

    if cfg['main']['import_kb_graphdb']:
        neo4j_importer.import_kb_and_create_index(cfg, neo4j)

    if cfg['main']['import_kb_solr']:
        kb_solr_importer.import_kb(cfg, solr)

    selenium_driver = SeleniumDriver(cfg['selenium']['load_page_timeout'])

    if cfg['main']['import_dataset_mongodb']:
        if cfg['mongodb_importer']['dataset'] == 'swde':
            swde.import_dataset(mongodb, selenium_driver, cfg)
        elif cfg['mongodb_importer']['dataset'] == 'monitor':
            monitor.import_dataset(mongodb, selenium_driver, cfg)

    page_service = WebpageService(mongodb, cfg['swde']['collection'])
    entity_service = EntityService(neo4j, solr)
    webpage_index = WebPageIndex(page_service, mongodb)

    if cfg['main']['compute_term_freq_indexes']:
        webpage_index.index_webpages_grouping_by_template()

    if cfg['main']['compute_page_entities']:
        page_entities.compute_page_entities(page_service, entity_service, webpage_index, cfg)

    if cfg['main']['topic_identification']:
        topic_identification.identify_topic(page_service, entity_service, webpage_index, cfg)

    if cfg['main']['compute_candidate_pred_obj_pairs']:
        candidate_pred_obj_pairs.get_pred_candidates_foreach_obj(page_service, entity_service, webpage_index, selenium_driver, cfg)

    if cfg['main']['compute_seed_labels']:
        seed_labels.compute_seed_labels(page_service, entity_service, webpage_index, selenium_driver, cfg)

    if cfg['main']['label_propagation']:
        label_propagation.propagate_labels(page_service, cfg, webpage_index)

    if cfg['main']['save_new_labels_in_kb']:
        new_labels_saver.save_new_labels_in_kb(page_service, neo4j, solr, cfg)

    if cfg['main']['crowdsourcing']:
        crowdsourcing.start_crowd(page_service, neo4j, solr, cfg)

    mongodb.disconnect()
    neo4j.disconnect()
    selenium_driver.close()

    if cfg['main']['manage_docker']:
            docker.docker_compose('down', './docker')





