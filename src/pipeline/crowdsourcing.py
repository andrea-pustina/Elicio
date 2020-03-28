import networkx as nx
import src.utils.iterators as iterators
import src.utils.elapsed_timer as timer
from community import community_louvain


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


# def is_seed_label(webpage, obj_xpath, pred_xpath):
#     return obj_xpath not in webpage['seed_labels'] and pred_xpath==webpage['seed_labels'][obj_xpath]['pred']


def start_crowd(page_service, neo4j, solr, cfg):
    templates = page_service.get_all_field_values('template')
    # templates = ['movie-imdb']

    for template in templates:
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
        total_operation_count = pow(curr_id+1, 2)
        status_printer = timer.StatusPrinter(total_operation_count, padding='      ')
        edges = []
        for pair1_id, pair1 in candidate_pairs.items():
            for pair2_id, pair2 in candidate_pairs.items():
                if pair1['obj_xpath'] == pair2['obj_xpath'] and pair1['pred_xpath'] == pair2['pred_xpath']:
                    continue

                pairs_similarity = get_similarity(pair1['obj_features'], pair1['pred_features'], pair2['obj_features'], pair2['pred_features'])

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


        cluster_freqs = iterators.get_elements_frequency(list(pairs_clusters.values()))
        del cluster_freqs[0]
        print('cluster_freqs: {}'.format(cluster_freqs))

        biggest_cluster = iterators.get_key_with_max_value(cluster_freqs)
        print('biggest_cluster: {}'.format(biggest_cluster))


        biggest_cluster_pairs = iterators.get_keys_with_value(pairs_clusters, biggest_cluster)

        # get pairs to test
        pairs_ids_to_test = []
        pair_test_pages = []
        i= 0
        j = 0
        while len(pairs_ids_to_test)<5 and i < len(biggest_cluster_pairs):
            pair_id_to_test = biggest_cluster_pairs[i]
            pair_to_test = candidate_pairs[pair_id_to_test]

            pair_test_page = pair_to_test['page_file_name']
            if pair_test_page not in pair_test_pages:
                pair_test_pages.append(pair_test_page)
                pairs_ids_to_test.append(pair_id_to_test)
                print('{}) {} - {} - {}'.format(j, pair_to_test['page_topic_text'], pair_to_test['pred_text'], pair_to_test['obj_text']))
                j += 1
            i += 1

        max_node_id = int(neo4j.get_max_node_property_value('node_id').single().value())
        curr_new_node_id = max_node_id + 1

        max_edge_type_id = int(neo4j.get_max_edge_property_value('edge_type_id').single().value())
        curr_new_edge_type_id = max_edge_type_id + 1

        print('write index of correct pair:    (ex: 1, 2, 3, 4')
        input_data = input()
        input_data = input_data.split(',')
        for pair_index in input_data:
            candidate_pair_id = pairs_ids_to_test[int(pair_index)]
            candidate_pair = candidate_pairs[candidate_pair_id]
            subj_id = candidate_pair['page_topic_id']
            pred_text = candidate_pair['pred_text']
            obj_text = candidate_pair['obj_text']

            neo4j.create_node({'node_id': curr_new_node_id, 'node_text': obj_text})
            solr.add_doc('kb_node', {'node_id': curr_new_node_id, 'node_text': obj_text})

            solr_response = solr.send_query('kb_edge_type', 'edge_type_text:"{}"'.format(pred_text))
            if len(solr_response) > 0:
                edge_type_id = solr_response[0]['edge_type_id']
                edge_type_text = solr_response[0]['edge_type_text']
            else:
                edge_type_id = curr_new_edge_type_id
                edge_type_text = pred_text
                solr.add_doc('kb_edge_type', {'edge_type_id': edge_type_id, 'edge_type_text': edge_type_text})

                curr_new_edge_type_id += 1

            neo4j.create_edge(subj_id, curr_new_node_id, {'edge_type_id': edge_type_id, 'edge_type_text': edge_type_text})
            print('{} - {} - {}'.format(candidate_pair['page_topic_text'], candidate_pair['pred_text'], candidate_pair['obj_text']))

            curr_new_node_id += 1




        break



