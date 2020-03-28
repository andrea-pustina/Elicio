import src.utils.elapsed_timer as timer
from src.html.webpage_lxml import ParsedPage
import src.utils.string_utils as string_utils
from selenium.common.exceptions import NoSuchElementException
import src.utils.compressor as compressor


def get_node_features(node_xpath, parsed_page, selenium_driver, other_node_xpath=None):
    selenium_pred_elem = selenium_driver.get_element(node_xpath)

    features = {}

    features['dom'] = {'font_family': selenium_driver.get_font_family(selenium_pred_elem),
                       'font_size': selenium_driver.get_font_size(selenium_pred_elem),
                       'font_weight': selenium_driver.get_font_weight(selenium_pred_elem),
                       'text_alignment': selenium_driver.get_text_alignment(selenium_pred_elem),
                       'color': selenium_driver.get_color(selenium_pred_elem)}

    # other_node -> obj, node -> pred
    if other_node_xpath is not None:
        features['distances'] = selenium_driver.get_elements_distances(node_xpath, other_node_xpath)

        features['graphic'] = {}
        features['graphic']['is_above_and_on_left'] = selenium_driver.is_above_and_on_the_left(node_xpath, other_node_xpath)

        features['dom_distance'] = parsed_page.get_node_dom_distance(node_xpath, other_node_xpath)

    #print(features)
    return features


def get_best_pred_candidates_from_nodes_list(curr_node, curr_node_freq, nodes_list, parsed_page, page_html, webpage_template, webpage_index, pages_count, number_of_candidates, selenium_driver, cfg, compute_pred_distance):
    min_pred_candidates_freq = cfg['candidate_pred_obj_pairs']['min_pred_candidates_freq']
    best_pred_candidates = []

    curr_node_xpath = parsed_page.get_xpath(curr_node)
    if 'svg' in curr_node_xpath or 'noscript' in curr_node_xpath:
        #print('discarding svg node')
        return []
    # not pred_candidate.text.isdigit() and \

    found = 0
    for pred_candidate in nodes_list:
        pred_candidate_xpath = parsed_page.get_xpath(pred_candidate)
        if 'svg' in pred_candidate_xpath or 'noscript' in pred_candidate_xpath:
            # print('discarding svg node')
            continue

        try:
            pred_candidate_freq = webpage_index.get_term_freq(webpage_template, pred_candidate.text, normalized=True)
            if pred_candidate_freq >= min_pred_candidates_freq and \
               pred_candidate_freq > curr_node_freq and \
               selenium_driver.is_above_and_on_the_left(pred_candidate_xpath, curr_node_xpath) and \
               len(pred_candidate.text) > 2:
                found += 1

                if compute_pred_distance:
                    distance = selenium_driver.get_elements_distance(curr_node_xpath, pred_candidate_xpath, normalized=True, increase_vertical_relevance=True)
                    best_pred_candidates.append({'node': pred_candidate, 'text': pred_candidate.text, 'distance': distance})
                else:
                    best_pred_candidates.append({'node': pred_candidate, 'text': pred_candidate.text})
        except NoSuchElementException:
            pass

        if found >= number_of_candidates:
            break

    return best_pred_candidates


def generate_pred_candidates_foreach_obj(parsed_page, page_html, text_nodes, webpage_template, webpage_index, pages_count, selenium_driver, cfg, compute_pred_distance=True):
    """
    generate all candidate predicates foreach topic related object.
    """
    candidate_preds_foreach_obj = cfg['candidate_pred_obj_pairs']['candidate_preds_foreach_obj']

    for text_node, metadata in text_nodes.items():
        curr_node = text_node
        curr_node_freq = webpage_index.get_term_freq(webpage_template, text_node.text, normalized=True)

        pred_candidates = []

        # get pred candidates from previous nodes
        previous_nodes = parsed_page.get_previous_text_nodes(text_node, clean=True)
        best_pred_candidates = get_best_pred_candidates_from_nodes_list(curr_node, curr_node_freq, previous_nodes, parsed_page, page_html, webpage_template, webpage_index, pages_count, candidate_preds_foreach_obj, selenium_driver, cfg, compute_pred_distance)
        pred_candidates.extend(best_pred_candidates)

        text_nodes[text_node]['pred_candidates'] = pred_candidates

    return text_nodes


