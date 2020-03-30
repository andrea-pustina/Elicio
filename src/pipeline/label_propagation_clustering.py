import src.utils.iterators as iterators
from collections import defaultdict
from src.html.webpage_lxml import ParsedPage
from src.service.webpage_service import check_pred_obj_pair
from sklearn import preprocessing
from sklearn.naive_bayes import GaussianNB
import random
import src.utils.string_utils as string_utils
from statistics import mean
import src.utils.elapsed_timer as timer
from community import community_louvain
import networkx as nx


def get_candidate_pred_obj_pairs(webpage, parsed_page):
    candidate_pairs = {}

    for obj_xpath, obj_metadata in webpage['candidate_pairs'].items():
        obj_text = obj_metadata['obj_text']
        obj_features = obj_metadata['features']

        candidate_preds = obj_metadata['pred_candidates']
        for candidate_pred in candidate_preds:
            candidate_pred_xpath = candidate_pred['node']
            candidate_pred_text = candidate_pred['text']
            candidate_pred_features = candidate_pred['features']

            if obj_xpath not in candidate_pairs:
                candidate_pairs[obj_xpath] = {'obj_text': obj_text,
                                              'obj_features': obj_features,
                                              'candidate_preds': {}}

            candidate_pairs[obj_xpath]['candidate_preds'][candidate_pred_xpath] = {'pred_text': candidate_pred_text,
                                                                                   'pred_features': candidate_pred_features}

    return candidate_pairs


def clean_datapoint_features(data_point, dom_features_names, dom_label_encoders, distance_features_names, max_distance_features_value, webpage_index, webpage_template, obj_text, pred_text, tag_encoder):
    """

    :param data_point: {'obj_features': {...}, 'pred_features': {...} }
    :param dom_features_names: ['font_size', ...]
    :param dom_label_encoders: {dom_feature_name: label_encoder, ...}
    :return: [0, 1, 0 , 1, 1]
    """

    datapoint_features_encoded = []

    # get dom features
    # for dom_feature_name in dom_features_names:
    #     label_encoder = dom_label_encoders[dom_feature_name]
    #
    #     obj_dom_feature = data_point['obj_features']['dom'][dom_feature_name]
    #     pred_dom_feature = data_point['pred_features']['dom'][dom_feature_name]
    #
    #     obj_dom_feature_encoded = label_encoder.transform([obj_dom_feature])[0]
    #     pred_dom_feature_encoded = label_encoder.transform([pred_dom_feature])[0]
    #
    #     datapoint_features_encoded.append(obj_dom_feature_encoded)
    #     datapoint_features_encoded.append(pred_dom_feature_encoded)

    same_dom_features = 1
    for dom_feature_name in dom_features_names:
        label_encoder = dom_label_encoders[dom_feature_name]

        obj_dom_feature = data_point['obj_features']['dom'][dom_feature_name]
        pred_dom_feature = data_point['pred_features']['dom'][dom_feature_name]

        # print(data_point['obj_features'])
        # print(data_point['pred_features'])

        obj_dom_feature_encoded = label_encoder.transform([obj_dom_feature])[0]
        pred_dom_feature_encoded = label_encoder.transform([pred_dom_feature])[0]

        if obj_dom_feature_encoded!=pred_dom_feature_encoded:
            same_dom_features = 0
            break
    datapoint_features_encoded.append(same_dom_features)

    # get dom distance
    datapoint_features_encoded.append(data_point['pred_features']['dom_distance'])

    # get distance features
    # distances = iterators.merge_two_dicts(data_point['pred_features']['distances']['horizontal'], data_point['pred_features']['distances']['vertical'])
    # #distances['min_distance'] = data_point['pred_features']['distances']['min_distance']
    # #distances['origin_distance'] = data_point['pred_features']['distances']['origin_distance']
    # for distance_feature_name in distance_features_names:
    #     distance_feature = distances[distance_feature_name]
    #     distance_feature_normalized = distance_feature / max_distance_features_value
    #     datapoint_features_encoded.append(distance_feature_normalized)

    min_horizontal_alignment = min(data_point['pred_features']['distances']['horizontal'].values())
    min_vertical_alignment = min(data_point['pred_features']['distances']['vertical'].values())
    datapoint_features_encoded.append(min_horizontal_alignment)
    datapoint_features_encoded.append(min_vertical_alignment)

    # get graphic features
    if data_point['pred_features']['graphic']['is_above_and_on_left']:
        datapoint_features_encoded.append(1)
    else:
        datapoint_features_encoded.append(0)

    # get pred and obj frequencies
    # datapoint_features_encoded.append(webpage_index.get_term_freq(webpage_template, obj_text, normalized=True))
    # datapoint_features_encoded.append(webpage_index.get_term_freq(webpage_template, pred_text, normalized=True))

    # get pred and obj tags
    obj_xpath = data_point['obj_xpath']
    pred_xpath = data_point['pred_xpath']

    obj_tag = obj_xpath.split('/')[-1]
    pred_tag = pred_xpath.split('/')[-1]

    obj_tag = string_utils.remove_substring_by_regex(obj_tag, '\\[.*\\]')
    pred_tag = string_utils.remove_substring_by_regex(pred_tag, '\\[.*\\]')

    datapoint_features_encoded.append(tag_encoder.transform([obj_tag])[0])
    datapoint_features_encoded.append(tag_encoder.transform([pred_tag])[0])

    #print(datapoint_features_encoded)
    return datapoint_features_encoded


