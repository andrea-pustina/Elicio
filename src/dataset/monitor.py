import json
import src.utils.files as file
import src.utils.string_utils as string_utils
import src.html.webpage_beautifulsoup as bs
import src.utils.elapsed_timer as timer
from collections import defaultdict
import src.utils.iterators as iterators
from src.html.webpage_lxml import ParsedPage


def import_dataset(mongodb, selenium_driver, cfg):
    print('import dataset mongodb...')

    collection = cfg['swde']['collection']
    mongodb.drop_collection(collection)

    dataset_dir = 'input_data/monitor_dataset'
    site_dirs = file.get_files_into_dir(dataset_dir, full_path=True)

    sites = cfg['monitor']['sites']

    max_number_of_webpages = cfg['monitor']['max_number_of_webpages']
    if max_number_of_webpages > 0:
        if len(sites)>0:
            len_sites = len(sites)
        else:
            len_sites = len(site_dirs)

        max_pages_for_site = int(max_number_of_webpages / len_sites)
        total_operation_count = max_number_of_webpages
        print('      max number of pages foreach site: {}'.format(max_pages_for_site))
    else:
        max_pages_for_site = None
        total_operation_count = len(file.get_all_subfiles(dataset_dir)) / 2

    status_printer = timer.StatusPrinter(total_operation_count, padding='      ')

    for site_dir in site_dirs:
        if 'getprice.com' in site_dir:                  # this has been used for kb
            continue

        site_name = site_dir.split('/')[-1]
        if len(sites) > 0 and site_name not in sites:
            continue

        all_site_files = file.get_files_into_dir(site_dir, full_path=True)

        webpages_files_paths = list(filter(lambda x: '.html' in x, all_site_files))
        groundtruth_files_paths = list(filter(lambda x: '.json' in x, all_site_files))

        # add webpages html
        webpage_count = 0
        for webpage_file_path in webpages_files_paths:
            if webpage_count >= max_pages_for_site:
                break

            webpage_file_name = webpage_file_path.split('/')[-1][:-5]
            groundtruth_file_path = [groundtruth_file_path for groundtruth_file_path in groundtruth_files_paths if webpage_file_name in groundtruth_file_path][0]

            with open(webpage_file_path, 'r', encoding="utf8") as webpage_file:
                with open(groundtruth_file_path, 'r', encoding="utf8") as groundtruth_file:
                    html = webpage_file.read()
                    html = ParsedPage.clean_html(html)

                    # if we don't correct html with browser, xpath retrived by lxml could fail
                    selenium_driver.set_page(html)
                    html = selenium_driver.get_corrected_html()

                    domain = 'monitor'
                    template = 'monitor-' + site_name
                    url = site_name + '/' + webpage_file_name

                    # print(groundtruth_file.read())
                    groundtruth = json.loads(groundtruth_file.read())
                    groundtruth['topic_entity_name'] = groundtruth['<page title>']
                    groundtruth = iterators.map_nested_dicts(groundtruth, lambda text: string_utils.clean_string(text), map_also_dict_keys=True)
                    groundtruth = iterators.map_nested_dicts(groundtruth, lambda text: [text], map_also_dict_keys=False)
                    del groundtruth['<page title>']

                    mongodb.insert_doc(collection,
                                       {'url': url, 'html': html, 'site': site_name, 'template': template, 'domain': domain,
                                        'file_name': webpage_file_name, 'ground_truth': groundtruth})

                    status_printer.operation_done()
                    webpage_count += 1

    status_printer.finish()




    print('   done')