def get_topic_related_text_nodes(entity_service, webpage_topic_id, webpage_topic_text, parsed_page, page_entities):
    # get ids of entities related in the kb to the webpage_topic
    topic_related_objs = page_entities[webpage_topic_id]['related_objs']

    topic_related_text_nodes = {}
    for obj_id in topic_related_objs.keys():
        if obj_id in page_entities:
            obj_text = topic_related_objs[obj_id]['obj_text']

            if webpage_topic_text in obj_text:
                continue

            relation_types = topic_related_objs[obj_id]['rel_types']       # relations webpage_topic -> obj

            obj_nodes_xpaths = page_entities[obj_id]['xpaths']
            obj_nodes = [parsed_page.get_nodes_xpath(node_xpath, clean=True)[0] for node_xpath in obj_nodes_xpaths]

            for obj_node in obj_nodes:
                topic_related_text_nodes[obj_node] = {'obj_id': obj_id, 'obj_text': obj_text, 'rel_types': relation_types}

    return topic_related_text_nodes


def get_pred_candidates_foreach_obj(page_service, entity_service, webpage_index, selenium_driver, cfg):
    domains = cfg['candidate_pred_obj_pairs']['domains']
    templates = cfg['candidate_pred_obj_pairs']['templates']

    if len(templates) > 0:
        templates = templates
    elif len(domains) > 0:
        templates = page_service.get_all_field_values('template')
        templates = list(filter(lambda template: any([domain in template for domain in domains]), templates))
    else:
        templates = page_service.get_all_field_values('template')

    pages_count = 0
    for template in templates:
        pages_count += page_service.count_all(template=template)
    status_printer = timer.StatusPrinter(pages_count, padding='         ')
    print('get pred candidates foreach obj...')

    for template in templates:
        debug = cfg['candidate_pred_obj_pairs']['debug']

        webpages_cursor = page_service.get_all(template=template, no_cursor_timeout=True)
        for webpage in webpages_cursor:
            if webpage['topic_id'] is None:
                continue

            parsed_page = ParsedPage(webpage['html'])
            selenium_driver.set_page(webpage['html'])

            webpage_template = webpage['template']
            webpage_topic_id = webpage['topic_id']
            webpage_topic_text = webpage['topic_text']

            page_entities = compressor.decompress_obj(webpage['page_entities'])

            # ==================  get candidate preds foreach object that in the kb is related to webpage topic

            # get only text nodes in the page that are related to the page_topic
            # return: {node_obj_1: {obj_id: '14785', obj_text: 'spielberg', rel_type_id: '123', rel_type_text:'is a '}, ...}
            topic_related_text_nodes = get_topic_related_text_nodes(entity_service, webpage_topic_id, webpage_topic_text, parsed_page, page_entities)

            # filter text nodes that are in a <p></p> tag
            topic_related_text_nodes = {node: node_data for (node,node_data) in topic_related_text_nodes.items() if not parsed_page.check_if_node_has_parent_with_tag('p', node)}

            # filter text node that contains the topic
            topic_related_text_nodes = {node: node_data for (node, node_data) in topic_related_text_nodes.items() if not string_utils.compare_string(node_data['obj_text'], webpage['topic_text'])}

            # add pred candidates foreach obj_node
            # return: {node_obj_1: {pred_candidates: [{node: lxml_node1, text: 'bruce willis'}, obj_id: '123', ...] ,...}, ...}
            topic_related_text_nodes = generate_pred_candidates_foreach_obj(parsed_page, webpage['html'], topic_related_text_nodes, webpage_template, webpage_index, pages_count, selenium_driver, cfg)

            if debug:
                print('         ' + webpage['ground_truth']['topic_entity_name'][0])
                print('            site: {}'.format(webpage['site']))
                print('            file: {}'.format(webpage['file_name']))
                print('            topic: {} ({})'.format(webpage['topic_text'], webpage_topic_id))

                print('            topic_related_text_nodes: ', end='')
                for obj, obj_metadata in topic_related_text_nodes.items():
                    print('"{}" id:{} rels:{}: ['.format(obj.text, obj_metadata['obj_id'], list(obj_metadata['rel_types'].values())), end='')
                    for pred_candidate in obj_metadata['pred_candidates']:
                        print('"{}", '.format(pred_candidate['text']), end='')
                    print('] \n                                   ', end='')
                print('')

            # convert all lxml nodes to xpath
            topic_related_text_nodes_xpath = parsed_page.convert_all_lxml_nodes_to_xpath_in_nested_dict(
                topic_related_text_nodes)

            # save in mongodb
            webpage['topic_related_candidate_pairs'] = topic_related_text_nodes_xpath

            # ==================  get candidate preds foreach object in the webpage with features
            text_nodes = parsed_page.get_all_text_nodes(clean=True)

            # filter too common text nodes (they are not objs)
            text_nodes = [node for node in text_nodes if webpage_index.get_term_freq(webpage_template, node.text , normalized=True) <= cfg['candidate_pred_obj_pairs']['max_obj_candidates_freq']]

            # filter text nodes that are in a <p></p> tag
            text_nodes = [node for node in text_nodes if not parsed_page.check_if_node_has_parent_with_tag('p', node)]

            # filter text node that contains the webpage topic
            text_nodes = [node for node in text_nodes if not string_utils.compare_string(node.text, webpage['topic_text'])]

            # change text_nodes format
            text_nodes = {node: {'obj_text': node.text} for node in text_nodes}

            # get pred candidates foreach obj_node
            # return: {node_obj_1: {pred_candidates: [{node: lxml_node1, text: 'bruce willis'}] ,...}, ...}
            candidate_pairs = generate_pred_candidates_foreach_obj(parsed_page, webpage['html'], text_nodes, webpage_template, webpage_index, pages_count, selenium_driver, cfg, compute_pred_distance=False)

            # convert all lxml nodes to xpath
            candidate_pairs = parsed_page.convert_all_lxml_nodes_to_xpath_in_nested_dict(candidate_pairs)

            # remove all nodes with 'svg' in xpath
            candidate_pairs2 = {}
            for obj_xpath, obj_metadata in candidate_pairs.items():
                if 'svg' in obj_xpath or 'noscript' in obj_xpath or any(['svg' in pred_candidate['node'] for pred_candidate in obj_metadata['pred_candidates']]) or any(['noscript' in pred_candidate['node'] for pred_candidate in obj_metadata['pred_candidates']]):
                    continue
                candidate_pairs2[obj_xpath] = obj_metadata
            candidate_pairs = candidate_pairs2

            # add features
            objs_to_delete = []
            for obj_xpath, obj_metadata in candidate_pairs.items():
                try:
                    obj_metadata['features'] = get_node_features(obj_xpath, parsed_page, selenium_driver)
                except NoSuchElementException:
                    objs_to_delete.append(obj_xpath)
                    print('deleting obj candidate! {} - {}'.format(webpage['file_name'], obj_xpath))
                    continue

                preds_to_delete = []
                for pred in obj_metadata['pred_candidates']:
                    try:
                        pred['features'] = get_node_features(pred['node'], parsed_page, selenium_driver, other_node_xpath=obj_xpath)
                    except NoSuchElementException:
                        preds_to_delete.append(pred)
                        print('deleting pred candidate! {} - {}'.format(webpage['file_name'], pred))

                for pred_to_delete in preds_to_delete:
                    del obj_metadata['pred_candidates'][pred_to_delete]

            for obj_to_delete in objs_to_delete:
                del candidate_pairs[obj_to_delete]


            # save in mongodb
            webpage['candidate_pairs'] = candidate_pairs

            page_service.save(webpage)

            if not debug:
                status_printer.operation_done()

        webpages_cursor.close()
    status_printer.finish()