def get_dom_label_encoders(page_service, template):
    dom_label_encoders = {}  # {dom_feature1: label_encoder1, dom_feature2:...}

    all_dom_features_values = defaultdict(set)  # {feature_name: [list of possible values]}
    for webpage in page_service.get_all(template=template):
        if 'candidate_pairs' not in webpage:
            continue

        for candidate_pair in webpage['candidate_pairs'].values():
            for dom_feature in candidate_pair['features']['dom'].keys():
                obj_dom_feature_value = candidate_pair['features']['dom'][dom_feature]
                all_dom_features_values[dom_feature].add(obj_dom_feature_value)

                for pred_candidate in candidate_pair['pred_candidates']:
                    pred_dom_feature_value = pred_candidate['features']['dom'][dom_feature]
                    all_dom_features_values[dom_feature].add(pred_dom_feature_value)

    # we later use label_encoder to tranform 'san serif'->0, 'times_new_roman'->1
    for feature_name, feature_values in all_dom_features_values.items():
        label_encoder = preprocessing.LabelEncoder()
        label_encoder.fit(list(feature_values))
        dom_label_encoders[feature_name] = label_encoder

    return dom_label_encoders


def get_max_distance_feature_value(page_service, template):
    """
    return the max value of any distance feature (for all webpages)
    :param page_service:
    :param template:
    :return: max_distance_features_value
    """

    curr_max_distance = -float('inf')
    for webpage in page_service.get_all(template=template):
        if 'candidate_pairs' not in webpage:
            continue

        for candidate_pair in webpage['candidate_pairs'].values():
            for candidate_pred in candidate_pair['pred_candidates']:
                pred_distance_features = candidate_pred['features']['distances']
                pred_max_distance = iterators.get_max_int_value_in_nested_dictionary(pred_distance_features, absolute=True)
                curr_max_distance = max(curr_max_distance, pred_max_distance)

    return curr_max_distance


def get_html_tag_encoder(page_service):
    # get html element tag encoder  (tags: div, br, p, ...)
    all_xpaths = []
    for webpage in page_service.get_all():
        if 'candidate_pairs' not in webpage:
            continue

        for candidate_obj_xpath, candidate_obj_metadata in webpage['candidate_pairs'].items():
            all_xpaths.append(candidate_obj_xpath)

            for pred in candidate_obj_metadata['pred_candidates']:
                pred_xpath = pred['node']
                all_xpaths.append(pred_xpath)

    all_tags = set()
    for xpath in all_xpaths:
        tags = xpath.split('/')
        tags = [string_utils.remove_substring_by_regex(tag, '\\[.*\\]') for tag in tags]

        all_tags.update(tags)

    tag_encoder = preprocessing.LabelEncoder()
    tag_encoder.fit(list(all_tags))

    # print(all_tags)
    # print(tag_encoder.classes_)
    return tag_encoder


