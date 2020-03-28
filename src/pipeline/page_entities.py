from src.html.webpage_lxml import ParsedPage
import src.utils.elapsed_timer as timer
import src.utils.string_utils as string_utils
import src.utils.compressor as compressor



def drop_too_common_textnodes(threshold, text_nodes, webpage_index, webpage_template):
    # skip text_node where text is too much common across webpages of the same template
    res_text_node = []
    for text_node in text_nodes:
        text = text_node.text
        normalized_freq = webpage_index.get_term_freq(webpage_template, text, normalized=True)
        if normalized_freq < threshold:
            res_text_node.append(text_node)
    return res_text_node


def filter_text_nodes(text_nodes, cfg, webpage_index, webpage_template):
    # filter text_nodes where len(text) <= 2
    text_nodes = list(filter(lambda node: len(node.text) > 2, text_nodes))

    # filter too common text_nodes (by webpage template)
    if cfg['page_entities']['ignore_too_common_text_node']:
        threshold = cfg['page_entities']['common_text_node_freq_threshold']
        text_nodes = drop_too_common_textnodes(threshold, text_nodes, webpage_index, webpage_template)

    return text_nodes


def compute_page_entities(page_service, entity_service, webpage_index, cfg):
    print('compute page entities...')
    debug = cfg['page_entities']['debug']
    overwrite_page_entities = cfg['page_entities']['overwrite_page_entities']

    total_operation_count = page_service.count_all()
    status_printer = timer.StatusPrinter(total_operation_count, padding='      ', avoid_use_of_timer=False)

    webpages = page_service.get_all(no_cursor_timeout=True)
    for webpage in webpages:

        # if not webpage['template']=='monitor-www.nexus-t.co.uk' or not webpage['file_name']=='141':
        #     continue

        # if overwrite_page_entities=false don't overwrite page entities
        if overwrite_page_entities or 'page_entities' not in webpage:
            parsed_page = ParsedPage(webpage['html'])
            all_text_nodes = parsed_page.get_all_text_nodes(clean=True)

            # drop some text_nodes that probably are not objs
            text_nodes = filter_text_nodes(all_text_nodes, cfg, webpage_index, webpage['template'])

            # get entities in the page
            page_entities = {}
            for text_node in text_nodes:
                text_node_xpath = parsed_page.get_xpath(text_node)
                text_node_text = string_utils.clean_string(text_node.text)
                text_node_entities = entity_service.search_entities(text_node_text, strict=False)     # a text node could match with more than a entity in the kb

                for entity in text_node_entities:
                    entity_id = entity['node_id']
                    if not entity_id in page_entities:
                        page_entities[entity_id] = {}
                        page_entities[entity_id]['xpaths'] = []

                    page_entities[entity_id]['text'] = entity['node_text']
                    page_entities[entity_id]['xpaths'].append(text_node_xpath)

            # get related objects foreach page entity
            for entity_id in page_entities.keys():
                related_objs = entity_service.get_related_objects(entity_id)
                page_entities[entity_id]['related_objs'] = related_objs

            webpage['page_entities'] = compressor.compress_obj(page_entities)
            page_service.save(webpage)

            if debug:
                print('   {} - {}'.format(webpage['site'], webpage['file_name']))
                print('      text_nodes: {}'.format([text_node.text for text_node in all_text_nodes]))
                print('      filtered_text_nodes: {}'.format([text_node.text for text_node in text_nodes]))
                print('      page_entities: {}'.format([page_entity['text'] for page_entity in page_entities.values()]))
                print('      page_entities: {}'.format(page_entities))

        if not debug:
            status_printer.operation_done()

    status_printer.finish()
    webpages.close()


# def add_new_related_entities(page_service, entity, new_related_entities):
#     webpages = page_service.get_all(no_cursor_timeout=True)
#     for webpage in webpages:
#
#         page_entities = compressor.decompress_obj(webpage['page_entities'])
#         if entity in page_entities.keys():
#             page_entities[entity][]
#
#             webpage['page_entities'] = compressor.compress_obj(page_entities)



