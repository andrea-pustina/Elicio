from src.html.webpage_lxml import ParsedPage
import src.utils.string_utils as string_utils
import src.service.webpage_service as webpage_service
import src.pipeline.seed_labels.pred_synonims as pred_synonims
from collections import defaultdict
import src.utils.plotter as plotter
import src.utils.iterators as iterators


def evaluate_results(page_service, entity_service, debug, template=None, domain=None):
    if template is None and domain is None:
        print('   total seed labels evaluation:')
    elif domain is not None:
        print('   seed labels evaluation ({}):'.format(domain))
    else:
        print('      seed labels evaluation')

    retrieved_count = 0                           # all pred-obj retrieved in seed label
    relevant_count = 0                            # all obj found in the webpage that are in the kb (of all this we should find a predicate)
    relevant_retrieved = []                       # pred-obj in seed label that are correct
    not_relevant_retrieved = defaultdict(list)    # pred-obj in seed label that are not correct
    relevant_not_retrieved = {}                   # pred-obj in the kb but not in seed_label

    if template:
        webpages = page_service.get_all(template=template)
    elif domain:
        webpages = page_service.get_all(domain=domain)
    else:
        webpages = page_service.get_all()

    for webpage in webpages:
        if 'topic_id' not in webpage or webpage['topic_id'] is None or 'seed_labels' not in webpage:
            continue

        parsed_page = ParsedPage(webpage['html'])

        seed_label = webpage['seed_labels']

        topic_related_text_nodes = [{'xpath': node_xpath, 'entity_id': node_metadata['obj_id']} for node_xpath, node_metadata in webpage['topic_related_candidate_pairs'].items()]

        retrieved_count += len(seed_label)
        relevant_count += len(topic_related_text_nodes)

        seed_labels_errors_count = 0

        # get relevant retrieved
        for obj, obj_metadata in seed_label.items():
            obj = parsed_page.get_nodes_xpath(obj)[0].text
            obj_id = obj_metadata['obj_id']
            pred = parsed_page.get_nodes_xpath(obj_metadata['pred'])[0].text

            true_preds = webpage_service.get_true_preds(webpage, obj)
            if any(string_utils.compare_string(true_pred, pred) for true_pred in true_preds):
                relevant_retrieved.append((pred, obj))
            else:
                kb_rel_with_page_topic = entity_service.get_relations_between(webpage['topic_id'], obj_id)
                kb_rel_with_page_topic = [rel['edge_type_text'] for rel in kb_rel_with_page_topic]
                not_relevant_retrieved[webpage['site'] + '-' + webpage['topic_text']].append((pred, true_preds, kb_rel_with_page_topic, obj))
                seed_labels_errors_count += 1

        # get relevant not retrieved
        retrieved = [parsed_page.get_nodes_xpath(node)[0].text for node in seed_label.keys()]

        relevants = {}
        for relevant in topic_related_text_nodes:
            relevant_node = parsed_page.get_nodes_xpath(relevant['xpath'], clean=True)[0]
            relevant_kb_entity = relevant['entity_id']
            relevant_preds_with_page_topic = entity_service.get_relations_between(webpage['topic_id'], relevant_kb_entity)
            relevants[relevant_node.text] = [pred['edge_type_text'] for pred in relevant_preds_with_page_topic]

        webpage_relevant_not_retrieved = set(relevants.keys()) - set(retrieved)
        webpage_relevant_not_retrieved = [{'true_pred': webpage_service.get_true_preds(webpage, obj), 'kb_pred': relevants[obj], 'obj': obj} for obj in webpage_relevant_not_retrieved]

        relevant_not_retrieved[webpage['site'] + '-' + webpage['topic_text']] = webpage_relevant_not_retrieved

        webpage['seed_labels_errors'] = seed_labels_errors_count
        page_service.save(webpage)

    if retrieved_count==0:
        precision = 0
        recall = 0
    else:
        precision = len(relevant_retrieved) / retrieved_count
        recall = len(relevant_retrieved) / relevant_count

    if precision > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0

    print('         precision: {}'.format(precision))
    print('         recall: {}'.format(recall))
    print('         f1: {}'.format(f1))
    print('         all_count: {}'.format(retrieved_count))

    if debug:
        print('         ok: {}'.format(relevant_retrieved))

        print('         errors: [pred, true_preds, kb_preds, obj]')
        for webpage, preds in not_relevant_retrieved.items():
            print('            {}: {}'.format(webpage, preds))

        print('         missed: [true_pred, kb_pred, obj]')
        for webpage, webpage_relevant_not_retrieved in relevant_not_retrieved.items():
            webpage_relevant_not_retrieved = [(x['true_pred'], x['kb_pred'], x['obj']) for x in webpage_relevant_not_retrieved]
            print('            {}: {}'.format(webpage, webpage_relevant_not_retrieved))

    return {'precision': precision, 'recall': recall, 'f1': f1}