def get_webpage_seeds_labels(candidate_pairs, webpage):
    # get seed vertices (seed labels)
    seeds = []
    for obj_xpath, obj_metadata in webpage['seed_labels'].items():
        try:
            pred_xpath = obj_metadata['pred']

            obj_features = candidate_pairs[obj_xpath]['obj_features']
            pred_features = candidate_pairs[obj_xpath]['candidate_preds'][pred_xpath]['pred_features']

            obj_text = candidate_pairs[obj_xpath]['obj_text']
            pred_text = candidate_pairs[obj_xpath]['candidate_preds'][pred_xpath]['pred_text']

            seeds.append({'class': 1, 'obj_xpath': obj_xpath, 'obj_features': obj_features, 'pred_xpath': pred_xpath,
                          'pred_features': pred_features, 'obj_text': obj_text, 'pred_text': pred_text})
        except KeyError:
            print('seed label dropped')

    # get not seed vertices
    not_seeds = []
    for seed in seeds:
        seed_obj_xpath = seed['obj_xpath']
        seed_pred_xpath = seed['pred_xpath']

        obj_features = candidate_pairs[seed_obj_xpath]['obj_features']
        obj_text = candidate_pairs[seed_obj_xpath]['obj_text']

        # for seed obj get all preds that are not the pred of the seed label
        for candidate_pred_xpath, candidate_pred_metadata in candidate_pairs[seed_obj_xpath]['candidate_preds'].items():
            if candidate_pred_xpath != seed_pred_xpath:
                pred_features = candidate_pred_metadata['pred_features']
                pred_text = candidate_pred_metadata['pred_text']

                not_seeds.append({'class': 0, 'obj_xpath': seed_obj_xpath, 'obj_features': obj_features,
                                  'pred_xpath': seed_pred_xpath, 'pred_features': pred_features, 'obj_text': obj_text,
                                  'pred_text': pred_text})

        # get seed_obj-pred pairs where pred!=seed_pred
        for i in range(0, 5):
            random_obj_xpath = random.choice(list(candidate_pairs.keys()))
            if random_obj_xpath != seed_obj_xpath:
                random_pred_xpath = random.choice(list(candidate_pairs[random_obj_xpath]['candidate_preds'].keys()))
                if random_pred_xpath != seed_pred_xpath:
                    pred_features = candidate_pairs[random_obj_xpath]['candidate_preds'][random_pred_xpath][
                        'pred_features']
                    pred_text = candidate_pairs[random_obj_xpath]['candidate_preds'][random_pred_xpath]['pred_text']

                    not_seeds.append({'class': 0, 'obj_xpath': seed_obj_xpath, 'obj_features': obj_features,
                                      'pred_xpath': random_pred_xpath, 'pred_features': pred_features,
                                      'obj_text': obj_text, 'pred_text': pred_text})

    # print('   {}'.format(webpage['topic_text']))
    # print('      template: {}'.format(template))
    # print('      file: {}'.format(webpage['file_name']))
    # print('      seed: {}'.format([(seed['obj_text'], seed['pred_text']) for seed in seeds]))
    # print('      not_seed: {}'.format([(not_seed['obj_text'], not_seed['pred_text']) for not_seed in not_seeds]))

    page_training = seeds + not_seeds
    return page_training


