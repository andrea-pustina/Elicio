import src.utils.elapsed_timer as timer
import src.utils.string_utils as string_utils
from collections import defaultdict
import src.utils.iterators as iterators
import src.utils.compressor as compressor


def calculate_candidate_pages_topic(page_service, entity_service, webpage_index, debug, cfg, domains, hint_xpaths=None, topics_to_drop=None):
    total_operation_count = page_service.count_all()
    status_printer = timer.StatusPrinter(total_operation_count, padding='      ')

    for domain in domains:
        webpages = page_service.get_all(domain=domain, no_cursor_timeout=True)
        for webpage in webpages:
            webpage_template = webpage['template']

            webpage_page_entities = compressor.decompress_obj(webpage['page_entities'])

            # page_entities: [(entity_id, node_xpath), ...]
            page_entities = []
            for page_entity_id, page_entity_metadata in webpage_page_entities.items():
                for xpath in page_entity_metadata['xpaths']:
                    page_entities.append((page_entity_id, xpath))
            page_entities = list(set(page_entities))

            # # page_entities: {xpath: [entity_id, entity_id2), ...}
            # page_entities_by_xpath = defaultdict(list)
            # for page_entity_id, page_entity_metadata in webpage_page_entities.items():
            #     for xpath in page_entity_metadata['xpaths']:
            #         page_entities_by_xpath[xpath].append(page_entity_id)
            #

            page_entities_ids = set([page_entity_id for (page_entity_id, node_xpath) in page_entities])

            tot = len(page_entities)
            # calculate score foreach page_entity
            for (page_entity_id, node_xpath) in page_entities:
                related_objs = webpage_page_entities[page_entity_id]['related_objs']
                related_objs_ids = set(related_objs.keys())

                # other_page_entities_ids are entities that were not found from the same node_xpath
                # (remember that from a node can be found many entities in the kb)
                #other_page_entities_ids = set([page_entity_id for (page_entity_id, node_xpath2) in page_entities if node_xpath2!=node_xpath])
                #other_page_entities_ids = page_entities_ids.difference(page_entities_by_xpath[node_xpath])
                other_page_entities_ids = page_entities_ids

                try:
                    score = len(other_page_entities_ids.intersection(related_objs_ids)) / len(other_page_entities_ids.union(related_objs_ids))
                except ZeroDivisionError:
                    score = 0

                if hint_xpaths is not None and webpage_template in hint_xpaths and node_xpath in hint_xpaths[webpage_template]:
                    score = score * hint_xpaths[webpage_template][node_xpath]

                if 'score' not in webpage_page_entities[page_entity_id]:
                    webpage_page_entities[page_entity_id]['score'] = 0

                if score > webpage_page_entities[page_entity_id]['score']:
                    webpage_page_entities[page_entity_id]['score'] = score

                #if string_utils.compare_string('george lucas', page_entities[page_entity_id]['text']):
                #    print('{} -> {}'.format(page_entities[page_entity_id]['text'], score))

                # tot -= 1
                # print(tot)

            # best_topic_candidate = entity with max score
            best_score = -1
            best_page_entity_id = None
            for page_entity_id in webpage_page_entities.keys():
                page_entity_text = webpage_page_entities[page_entity_id]['text']
                page_entity_score = webpage_page_entities[page_entity_id]['score']
                if page_entity_score > best_score:
                    if topics_to_drop is not None and webpage_template in topics_to_drop and page_entity_text in topics_to_drop[webpage_template]:
                        continue

                    if cfg['topic_identification']['use_ground_truth']:
                        webpage_topic_true = webpage['ground_truth']['topic_entity_name'][0]
                        if not string_utils.compare_string_meaning(webpage_topic_true, page_entity_text):
                            continue

                    best_score = page_entity_score
                    best_page_entity_id = page_entity_id

            if best_page_entity_id is not None:
                # now we have page topic
                topic_id = best_page_entity_id
                topic_text = webpage_page_entities[topic_id]['text']
                topic_score = webpage_page_entities[topic_id]['score']
            else:
                topic_id = None
                topic_text = None
                topic_score = None

            webpage['topic_id'] = topic_id
            webpage['topic_text'] = topic_text
            page_service.save(webpage)

            if debug:
                print('      ' + webpage['ground_truth']['topic_entity_name'][0])
                print('         site: {}'.format(webpage['site']))
                print('         file: {}'.format(webpage['file_name']))
                print('         topic: {} [id: {}, score: {}]'.format(topic_text, topic_id, topic_score))
            else:
                status_printer.operation_done()

        webpages.close()