"""
            parsed_page = ParsedPage(webpage['html'])

            # get list of candidate pred-obj pairs (id_map is used to retrieve id, given pred and obj xpaths)
            # id_map = {'obj_xpath + '||' + pred_xpath': vertex_id}
            candidate_pairs, id_map = get_candidate_pred_obj_pairs(webpage, parsed_page)
            # print(candidate_pairs)

            # create similarity graph
            if len(candidate_pairs) == 0 or len(webpage['seed_labels']) == 0:
                continue

            g = nx.Graph()
            g.add_nodes_from([candidate_pair['id'] for candidate_pair in candidate_pairs])
            g_labels = {
                candidate_pair['id']: candidate_pair['obj']['text'][:4] + '||' + candidate_pair['pred']['text'][:4] for
                candidate_pair in candidate_pairs}
            for pair1 in candidate_pairs:
                for pair2 in candidate_pairs:
                    if pair1['obj']['xpath'] == pair2['obj']['xpath'] and pair1['pred']['xpath'] == pair2['pred'][
                        'xpath']:
                        continue

                    pair1_id = pair1['id']
                    pair2_id = pair2['id']
                    pairs_similarity = get_similarity(pair1['obj']['features'], pair1['pred']['features'],
                                                      pair2['obj']['features'], pair2['pred']['features'])

                    g.add_weighted_edges_from([(pair1_id, pair2_id, pairs_similarity)])

            # leave only 10 edges with max weight foreach vertex
            # for vertex in g.nodes:
            #     vertex_edges = list(g.edges(vertex, data=True))
            #     sorted(vertex_edges, key=lambda vertex_edge: vertex_edge[2]['weight'], reverse=True)
            #     for source_vertex, dst_vertex, edge_data in vertex_edges[9:]:
            #         g.remove_edge(source_vertex, dst_vertex)

            # get seed vertices (seed labels)
            seeds = []
            for obj_xpath, obj_metadata in webpage['seed_labels'].items():
                pred_xpath = obj_metadata['pred']
                seed_id = iterators.get_keys_with_value(id_map, (obj_xpath, pred_xpath))[0]
                seeds.append(seed_id)

            # get not seed vertices
            # not_seeds = list(set(id_map.keys()) - set(seeds))
            not_seeds = []
            for seed in seeds:
                seed_obj_xpath, seed_pred_xpath = id_map[seed]
                seed_candidate_preds = webpage['candidate_pairs'][seed_obj_xpath]['pred_candidates']
                for seed_candidate_pred in seed_candidate_preds:
                    seed_candidate_pred_xpath = seed_candidate_pred['node']
                    if seed_candidate_pred_xpath != seed_pred_xpath:
                        not_seeds.append(
                            iterators.get_keys_with_value(id_map, (seed_obj_xpath, seed_candidate_pred_xpath))[0])

            seed1 = seeds[0]
            seed1_neighbours = [n for n in g.neighbors(seed1)]
            seed1_neighbours = sorted(seed1_neighbours,
                                      key=lambda seed1_neighbour: g.get_edge_data(seed1, seed1_neighbour)['weight'])
            seed1_neighbours = [x for x in seed1_neighbours if x not in seeds]
            best_seed1_neighbour = seed1_neighbours[0]

            # not seed = all nodes that are not in seed
            # worst_seed1_neighbour = seed1_neighbours[-1]
            # nodes_to_plot = seeds + [best_seed1_neighbour, worst_seed1_neighbour]
            # draw_graph(g, g_labels, nodes_to_plot=nodes_to_plot, nodes_to_color={'g': seeds, 'r': [best_seed1_neighbour]})

            # not seed = find nodes that surely are not seeds
            nodes_to_plot = seeds + [not_seeds[0], best_seed1_neighbour]
            # draw_graph(g, g_labels, nodes_to_plot=nodes_to_plot, nodes_to_color={'g': seeds, 'r': [not_seeds[0]]})

            # label propagation
            labels = {'seed': seeds, 'not_seed': not_seeds}
            new_labels = multi_rank_walk(g, labels)

            new_seeds = [vertex for vertex, label in new_labels.items() if label == 'seed' and vertex in nodes_to_plot]
            new_not_seeds = [vertex for vertex, label in new_labels.items() if
                             label == 'not_seed' and vertex in nodes_to_plot]
            # draw_graph(g, g_labels, nodes_to_plot=nodes_to_plot, nodes_to_color={'g': new_seeds, 'r': new_not_seeds})

            # go from vertex to page webpage nodes
            new_pred_obj_pairs = []
            for vertex_id, vertex_label in new_labels.items():
                if vertex_label == 'seed':
                    (obj_xpath, pred_xpath) = id_map[vertex_id]

                    obj_text = parsed_page.get_nodes_xpath(obj_xpath, clean=True)[0].text
                    pred_text = parsed_page.get_nodes_xpath(pred_xpath, clean=True)[0].text

                    new_pred_obj_pairs.append({'obj_xpath': obj_xpath, 'pred_xpath': pred_xpath, 'obj_text': obj_text,
                                               'pred_text': pred_text})

            # g = nx.Graph()
            # edges = [('A', 'X'), ('B', 'X'), ('X', 'Y'), ('C', 'X'), ('C', 'Y'), ('D', 'Y')]
            # g.add_edges_from(edges)
            #
            # labels = {'seed': ['A', 'B', 'D'], 'not_seed': ['C']}
            # new_labels = multi_rank_walk(g, labels)
            # print(new_labels)

            # for seed in seeds:
            #     g._node[seed]['label'] = 'seed'
            # #result = community.asyn_lpa_communities(g, weight='weight')
            # result = community.label_propagation_communities(g)
            # print(list(result))

            # for new_pair in new_pred_obj_pairs:
            #     print('{} - {}'.format(new_pair['obj_text'], new_pair['pred_text']))

            webpage['new_labels'] = new_pred_obj_pairs
            page_service.save(webpage)

    for template in templates:
        evaluate_results(page_service, template=template)
"""