def get_similarity(features_obj1, features_pred1, features_obj2, features_pred2):
    similarity = 0

    # dom similarity
    if features_obj1['dom'] == features_obj2['dom'] and features_pred1['dom'] == features_pred2['dom']:
        pass
    else:
        return 0

    # graphic similarity
    if features_pred1['graphic'] == features_pred2['graphic']:
        similarity += 1

    # horizontal similarity
    pair1_horizontal_distances = features_pred1['distances']['horizontal']
    pair2_horizontal_distances = features_pred2['distances']['horizontal']

    horizontal_similarity = 0
    for distance1 in pair1_horizontal_distances.values():
        for distance2 in pair2_horizontal_distances.values():
            distance1 = abs(distance1)
            distance2 = abs(distance2)

            curr_sim = max(0, min(distance1, distance2) / max(distance1, distance2)) if max(distance1, distance2) != 0 else 0
            horizontal_similarity = max(horizontal_similarity, curr_sim)

    similarity += horizontal_similarity

    # vertical similarity
    pair1_vertical_distances = features_pred1['distances']['vertical']
    pair2_vertical_distances = features_pred2['distances']['vertical']

    vertical_similarity = 0
    for distance1 in pair1_vertical_distances.values():
        for distance2 in pair2_vertical_distances.values():
            distance1 = abs(distance1)
            distance2 = abs(distance2)

            curr_sim = max(0, min(distance1, distance2) / max(distance1, distance2)) if max(distance1, distance2) != 0 else 0
            vertical_similarity = max(vertical_similarity, curr_sim)

    similarity += vertical_similarity

    return similarity


def get_training_set(page_service, template, webpage_index, tag_encoder, cluster_candidate_pairs):
    training_x = []
    training_y = []

    # # change candidate_preds format
    # formatted_candidate_pairs = {}
    # for candidate_pair in candidate_pairs:
    #     formatted_candidate_pairs[candidate_pair['obj_xpath']] = {
    #         'obj_text': candidate_pair['obj_text'],
    #         'obj_features': candidate_pair['obj_features'],
    #         'candidate_preds': {}
    #     }
    #
    # for obj_xpath in formatted_candidate_pairs.keys():
    #     obj_candidate_pairs = filter(lambda candidate_pair: candidate_pair['obj_xpath']==obj_xpath, candidate_pairs)
    #     for obj_candidate_pair in obj_candidate_pairs:
    #         pred_xpath = obj_candidate_pair['pred_xpath']
    #
    #         formatted_candidate_pairs[obj_xpath]['candidate_preds'][pred_xpath] = {
    #             'pred_text': obj_candidate_pair['pred_text'],
    #             'pred_features': obj_candidate_pair['prd_features']
    #         }
    #



    for webpage in page_service.get_all(template=template):
        if 'candidate_pairs' not in webpage:
            continue

        page_file_name = webpage['file_name']
        parsed_page = ParsedPage(webpage['html'])

        # get list of candidate pred-obj pairs -> candidate_pairs = {obj_xpath: {obj_text: 'avatar', obj_features: {...}, candidate_preds: {pred_xpath: {pred_text: 'film', pred_features: {...}}, ... } }}
        candidate_pairs = get_candidate_pred_obj_pairs(webpage, parsed_page)

        # get only candidate_pairs of the cluster
        page_cluster_candidate_pairs = filter(lambda cluster_candidate_pair: cluster_candidate_pair['page_file_name']==page_file_name, cluster_candidate_pairs)
        page_cluster_candidate_pairs_obj_xpaths = list(map(lambda candidate_pair: candidate_pair['obj_xpath'], page_cluster_candidate_pairs))
        #candidate_pairs = dict(filter(lambda candidate_pair: candidate_pair[0] in page_cluster_candidate_pairs_obj_xpaths, candidate_pairs.items()))
        candidate_pairs = {k: v for k, v in candidate_pairs.items() if k in page_cluster_candidate_pairs_obj_xpaths}
        print('cluster_candidate_pairs: {} elements'.format(len(candidate_pairs)))

        # build training set
        page_training = get_webpage_seeds_labels(candidate_pairs, webpage)
        page_training_x = [{'obj_features': data_point['obj_features'], 'pred_features': data_point['pred_features'],
                            'obj_text': data_point['obj_text'], 'pred_text': data_point['pred_text'],
                            'obj_xpath': data_point['obj_xpath'], 'pred_xpath': data_point['pred_xpath']} for data_point
                           in page_training]
        page_training_y = [data_point['class'] for data_point in page_training]

        training_x.extend(page_training_x)
        training_y.extend(page_training_y)

    # get features names to be sure to get features in the same order
    if len(training_x) > 0:
        dom_features_names = list(training_x[0]['obj_features']['dom'].keys())
        distance_features_names = list(training_x[0]['pred_features']['distances']['vertical'].keys()) + list(training_x[0]['pred_features']['distances']['horizontal'].keys())
    else:
        dom_features_names = []
        distance_features_names = []

    # distance_features_names.remove('left-left')
    # distance_features_names.remove('left-right')
    # distance_features_names.remove('right-right')
    # distance_features_names.remove('up-up')
    # distance_features_names.remove('up-down')
    # distance_features_names.remove('down-down')

    # distance_features_names = ['origin_distance']

    # label encoders are used to tranform categorical features into numbers (ex 'san serif' -> 0 , 'times new roman' -> 1)
    # dom_label_encoders = {dom_feature1: label_encoder1, dom_feature2:...}
    dom_label_encoders = get_dom_label_encoders(page_service, template)

    # get max distance to normalize all distances
    max_distance_features_value = get_max_distance_feature_value(page_service, template)

    # get features encoded foreach datapoint
    training_x_encoded = []
    for data_point in training_x:
        obj_text = data_point['obj_text']
        pred_text = data_point['pred_text']
        datapoint_features_encoded = clean_datapoint_features(data_point, dom_features_names, dom_label_encoders,
                                                              distance_features_names, max_distance_features_value,
                                                              webpage_index, template, obj_text, pred_text, tag_encoder)
        training_x_encoded.append(datapoint_features_encoded)

    return training_x_encoded, training_y, dom_features_names, dom_label_encoders, distance_features_names, max_distance_features_value


