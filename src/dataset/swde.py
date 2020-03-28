import json
import src.utils.files as file
import src.utils.string_utils as string_utils
import src.html.webpage_beautifulsoup as bs
import src.utils.elapsed_timer as timer
from collections import defaultdict
from src.html.webpage_lxml import ParsedPage


def import_site(mongodb, collection, site_annotations, domain, site_dir, site_name, status_printer, selenium_driver, topics_to_import=None, max_number_of_pages=None, debug=False):
    webpages_paths = file.get_files_into_dir(site_dir, full_path=True)
    pages_count = 0
    for webpage_path in webpages_paths:
        webpage_file_name = webpage_path.split('/')[-1]
        annotations = site_annotations[webpage_file_name]

        if 'topic_entity_name' in annotations:
            topic = annotations['topic_entity_name'][0]
        else:
            continue

        # topic_to_import can define a list of topics. only pages with one of that topics as subject will be imported
        if topics_to_import is not None and not any(string_utils.compare_string(topic, topic_to_import, clean=True) for topic_to_import in topics_to_import):
            continue

        with open(webpage_path, 'r', encoding="utf8") as webpage_file:
            html = webpage_file.read()

            # beautiful soup rimuove i <style> quindi li si salva e li si rimette dopo
            styles = []
            parsedPage = ParsedPage(html)
            style_nodes = parsedPage.get_nodes_xpath('//style', clean=False)
            for style_node in style_nodes:
                style = style_node.text
                #style = string_utils.remove_substring_by_regex(style, '\\*[^\\*]+\\*')
                styles.append(style)

            web_page = bs.ParsedPage(html)
            url = web_page.get_tags('base')[0]['href']
            web_page.remove_tags('base')
            html = web_page.get_html()

            # if we don't correct html with browser, xpath retrived by lxml could fail
            selenium_driver.set_page(html)
            html = selenium_driver.get_corrected_html()

            template = domain + '-' + site_name

            webpage_file_name = webpage_path.split('/')[-1]
            annotations = site_annotations[webpage_file_name]

            # riaggiungi gli styles
            all_styles_string = ''
            for style in styles:
                style = '\n <style>{}</style>'.format(style)
                all_styles_string += style
            html = string_utils.insert_string_after_substring(html, '<head>', all_styles_string)
            #print(html)

            mongodb.insert_doc(collection, {'url': url, 'html': html, 'site': site_name, 'template': template, 'domain': domain, 'file_name': webpage_file_name, 'ground_truth': annotations})
            pages_count += 1

            status_printer.operation_done()

        if max_number_of_pages is not None and pages_count >= max_number_of_pages:
            break

    return pages_count


def load_extended_site_annotations(annotation_file_path):
    try:
        with open(annotation_file_path, 'r', encoding="utf8") as annotation_file:
            annotations = json.load(annotation_file)
    except FileNotFoundError:
        return None

    for webpage_file, attributes in annotations.items():
        clean_attributes = defaultdict(list)

        for preds, objs in attributes.items():
            objs = [string_utils.clean_string(obj) for obj in objs]

            if '|' in preds:
                preds = preds.split('|')
                for pred in preds:
                    pred = string_utils.clean_string(pred)
                    clean_attributes[pred].extend(objs)
            else:
                preds = string_utils.clean_string(preds)
                clean_attributes[preds].extend(objs)

        # for pred, objs in attributes.items():
        #     if '|' in pred:
        #         pred = pred.split('|')[-1]
        #     pred = string_utils.clean_string(pred)
        #     objs = [string_utils.clean_string(obj) for obj in objs]
        #     clean_attributes[pred].extend(objs)

            annotations[webpage_file] = clean_attributes
    return annotations


def import_domain(mongodb, collection, domain_name, selenium_driver, sites=None, topics_to_import=None, max_number_of_webpages=None, debug=False):
    print('   import web_pages: {}'.format(domain_name))

    domain_dir = 'input_data/swde/webpages/{}'.format(domain_name)
    domain_annotation_dir = 'input_data/swde_extended/{}'.format(domain_name)

    sites_dirs = file.get_files_into_dir(domain_dir, full_path=True)
    sites_annotation_files = file.get_files_into_dir(domain_annotation_dir, full_path=True)

    if sites is None:  # get all
        sites = []
        for site_dir in sites_annotation_files:
            site_name = string_utils.get_substring_by_regex(site_dir, '-.*\(')[1:-1]
            sites.append(site_name)
        print('      site number: {}'.format(len(sites)))

    # get max number of pages foreach site
    if max_number_of_webpages is not None:
        max_pages_for_site = int(max_number_of_webpages / len(sites))
        print('      max number of pages foreach site: {}'.format(max_pages_for_site))
    else:
        max_pages_for_site = None

    # import web pages from all selected sites
    if topics_to_import is not None:
        total_operation_count = len(topics_to_import) * len(sites)
    elif max_number_of_webpages is not None:
        total_operation_count = max_number_of_webpages
    else:
        total_operation_count = sum(len(file.get_all_subfiles(site_dir)) for site_dir in sites_dirs)

    status_printer = timer.StatusPrinter(total_operation_count, padding='      ')
    imported_pages_count = {}
    for site in sites:
        try:
            webpages_dir_path = [webpages_dir_path for webpages_dir_path in sites_dirs if site in webpages_dir_path][0]
            annotation_file_path = [annotation_file_path for annotation_file_path in sites_annotation_files if site in annotation_file_path][0]
        except IndexError:
            # there are not annotations for that file
            continue

        # webpages_dir_path = '{}/{}-{}(2000)/'.format(domain_dir, domain_name, site)
        # annotation_file_path = '{}/{}-{}(2000).json'.format(domain_annotation_dir, domain_name, site)

        site_annotations = load_extended_site_annotations(annotation_file_path)
        if site_annotations is not None:
            pages_count = import_site(mongodb, collection, site_annotations, domain_name, webpages_dir_path, site, status_printer, selenium_driver, topics_to_import, max_pages_for_site, debug)
            imported_pages_count[site] = pages_count

    status_printer.finish()

    if debug:
        print('      imported pages count:')
        for site, pages_count in imported_pages_count.items():
            print('         {}-{}: {}'.format(domain_name, site, pages_count))

        print('      done')


def import_dataset(mongodb, selenium_driver, cfg):
    print('import dataset mongodb...')

    debug = cfg['swde']['debug']
    max_number_of_webpages = cfg['swde']['max_number_of_webpages']
    sites = cfg['swde']['sites']
    topics_to_import = cfg['swde']["topics_to_import"]

    if max_number_of_webpages == 0:
        max_number_of_webpages = None

    if len(sites)==0:
        sites = None

    if len(topics_to_import)==0:
        topics_to_import = None

    collection = cfg['swde']['collection']
    mongodb.drop_collection(collection)

    for domain in cfg['swde']['domain']:
        import_domain(mongodb, collection, domain, selenium_driver, sites, topics_to_import, max_number_of_webpages, debug)
    print('   done')
