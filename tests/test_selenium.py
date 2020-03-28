import os
os.chdir('../')

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
    def test_open_some_pages(self):
        domain = 'movie'
        sites = ['allmovie', 'amctv', 'boxofficemojo', 'hollywood', 'iheartmovies', 'imdb', 'metacritic', 'msn', 'rottentomatoes', 'yahoo']
        #sites = ['rottentomatoes']
        page_to_open = 1

        browser_tab_count = 1
        for site in sites:
            opened_pages = 0
            webpages_paths = file.get_files_into_dir('input_data/swde/webpages/{}/{}-{}(2000)'.format(domain, domain, site), full_path=True)
            for webpage_path in webpages_paths:
                with open(webpage_path, 'r', encoding="utf8") as webpage_file:
                    html = webpage_file.read()
                    html = ParsedPage.clean_html(html)

                    selenium_driver.open_tab(browser_tab_count)
                    selenium_driver.select_tab(browser_tab_count)
                    selenium_driver.set_page(html)
                    # print(selenium_driver.get_corrected_html())
                    browser_tab_count += 1

                opened_pages += 1
                if opened_pages >= page_to_open:
                    break

    @ignore_warnings
    def test_open_some_loaded_pages(self):
        domain = 'movie'
        sites = []
        pages_for_template = 1

        if len(sites) == 0:
            templates = page_service.get_all_field_values('template')
        else:
            templates = [domain + '-' + site for site in sites]

        browser_tab_count = 1
        template_pages_count = 0
        for template in templates:
            for page in page_service.get_all(template=template):
                print('{} - {}'.format(page['site'], page['file_name']))
                selenium_driver.open_tab(browser_tab_count)
                selenium_driver.select_tab(browser_tab_count)
                selenium_driver.set_page(page['html'])

                browser_tab_count += 1
                template_pages_count += 1
                if template_pages_count >= pages_for_template:
                    break

            template_pages_count = 0

    @ignore_warnings
    def test_get_all_text_nodes(self):
        domain = 'movie'
        sites = []

        if len(sites) == 0:
            templates = page_service.get_all_field_values('template')
        else:
            templates = [domain + '-' + site for site in sites]

        browser_tab_count = 1
        for template in templates:
            page = page_service.get_all(template=template)[1]
            parsed_page = ParsedPage(page['html'])

            text_nodes = parsed_page.get_all_text_nodes()
            print(len(text_nodes))
            print([text_node.text for text_node in text_nodes])
            text_nodes_xpaths = parsed_page.convert_all_lxml_nodes_to_xpath_in_nested_dict(text_nodes)
            text_nodes_xpaths = list(filter(lambda xpath: 'noscript' not in xpath, text_nodes_xpaths))

            selenium_driver.open_tab(browser_tab_count)
            selenium_driver.select_tab(browser_tab_count)
            browser_tab_count += 1

            selenium_driver.set_page(page['html'])
            selenium_driver.color_elements(text_nodes_xpaths)

    @ignore_warnings
    def test_get_filtered_text_nodes(self):
        domain = 'monitor'
        sites = []

        if len(sites) == 0:
            templates = page_service.get_all_field_values('template')
        else:
            templates = [domain + '-' + site for site in sites]

        browser_tab_count = 1
        for template in templates:
            page = page_service.get_all(template=template)[1]
            parsed_page = ParsedPage(page['html'])

            print('{} - {}'.format(template, page['file_name']))

            text_nodes = parsed_page.get_all_text_nodes()
            text_nodes = page_entities.filter_text_nodes(text_nodes, cfg, webpage_index, page['template'])
            print([text_node.text for text_node in text_nodes])
            text_nodes_xpaths = parsed_page.convert_all_lxml_nodes_to_xpath_in_nested_dict(text_nodes)

            selenium_driver.open_tab(browser_tab_count)
            selenium_driver.select_tab(browser_tab_count)
            browser_tab_count += 1

            selenium_driver.set_page(page['html'])
            selenium_driver.color_elements(text_nodes_xpaths)

    @ignore_warnings
    def test_page_topic_related_objs(self):
        domain = 'movie'
        sites = []
        pages_for_template = 1

        if len(sites) == 0:
            templates = page_service.get_all_field_values('template')
        else:
            templates = [domain + '-' + site for site in sites]

        browser_tab_count = 1
        template_pages_count = 0
        for template in templates:
            for page in page_service.get_all(template=template):
                if 'topic_related_candidate_pairs' in page:

                    print('{} - {}'.format(page['site'], page['file_name']))
                    selenium_driver.open_tab(browser_tab_count)
                    selenium_driver.select_tab(browser_tab_count)
                    selenium_driver.set_page(page['html'])


                    topic_related_objs = [obj for obj in page['topic_related_candidate_pairs'].keys()]
                    selenium_driver.color_elements(topic_related_objs)

                    browser_tab_count += 1
                    template_pages_count += 1
                    if template_pages_count >= pages_for_template:
                        break

            template_pages_count = 0

    @ignore_warnings
    def test_seed_labels(self):
        domain = 'movie'
        sites = []
        topics = []
        pages_for_template = 1

        if len(sites) == 0:
            templates = page_service.get_all_field_values('template')
            templates = list(filter(lambda template: domain in template, templates))
        else:
            templates = [domain + '-' + site for site in sites]


        browser_tab_count = 1
        template_pages_count = 0
        for template in templates:
            for page in page_service.get_all(template=template):
                if 'seed_labels' in page and len(page['seed_labels'])>0 and page['seed_labels_errors'] >= 0:
                    if len(topics)>0 and page['topic_text'] not in topics:
                        continue

                    print('{} - {}'.format(page['site'], page['file_name']))
                    selenium_driver.open_tab(browser_tab_count)
                    selenium_driver.select_tab(browser_tab_count)
                    selenium_driver.set_page(page['html'])

                    seed_labels = page['seed_labels']
                    seed_labels_by_pred = defaultdict(list)
                    for obj_xpath, obj_data in seed_labels.items():
                        pred_xpath = obj_data['pred']
                        seed_labels_by_pred[pred_xpath].append(obj_xpath)

                    for pred_xpath, objs_xpaths in seed_labels_by_pred.items():
                        objs_xpaths.append(pred_xpath)
                        selenium_driver.color_elements(objs_xpaths)

                    browser_tab_count += 1
                    template_pages_count += 1
                if template_pages_count >= pages_for_template:
                    break

            template_pages_count = 0

    @ignore_warnings
    def test_get_element_corners(self):
        domain = 'movie'
        site = 'rottentomatoes'
        xpath = '/html/body/div[6]/div/div/div[4]/div/div[1]/div[1]/div[1]/ul[1]/li/a'

        template = domain + '-' + site

        for page in page_service.get_all(template=template):
            print('{} - {}'.format(page['site'], page['file_name']))
            selenium_driver.open_tab(1)
            selenium_driver.select_tab(1)
            selenium_driver.set_page(page['html'])

            if xpath != '':
                element = selenium_driver.get_element(xpath)
                print(selenium_driver.get_element_corners(element))
                print(selenium_driver.get_font_size(element))
                print(selenium_driver.get_font_family(element))
                print(selenium_driver.get_font_weight(element))
                print(selenium_driver.get_text_alignment(element))
                print(selenium_driver.get_color(element))

            break

    @ignore_warnings
    def test_get_element_min_distances(self):
        domain = 'movie'
        site = 'imdb'
        xpath1 = '/html/body/div[2]/div/div[3]/div[1]/div[1]/div[1]/div/table/tbody/tr[1]/td[2]/div[4]/h4'
        xpath2 = '/html/body/div[2]/div/div[3]/div[1]/div[1]/div[1]/div/table/tbody/tr[1]/td[2]/div[4]/a'

        template = domain + '-' + site

        for page in page_service.get_all(template=template):
            print('{} - {}'.format(page['site'], page['file_name']))

            parsed_page = ParsedPage(page['html'])
            print(parsed_page.get_nodes_xpath(xpath1)[0].text)
            print(parsed_page.get_nodes_xpath(xpath2)[0].text)

            selenium_driver.open_tab(1)
            selenium_driver.select_tab(1)
            selenium_driver.set_page(page['html'])

            if xpath1 != '':
                print(selenium_driver.get_elements_distances(xpath1, xpath2))

            break

    @ignore_warnings
    def test_get_element_between_nodes(self):
        domain = 'movie'
        site = 'imdb'
        xpath1 = '/html/body/div[2]/div/div[3]/div[1]/div[1]/div[1]/div/table/tbody/tr[1]/td[2]/div[1]/a'
        xpath2 = '/html/body/div[2]/div/div[3]/div[1]/div[1]/div[1]/div/table/tbody/tr[1]/td[2]/div[3]/div/div/span[4]'

        template = domain + '-' + site

        for page in page_service.get_all(template=template):
            print('{} - {}'.format(page['site'], page['file_name']))

            parsed_page = ParsedPage(page['html'])
            print(parsed_page.get_nodes_xpath(xpath1)[0].text)
            print(parsed_page.get_nodes_xpath(xpath2)[0].text)

            selenium_driver.open_tab(1)
            selenium_driver.select_tab(1)
            selenium_driver.set_page(page['html'])

            if xpath1 != '':
                middle_elements = selenium_driver.get_elements_in_the_middle(xpath1, xpath2)
                selenium_driver.color_elements(middle_elements)
                selenium_driver.color_elements([xpath1, xpath2])


            break

    @ignore_warnings
    def test_new_labels(self):
        domain = 'movie'
        sites = []
        topics = []
        pages_for_template = 1

        if len(sites) == 0:
            templates = page_service.get_all_field_values('template')
        else:
            templates = [domain + '-' + site for site in sites]

        browser_tab_count = 1
        template_pages_count = 0
        for template in templates:
            for page in page_service.get_all(template=template):
                if 'new_labels' in page and len(page['new_labels']) > 0:
                    if len(topics) > 0 and page['topic_text'] not in topics:
                        continue

                    print('{} - {}'.format(page['site'], page['file_name']))
                    selenium_driver.open_tab(browser_tab_count)
                    selenium_driver.select_tab(browser_tab_count)
                    selenium_driver.set_page(page['html'])

                    new_labels = page['new_labels']
                    new_labels_by_pred = defaultdict(list)
                    for new_label in new_labels:
                        obj_xpath = new_label['obj_xpath']
                        pred_xpath = new_label['pred_xpath']
                        new_labels_by_pred[pred_xpath].append(obj_xpath)

                    for pred_xpath, objs_xpaths in new_labels_by_pred.items():
                        objs_xpaths.append(pred_xpath)
                        selenium_driver.color_elements(objs_xpaths)

                    browser_tab_count += 1
                    template_pages_count += 1
                if template_pages_count >= pages_for_template:
                    break

            template_pages_count = 0

    @ignore_warnings
    def test_candidate_objs(self):
        domain = 'monitor'
        sites = []
        topics = []
        pages_for_template = 1

        if len(sites) == 0:
            templates = page_service.get_all_field_values('template')
            templates = list(filter(lambda template: domain in template, templates))
        else:
            templates = [domain + '-' + site for site in sites]

        browser_tab_count = 1
        template_pages_count = 0
        for template in templates:
            for page in page_service.get_all(template=template):
                if 'candidate_pairs' in page and len(page['candidate_pairs']) > 0:
                    if len(topics) > 0 and page['topic_text'] not in topics:
                        continue

                    print('{} - {}'.format(page['site'], page['file_name']))
                    selenium_driver.open_tab(browser_tab_count)
                    selenium_driver.select_tab(browser_tab_count)
                    selenium_driver.set_page(page['html'])

                    candidates_objs = page['candidate_pairs'].keys()
                    selenium_driver.color_elements(candidates_objs)

                    browser_tab_count += 1
                    template_pages_count += 1
                if template_pages_count >= pages_for_template:
                    break

            template_pages_count = 0




if __name__ == '__main__':
    unittest.main()
    mongodb.disconnect()
    neo4j.disconnect()