def do_classification(page_service, template, webpage_index, model, tag_encoder, dom_features_names, dom_label_encoders, distance_features_names, max_distance_features_value, cluster_candidate_pairs):
    # compute score foreach pred candidate foreach obj
    for webpage in page_service.get_all(template=template):
        if 'candidate_pairs' not in webpage:
            continue

        # get only candidate_pairs of the cluster
        page_file_name = webpage['file_name']
        page_cluster_candidate_pairs = filter(lambda cluster_candidate_pair: cluster_candidate_pair['page_file_name']==page_file_name, cluster_candidate_pairs)
        page_cluster_candidate_pairs_obj_xpaths = list(map(lambda candidate_pair: candidate_pair['obj_xpath'], page_cluster_candidate_pairs))


        for obj_xpath, obj_metadata in webpage['candidate_pairs'].items():
            if not obj_xpath in page_cluster_candidate_pairs_obj_xpaths:
                continue

            obj_features = obj_metadata['features']
            obj_text = obj_metadata['obj_text']

            pred_candidates = obj_metadata['pred_candidates']
            for pred_candidate in pred_candidates:
                pred_features = pred_candidate['features']
                pred_text = pred_candidate['text']
                pred_xpath = pred_candidate['node']

                data_point = {'obj_features': obj_features, 'pred_features': pred_features, 'obj_xpath': obj_xpath,
                              'pred_xpath': pred_xpath}
                data_point_features = clean_datapoint_features(data_point, dom_features_names, dom_label_encoders,
                                                               distance_features_names, max_distance_features_value,
                                                               webpage_index, template, obj_text, pred_text,
                                                               tag_encoder)
                pred_score = model.predict([data_point_features])[0]

                # print(pred_score)
                pred_candidate['score'] = float(pred_score)

        page_service.save(webpage)

    # foreach obj select pred from pred candidates
    for webpage in page_service.get_all(template=template):
        if 'candidate_pairs' not in webpage:
            continue

        page_new_pred_obj_pairs = []

        for obj_xpath, obj_metadata in webpage['candidate_pairs'].items():
            if not obj_xpath in page_cluster_candidate_pairs_obj_xpaths:
                continue

            obj_text = obj_metadata['obj_text']

            pred_candidates = obj_metadata['pred_candidates']
            if len(pred_candidates) > 0:
                best_pred_candidate = max(pred_candidates, key=lambda pred_candidate: pred_candidate['score'])

                best_pred_candidate_xpath = best_pred_candidate['node']
                best_pred_candidate_text = best_pred_candidate['text']
                best_pred_candidate_score = best_pred_candidate['score']

                if best_pred_candidate_score > 0:
                    page_new_pred_obj_pairs.append(
                        {'obj_xpath': obj_xpath, 'pred_xpath': best_pred_candidate_xpath, 'obj_text': obj_text,
                         'pred_text': best_pred_candidate_text})

        webpage['new_labels'] = page_new_pred_obj_pairs
        page_service.save(webpage)