def get_best_pred(parsed_page, text_node_kb_entity_id, text_node_pred_candidates, text_node_relation_types, pred_syns, page_topic_id, entity_service, cfg):
    text_node_relations = text_node_relation_types
    redundancy_against_distance = cfg['seed_labels']['redundancy_against_distance']

    # # search best pred by string similarity
    # for pred_candidate in text_node_pred_candidates:
    #     pred_candidate_node = parsed_page.get_nodes_xpath(pred_candidate['node'])[0]
    #     for kb_relation_text in text_node_relations.values():
    #         if string_utils.compare_string_meaning(kb_relation_text, pred_candidate_node.text):
    #             return pred_candidate_node

    # search best pred with synonims
    best_pred_candidate_score = 0
    best_pred_candidate = None

    for pred_candidate in text_node_pred_candidates:
        for kb_relation_id, kb_relation_text in text_node_relations.items():  # (pred_syns_scores are grouped by kb_relation)
            if kb_relation_id not in pred_syns:
                continue

            relation_pred_syns = pred_syns[kb_relation_id]
            pred_candidate_node = parsed_page.get_nodes_xpath(pred_candidate['node'])[0]

            pred_candidate_text = pred_candidate_node.text
            pred_candidate_text = string_utils.clean_string(pred_candidate_text)
            pred_candidate_text = string_utils.stem_sentence(pred_candidate_text)

            if pred_candidate_text in relation_pred_syns:
                pred_candidate_redundancy_score = relation_pred_syns[pred_candidate_text]
                pred_candidate_distance_score = 1 - pred_candidate['distance']

                # weighted mean
                pred_candidate_score = redundancy_against_distance * pred_candidate_redundancy_score + (1 - redundancy_against_distance) * pred_candidate_distance_score

                # harmonic weighted mean
                # pred_candidate_score = 1 / (redundancy_against_distance / pred_candidate_redundancy_score + (1 - redundancy_against_distance) / pred_candidate_distance_score)

                if pred_candidate_score > best_pred_candidate_score:
                    best_pred_candidate_score = pred_candidate_score
                    best_pred_candidate = pred_candidate_node

    return best_pred_candidate, best_pred_candidate_score


    # if string_utils.compare_string_meaning(kb_relation_synonim, pred_candidate_node.text):
    #     return pred_candidate_node