def evaluate_results(page_service, debug, domain=None):
    true_positive = 0
    false_positive = 0
    unknown = 0

    if domain is not None:
        webpages = page_service.get_all(domain=domain)
    else:
        webpages = page_service.get_all()

    for webpage in webpages:
        if 'topic_id' not in webpage or webpage['topic_id'] is None:
            unknown += 1
            continue

        webpage_topic = webpage['topic_text']
        webpage_topic_true = webpage['ground_truth']['topic_entity_name'][0]

        if string_utils.compare_string(webpage_topic, webpage_topic_true, clean=True):
            true_positive += 1
        else:
            false_positive += 1

    if true_positive == 0:
        precision = 0
        recall = 0
    else:
        precision = true_positive / (true_positive + false_positive)
        recall = true_positive / (true_positive + unknown)

    print('   Evaluation ({})'.format(domain if domain else 'all'))
    print('      precision: {}'.format(precision))
    print('      recall: {}'.format(recall))

    # count pages with topic foreach site
    if domain is None:
        webpages = page_service.get_all(domain=domain)
    else:
        webpages = page_service.get_all()

    pages_count_by_site = defaultdict(lambda: 0)
    for webpage in webpages:
        if 'topic_id' in webpage and webpage['topic_id'] is not None:
            pages_count_by_site[webpage['site']] += 1

    print('      pages_with_topic_count_by_site {}'.format(dict(pages_count_by_site)))


def identify_topic(page_service, entity_service, webpage_index, cfg):
    print('topic identification...')
    debug = cfg['topic_identification']['debug']

    # page_service.remove_field_all('topic_id')
    # page_service.remove_field_all('topic_text')

    domains = cfg['topic_identification']['domains']
    if len(domains) == 0:
        domains = page_service.get_all_field_values('domain')

    for domain in domains:
        for page in page_service.get_all(domain=domain):
            if 'topic_id' in page:
                page['topic_id'] = None
            if 'topic_text' in page:
                page['topic_text'] = None
            page_service.save(page)

        print('   calculate candidate topic ({})'.format(domain))
        calculate_candidate_pages_topic(page_service, entity_service, webpage_index, debug, cfg, [domain])

        print('   compute candidate topic frequency (by template)')
        templates = page_service.get_all_field_values('template')
        templates = list(filter(lambda template: domain in template, templates))

        topic_freq = defaultdict(lambda: defaultdict(lambda: 0))
        for template in templates:
            for page in page_service.get_all(template=template):
                page_topic = page['topic_text']
                topic_freq[template][page_topic] += 1

        # drop topics that were found for more than 3 pages
        topic_to_drop = defaultdict(list)
        for template, pages_topics_freqs in topic_freq.items():
            for topic, freq in pages_topics_freqs.items():
                if freq >= 3:
                    topic_to_drop[template].append(topic)

        if debug:
            print('      topics_freq: {}'.format(dict(topic_freq)))
            print('      topics_to_drop: {}'.format(dict(topic_to_drop)))

        # get topics xpath frequencies by template
        topics_xpath_freqs = defaultdict(list)
        for page in page_service.get_all(domain=domain):
            if page['topic_id'] is None:
                    continue

            topic_id = page['topic_id']
            page_entities = compressor.decompress_obj(page['page_entities'])
            topic_xpaths = page_entities[topic_id]['xpaths']
            topics_xpath_freqs[page['template']].extend(topic_xpaths)
        topics_xpath_freqs = {template: iterators.get_elements_frequency(xpaths) for template, xpaths in topics_xpath_freqs.items()}

        # print(topics_xpath_freqs)

        print('   calculate topic ')
        calculate_candidate_pages_topic(page_service, entity_service, webpage_index, debug, cfg, [domain], topics_to_drop=topic_to_drop, hint_xpaths=topics_xpath_freqs)

        evaluate_results(page_service, debug, domain)

    evaluate_results(page_service, debug)





"""
    print('   get best xpath')
    topics_xpaths = []
    for page in page_service.get_all():
        topics_xpaths.extend(page['topic_xpath'])
    most_common_xpath = max(set(topics_xpaths), key=topics_xpaths.count)
    most_common_xpath = [most_common_xpath]
    print('      most_common_xpath: {}'.format(most_common_xpath))

    print('   calculate topic')
    calculate_candidate_pages_topic(page_service, entity_service, webpage_index, hint_xpaths=most_common_xpath)

    print('   done')
"""