def candidate_pairs_clustering(page_service, template):
    g = nx.Graph()

    # get all candidate pairs which obj is not in seed labels
    print('computing_nodes...', end='')
    curr_id = 0
    candidate_pairs = {}
    for webpage in page_service.get_all(template=template):
        if 'candidate_pairs' not in webpage:
            continue

        new_labels_obj_xpaths = [x['obj_xpath'] for x in webpage['new_labels']]

        for obj_xpath, obj_data in webpage['candidate_pairs'].items():
            for pred_data in obj_data['pred_candidates']:
                pred_xpath = pred_data['node']

                if obj_xpath not in webpage['seed_labels'] and obj_xpath not in new_labels_obj_xpaths:
                    candidate_pair = {}
                    candidate_pair['obj_xpath'] = obj_xpath
                    candidate_pair['pred_xpath'] = pred_xpath
                    candidate_pair['obj_text'] = obj_data['obj_text']
                    candidate_pair['pred_text'] = pred_data['text']

                    candidate_pair['obj_features'] = obj_data['features']
                    candidate_pair['pred_features'] = pred_data['features']

                    candidate_pair['page_file_name'] = webpage['file_name']
                    candidate_pair['page_topic_id'] = webpage['topic_id']
                    candidate_pair['page_topic_text'] = webpage['topic_text']

                    candidate_pairs[curr_id] = candidate_pair
                    curr_id += 1
    print('ok')

    print('add_nodes...', end='')
    g.add_nodes_from(candidate_pairs.keys())
    print('ok')

    print('computing_edges...')
    total_operation_count = pow(curr_id + 1, 2)
    status_printer = timer.StatusPrinter(total_operation_count, padding='      ')
    edges = []
    for pair1_id, pair1 in candidate_pairs.items():
        for pair2_id, pair2 in candidate_pairs.items():
            if pair1['obj_xpath'] == pair2['obj_xpath'] and pair1['pred_xpath'] == pair2['pred_xpath']:
                continue

            pairs_similarity = get_similarity(pair1['obj_features'], pair1['pred_features'], pair2['obj_features'],
                                              pair2['pred_features'])

            if pairs_similarity > 0:
                edges.append((pair1_id, pair2_id, pairs_similarity))

            status_printer.operation_done()
    status_printer.finish()

    print('add_edges...', end='')
    g.add_weighted_edges_from(edges)
    print('ok')

    print('clustering...', end='')
    pairs_clusters = community_louvain.best_partition(g)
    print('ok')

    clusters = set()
    for id, cluster in pairs_clusters.items():
        candidate_pairs[id]['cluster'] = cluster
        clusters.add(cluster)

    return candidate_pairs.values(), clusters