def compute_seed_labels(page_service, entity_service, webpage_index, selenium_driver, cfg):
    print('compute seed labels...')
    debug = cfg['seed_labels']['debug']
    intra_against_inter = cfg['seed_labels']['intradomain_redundancy_against_interdomain']

    # if intra_against_inter < 1:     # if is 1 inter is not needed
    #     print('   all templates (inter domain):')
    #     pred_syns_interdomain = pred_synonims.compute_pred_synonim_scores(page_service, selenium_driver, 0, debug)

    templates = page_service.get_all_field_values('template')
    print(templates)
    # leave only templates in config
    if len(cfg['seed_labels']['templates']) > 0:
        templates_to_leave = cfg['seed_labels']['templates']
        templates = list(filter(lambda template: any(template_to_leave in template for template_to_leave in templates_to_leave), templates))
    elif len(cfg['seed_labels']['domains']) > 0:
        domains = cfg['seed_labels']['domains']
        templates = list(filter(lambda template: any(domain in template for domain in domains), templates))

    # get predicate synonims
    # pred_syns = {template1: {pred_id1:{pred_syn: score1, pred_syn2:score2}}}
    pred_syns = {}
    for template in templates:
        print('   template: {}'.format(template))

        pred_syns_intradomain = pred_synonims.compute_pred_synonim_scores(page_service, selenium_driver, cfg, debug, templates=[template])

        if intra_against_inter < 1:  # if is 1 inter is not needed
            pred_syns_interdomain = pred_synonims.compute_pred_synonim_scores(page_service, selenium_driver, cfg, debug, templates=list(templates).remove(template))

        # merge interdomain and intradomain pred syns scores
        site_pred_syns = defaultdict(dict)
        for pred_id, intra_pred_syns in pred_syns_intradomain.items():
            for intra_pred_syn, score_intra in intra_pred_syns.items():
                if intra_against_inter < 1:
                    if pred_id in pred_syns_interdomain and intra_pred_syn in pred_syns_interdomain[pred_id]:
                        score_inter = pred_syns_interdomain[pred_id][intra_pred_syn]
                    else:
                        score_inter = 0
                    score = intra_against_inter * score_intra + (1 - intra_against_inter) * score_inter
                else:
                    score = score_intra
                site_pred_syns[pred_id][intra_pred_syn] = score
        #site_pred_syns = {pred_id: iterators.get_key_with_max_value(pred_syns) for pred_id, pred_syns in site_pred_syns.items()}
        pred_syns[template] = site_pred_syns

    # increase score of pred syns that were found in at least 2 different sites
    # pred_syns_sites_freqs = defaultdict(lambda: defaultdict(lambda: 0))               # {pred_id: {pred_syn1: 1, pred_syn2: 4}}
    # for template, template_preds in pred_syns.items():
    #     for pred_id, template_pred_syns in template_preds.items():
    #         for template_pred_syn, score in template_pred_syns.items():
    #             pred_syns_sites_freqs[pred_id][template_pred_syn] += 1
    #
    # filtered_pred_syns = defaultdict(lambda: defaultdict(lambda: defaultdict()))      # {template1: {pred_id1:{pred_syn: score1, pred_syn2:score2}}}
    # for template, template_preds in pred_syns.items():
    #     for pred_id, template_pred_syns in template_preds.items():
    #         for template_pred_syn, score in template_pred_syns.items():
    #             if pred_syns_sites_freqs[pred_id][template_pred_syn] > 1:
    #                 score = score * 1.2
    #                 print('{}'.format(template_pred_syn))
    #             filtered_pred_syns[template][pred_id][template_pred_syn] = score
    # pred_syns = filtered_pred_syns
    # print(pred_syns)

    # get seed labels
    for template in templates:
        print('   get_seed_labels...')
        print('      template: {}'.format(template))
        # foreach obj get the best pred in candidates_preds
        for page in page_service.get_all(template=template):
            if page['topic_id'] is None:
                continue

            page_preds = {}

            parsed_page = ParsedPage(page['html'])
            page_topic_id = page['topic_id']

            for text_node_xpath, text_node_metadata in page['topic_related_candidate_pairs'].items():
                text_node_text = text_node_metadata['obj_text']
                text_node_kb_entity = text_node_metadata['obj_id']
                text_node_relation_types = text_node_metadata['rel_types']

                text_node_pred_candidates = text_node_metadata['pred_candidates']

                node_pred, node_pred_score = get_best_pred(parsed_page, text_node_kb_entity, text_node_pred_candidates, text_node_relation_types, pred_syns[template], page_topic_id, entity_service, cfg)

                if node_pred is not None:
                    node_pred_xpath = parsed_page.get_xpath(node_pred)
                    page_preds[text_node_xpath] = {'pred': node_pred_xpath, 'pred_text': node_pred.text, 'obj_id': text_node_kb_entity, 'obj_text': text_node_text, 'score': node_pred_score}

            # if there is multiple times the same obj, remove one that has pred with lower score
            page_preds_by_obj_text = defaultdict(list)   # {'bruce willis': [{obj_xpath: xpath, score:0.85}, ...]}
            for obj_xpath, obj_metadata in page_preds.items():
                obj_text = obj_metadata['obj_text']
                pred_score = obj_metadata['score']
                page_preds_by_obj_text[obj_text].append({'obj_xpath': obj_xpath, 'score': pred_score})

            obj_xpath_to_remove = []
            for obj_text, objs in page_preds_by_obj_text.items():
                if len(objs) > 1:
                    max_score = max(objs, key=lambda x: x['score'])['score'] * 0.9
                    for obj in objs:
                        if obj['score'] < max_score:
                            obj_xpath_to_remove.append(obj['obj_xpath'])

            for obj_xpath in obj_xpath_to_remove:
                page_preds.pop(obj_xpath)


            page['seed_labels'] = page_preds
            page_service.save(page)

        # remove all seed labels which pred after have always the same string
        # pred_next_string = defaultdict(list)                            # {pred1:[review, review,], }
        # for page in page_service.get_all(template=template):
        #     if not 'seed_labels' in page:
        #         continue
        #
        #     for obj_xpath, obj_metadata in page['seed_labels'].items():
        #         parsed_page = ParsedPage(page['html'])
        #         pred_node = parsed_page.get_nodes_xpath(obj_metadata['pred'], clean=True)[0]
        #         next_node = parsed_page.get_successor_text_nodes(pred_node, clean=True)[0]
        #         pred_next_string[pred_node.text].append(next_node.text)
        #
        # pred_next_string_freqs = {pred: iterators.get_elements_frequency(next_strings, normalized=True) for pred, next_strings in pred_next_string.items()}
        # print(pred_next_string_freqs)
        #
        # preds_to_remove = []
        # for pred, next_strings_freqs in pred_next_string_freqs.items():
        #     for next_string, freq in next_strings_freqs.items():
        #         if freq > 0.9:
        #             preds_to_remove.append(pred)
        #             break
        #
        # for page in page_service.get_all(template=template):
        #     if not 'seed_labels' in page:
        #         continue
        #
        #     obj_xpath_to_remove = []
        #     for obj_xpath, obj_metadata in page['seed_labels'].items():
        #         parsed_page = ParsedPage(page['html'])
        #         pred_node = parsed_page.get_nodes_xpath(obj_metadata['pred'], clean=True)[0]
        #         if pred_node.text in preds_to_remove:
        #             obj_xpath_to_remove.append(obj_xpath)
        #
        #     for obj_xpath in obj_xpath_to_remove:
        #         page['seed_labels'].pop(obj_xpath)
        #
        #     page_service.save(page)


        # remove all seed labels which have always the same string in the middle
        preds_middle_strings = defaultdict(list)                                                        # {pred_text:[[strings in the midlle of pred1-obj1], [strings in the midlle of pred2-obj2],], }
        pages_cursor = page_service.get_all(template=template, no_cursor_timeout=True)
        for page in pages_cursor:
            if not 'seed_labels' in page:
                continue

            for obj_xpath, obj_metadata in page['seed_labels'].items():
                pred_xpath = obj_metadata['pred']
                pred_text = obj_metadata['pred_text']
                selenium_driver.set_page(page['html'])
                middle_nodes = selenium_driver.get_elements_in_the_middle(pred_xpath, obj_xpath, only_text=True)
                preds_middle_strings[pred_text].append(middle_nodes)

        middle_strings_freqs = defaultdict(lambda: defaultdict(lambda: 0))                                # {pred_text: {middle_string: freq, middle_string2: freq}, ...}
        for pred_text, all_pred_middle_strings in preds_middle_strings.items():
            for pred_middle_strings in all_pred_middle_strings:
                for pred_middle_string in pred_middle_strings:
                    middle_strings_freqs[pred_text][pred_middle_string] += 1 / len(all_pred_middle_strings)

        preds_to_remove = []
        for pred, middle_strings_freqs in middle_strings_freqs.items():
            for middle_string, freq in middle_strings_freqs.items():
                if freq > 0.9:
                    preds_to_remove.append(pred)
                    break

        pages_cursor.close()

        for page in page_service.get_all(template=template):
            if not 'seed_labels' in page:
                    continue

            obj_xpath_to_remove = []
            for obj_xpath, obj_metadata in page['seed_labels'].items():
                pred_text = obj_metadata['pred_text']
                if pred_text in preds_to_remove:
                    obj_xpath_to_remove.append(obj_xpath)

            for obj_xpath in obj_xpath_to_remove:
                page['seed_labels'].pop(obj_xpath)

            page_service.save(page)







        # pred_next_string_freqs = {pred: iterators.get_elements_frequency(next_strings, normalized=True) for pred, next_strings in preds_middle_strings.items()}
        # print(pred_next_string_freqs)
        #
        # preds_to_remove = []
        # for pred, next_strings_freqs in pred_next_string_freqs.items():
        #     for next_string, freq in next_strings_freqs.items():
        #         if freq > 0.9:
        #             preds_to_remove.append(pred)
        #             break
        #
        # for page in page_service.get_all(template=template):
        #     if not 'seed_labels' in page:
        #         continue
        #
        #     obj_xpath_to_remove = []
        #     for obj_xpath, obj_metadata in page['seed_labels'].items():
        #         parsed_page = ParsedPage(page['html'])
        #         pred_node = parsed_page.get_nodes_xpath(obj_metadata['pred'], clean=True)[0]
        #         if pred_node.text in preds_to_remove:
        #             obj_xpath_to_remove.append(obj_xpath)
        #
        #     for obj_xpath in obj_xpath_to_remove:
        #         page['seed_labels'].pop(obj_xpath)
        #
        #     page_service.save(page)





        # # remove all seed labels that have lowest embedding distance (pred-obj)
        # for page in page_service.get_all(template=template):
        #     if not 'seed_labels' in page:
        #         continue
        #
        #     seed_labels = page['seed_labels']
        #     embedder = string_utils.FastTextEmbedder()
        #
        #     for obj_xpath, obj_metadata in seed_labels.items():
        #         pred_text = obj_metadata['pred_text']
        #         obj_text = obj_metadata['obj_text']
        #         embedding_distance = embedder.get_distance(pred_text, obj_text)
        #         seed_labels[obj_xpath]['embedding_distance'] = embedding_distance
        #     page_service.save(page)
        #
        # embedding_distances = []
        # for page in page_service.get_all(template=template):
        #     if not 'seed_labels' in page:
        #         continue
        #     page_embedding_distances = [obj_metadata['embedding_distance'] for obj_metadata in page['seed_labels'].values()]
        #     embedding_distances.extend(page_embedding_distances)
        # print(embedding_distances)
        # plotter.plot_histogram(embedding_distances, template)




        # evaluate results
        if debug:
            evaluate_results(page_service, entity_service, debug, template)

    if len(cfg['seed_labels']['domains']) > 0:
        for domain in domains:
            evaluate_results(page_service, entity_service, debug=False, domain=domain)

    return evaluate_results(page_service, entity_service, debug=False)