def propagate_labels(page_service, cfg, webpage_index):
    print('propagating labels...')
    templates = page_service.get_all_field_values('template')

    tag_encoder = get_html_tag_encoder(page_service)

    for template in templates:
        candidate_pairs, clusters = candidate_pairs_clustering(page_service, template)

        for cluster in clusters:
            print('cluster: {}'.format(cluster))
            cluster_candidate_pairs = list(filter(lambda candidate_pair: candidate_pair['cluster']==cluster, candidate_pairs))
            print('   cluster_candidate_pairs: {}'.format(cluster_candidate_pairs))

            training_x_encoded, training_y, dom_features_names, dom_label_encoders, distance_features_names, max_distance_features_value = get_training_set(page_service, template, webpage_index, tag_encoder, cluster_candidate_pairs)

            print('   cluster_training_x_encoded: {}'.format(training_x_encoded))
            if len(training_x_encoded) <= 0:
                continue

            # train ml model
            model = GaussianNB()                            # naive bayes
            model.fit(training_x_encoded, training_y)

            do_classification(page_service, template, webpage_index,model, tag_encoder, dom_features_names, dom_label_encoders, distance_features_names, max_distance_features_value, cluster_candidate_pairs)

    for template in templates:
        evaluate_results(page_service, template=template)
    evaluate_results(page_service)


def evaluate_results(page_service, template=None):
    retrieved_count = 0
    relevant_count = 0
    relevant_retrieved = []
    not_relevant_retrieved = []

    for webpage in page_service.get_all(template=template):
        if 'new_labels' not in webpage:
            continue

        page_retrieved_count = 0
        page_relevant_count = sum([len(objs) for pred, objs in webpage['ground_truth'].items()]) # objs in groun truth

        page_relevant_retrieved = []                     # pred-obj in new_labels that are correct
        page_not_relevant_retrieved = []                 # pred-obj in new_labels that are not correct

        for new_label in webpage['new_labels']:
            page_retrieved_count += 1

            obj_text = new_label['obj_text']
            pred_text = new_label['pred_text']
            obj_xpath = new_label['obj_xpath']
            pred_xpath = new_label['pred_xpath']

            new_label['file_name'] = webpage['file_name']

            # get dom distance
            obj_pred_candidates = webpage['candidate_pairs'][obj_xpath]['pred_candidates']
            new_label['dom_distance'] = iterators.get_first(obj_pred_candidates, lambda x: x['node']==pred_xpath)['features']['dom_distance']

            if check_pred_obj_pair(webpage, pred_text, obj_text):
                #print('ok -> {} - {}'.format(pred_text, obj_text))
                page_relevant_retrieved.append(new_label)
            else:
                #print('ko -> {} - {}'.format(pred_text, obj_text))
                page_not_relevant_retrieved.append(new_label)

        retrieved_count += page_retrieved_count
        relevant_count += page_relevant_count
        relevant_retrieved.extend(page_relevant_retrieved)
        not_relevant_retrieved.extend(page_not_relevant_retrieved)

    if retrieved_count == 0:
        precision = 0
        recall = 0
    else:
        precision = len(relevant_retrieved) / retrieved_count
        recall = len(relevant_retrieved) / relevant_count

    if precision > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0

    print('    Evaluation ({})'.format(template))
    print('         precision: {}'.format(precision))
    print('         recall: {}'.format(recall))
    print('         f1: {}'.format(f1))
    print('         ok ({}): {}'.format(len(relevant_retrieved), [(x['pred_text'], x['obj_text'], x['file_name']) for x in relevant_retrieved]))
    print('         errors ({}): {}'.format(len(not_relevant_retrieved), [(x['pred_text'], x['obj_text'], x['file_name']) for x in not_relevant_retrieved]))
    print('         retrieved: {}'.format(retrieved_count))


    dom_distance_relevant_retrieved = [x['dom_distance'] for x in relevant_retrieved]
    dom_distance_not_relevant_retrieved = [x['dom_distance'] for x in not_relevant_retrieved]
    if len(dom_distance_relevant_retrieved) > 0:
        print('         dom_distance_relevant_retrieved (avg:{}): {}'.format(mean(dom_distance_relevant_retrieved), dom_distance_relevant_retrieved))
    if len(dom_distance_not_relevant_retrieved) > 0:
        print('         dom_distance_not_relevant_retrieved (avg:{}): {}'.format(mean(dom_distance_not_relevant_retrieved), dom_distance_not_relevant_retrieved))







