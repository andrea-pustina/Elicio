import src.utils.string_utils as string_utils
import os

from src.utils.graph.pyrwr.ppr import PPR
import src.utils.iterators as iterators
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from src.html.webpage_lxml import ParsedPage
from src.service.webpage_service import check_pred_obj_pair
import math
from networkx.algorithms import community


def get_candidate_pred_obj_pairs(webpage, parsed_page):
    candidate_pairs = []
    id_map = {}  # {'obj_xpath+pred_xpath': id}
    curr_id = 0

    for obj_xpath, obj_metadata in webpage['candidate_pairs'].items():
        obj_text = obj_metadata['obj_text']
        obj_features = obj_metadata['features']

        candidate_preds = obj_metadata['pred_candidates']
        for candidate_pred in candidate_preds:
            candidate_pred_xpath = candidate_pred['node']
            candidate_pred_text = candidate_pred['text']
            candidate_pred_features = candidate_pred['features']

            candidate_pair = {'obj': {'xpath': obj_xpath,
                                      'text': obj_text,
                                      'features': obj_features},
                              'pred': {'xpath': candidate_pred_xpath,
                                       'text': candidate_pred_text,
                                       'features': candidate_pred_features},
                              'id': curr_id
                              }

            id_map[curr_id] = (obj_xpath, candidate_pred_xpath)
            curr_id += 1

            candidate_pairs.append(candidate_pair)


    # webpage_text_nodes = parsed_page.get_all_text_nodes(clean=True)
    # for text_node1 in webpage_text_nodes:
    #     for text_node2 in webpage_text_nodes:
    #         if not parsed_page.elements_equal(text_node1, text_node2):
    #             pred_xpath = candidate_pred['node']
    #             pred_text = candidate_pred['text']
    #             pred_features = candidate_pred['features']
    #
    #             candidate_pair = {'obj': {'xpath': obj_xpath,
    #                                       'text': obj_text,
    #                                       'features': obj_features},
    #                               'pred': {'xpath': candidate_pred_xpath,
    #                                        'text': candidate_pred_text,
    #                                        'features': candidate_pred_features},
    #                               'id': curr_id
    #                               }
    #
    #             id_map[curr_id] = (obj_xpath, candidate_pred_xpath)
    #             curr_id += 1
    #
    #             candidate_pairs.append(candidate_pair)

    return candidate_pairs, id_map


def get_similarity(features_obj1, features_pred1, features_obj2, features_pred2):
    similarity = 0

    # dom similarity
    if features_obj1['dom'] == features_obj2['dom'] and features_pred1['dom'] == features_pred2['dom']:
        similarity += 1

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


def multi_rank_walk(g, labels):
    """
    :param labels: ['class1': [list of vertices ids], 'class2': ...]
    """

    # each vertex has a score foreach class (class is a type of label) (score is computed with random_walk)
    # classes_scores = {vertex_id1: {class1: score1, class2:score2}, ...}
    classes_scores = defaultdict(dict)

    # run random walk foreach class
    for class_name, class_vertices in labels.items():

        # set all vertices to 0
        u = {vertex_id: 0 for vertex_id in g.nodes}    # u explanation is in personalized_page_rank()

        # set to 1 vertex that are of the current class
        for class_vertex in class_vertices:
            u[class_vertex] = 1.0

        # normalize u such as ||u||=1 (euclidean norm)
        norm_factor = math.sqrt(sum(u.values()))
        for vertex in u.keys():
            u[vertex] /= norm_factor
        #print(u)

        # compute class score
        class_scores = personalized_page_rank(g, u)

        # save class score
        for vertex_id, vertex_class_score in class_scores.items():
            classes_scores[vertex_id][class_name] = vertex_class_score

    # foreach vertex get the class with highest score
    # final_vertices_labels
    final_vertices_labels = {}
    for vertex_id, vertex_classes_scores in classes_scores.items():
        final_vertices_labels[vertex_id] = iterators.get_key_with_max_value(vertex_classes_scores)

    print('before: ' + str({label_name: len(labeled_vertices) for label_name, labeled_vertices in labels.items()}))
    print('after: ' + str(iterators.get_elements_frequency(list(final_vertices_labels.values()))))
    print('labels: {}'.format(labels))
    print('classes_scores: {}'.format(dict(classes_scores)))
    print('final_labels: {}'.format(final_vertices_labels))
    print('')

    return final_vertices_labels


def draw_graph(g, g_labels, nodes_to_plot=None, nodes_to_color=None):
    """

    :param g:
    :param g_labels: {vertex1: label1, ...}
    :param nodes_to_plot: [vertex1, ....]
    :param nodes_to_color: ['r': [vertex1, vertex2], ...]
    :return:
    """
    if nodes_to_plot is not None:
        g = g.subgraph(nodes_to_plot)
        g_labels = {vertex_id: vertex_label for vertex_id, vertex_label in g_labels.items() if vertex_id in nodes_to_plot}

    #pos = nx.spring_layout(g)  # positions for all nodes
    pos = nx.circular_layout(g)

    if nodes_to_color is not None:
        all_colored_nodes = []
        for color, colored_nodes in nodes_to_color.items():
            nx.draw_networkx_nodes(g, pos,
                                   nodelist=colored_nodes,
                                   node_color=color)
            all_colored_nodes.extend(colored_nodes)

        nx.draw_networkx_nodes(g, pos,
                               nodelist=list(set(g.nodes)-set(all_colored_nodes)),
                               node_color='b')

        nx.draw_networkx_edges(g, pos,
                               edgelist=list(g.edges),
                               edge_color='b')

        nx.draw_networkx_labels(g, pos, g_labels)
    else:
        nx.draw(g, pos=pos, labels=g_labels, with_labels=True)

    # plot edges weights
    edge_labels = nx.get_edge_attributes(g, 'weight')
    edge_labels = {vertices: "%.2f" % label for vertices, label in edge_labels.items()}  # round la
    nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, label_pos=0.3)

    # adjust fig margins to keep labels inside
    x_values, y_values = zip(*pos.values())
    x_max = max(x_values)
    x_min = min(x_values)
    x_margin = (x_max - x_min) * 0.30
    plt.xlim(x_min - x_margin, x_max + x_margin)

    plt.axis('off')
    plt.savefig("graph.png", dpi=1000)
    plt.show()


def personalized_page_rank(g, u):
    """
    At each step there is a nonzero probability the surfer goes to a random page (as opposed to following a link).
    If the choice of that random page is weighted (parameter u), then it is referred to as personalized PageRank

    :param g: networkx graph
    :param u: {vertex_id: probability1, ....}
    :return:
    """

    return nx.pagerank(g, personalization=u)


def propagate_labels(page_service, cfg, webpage_index):
    templates = page_service.get_all_field_values('template')
    #templates = ['movie-imdb']

    for template in templates:
        for webpage in page_service.get_all(template=template):
            if 'candidate_pairs' not in webpage:
                continue

            parsed_page = ParsedPage(webpage['html'])

            # get list of candidate pred-obj pairs (id_map is used to retrieve id, given pred and obj xpaths)
            # id_map = {'obj_xpath + '||' + pred_xpath': vertex_id}
            candidate_pairs, id_map = get_candidate_pred_obj_pairs(webpage, parsed_page)
            #print(candidate_pairs)

            # create similarity graph
            if len(candidate_pairs) == 0 or len(webpage['seed_labels']) == 0:
                continue

            g = nx.Graph()
            g.add_nodes_from([candidate_pair['id'] for candidate_pair in candidate_pairs])
            g_labels = {candidate_pair['id']: candidate_pair['obj']['text'][:4] + '||' + candidate_pair['pred']['text'][:4] for candidate_pair in candidate_pairs}
            for pair1 in candidate_pairs:
                for pair2 in candidate_pairs:
                    if pair1['obj']['xpath'] == pair2['obj']['xpath'] and pair1['pred']['xpath'] == pair2['pred']['xpath']:
                        continue

                    pair1_id = pair1['id']
                    pair2_id = pair2['id']
                    pairs_similarity = get_similarity(pair1['obj']['features'], pair1['pred']['features'], pair2['obj']['features'], pair2['pred']['features'])

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
                        not_seeds.append(iterators.get_keys_with_value(id_map, (seed_obj_xpath, seed_candidate_pred_xpath))[0])


            seed1 = seeds[0]
            seed1_neighbours = [n for n in g.neighbors(seed1)]
            seed1_neighbours = sorted(seed1_neighbours, key=lambda seed1_neighbour: g.get_edge_data(seed1, seed1_neighbour)['weight'])
            seed1_neighbours = [x for x in seed1_neighbours if x not in seeds]
            best_seed1_neighbour = seed1_neighbours[0]


            # not seed = all nodes that are not in seed
            # worst_seed1_neighbour = seed1_neighbours[-1]
            # nodes_to_plot = seeds + [best_seed1_neighbour, worst_seed1_neighbour]
            # draw_graph(g, g_labels, nodes_to_plot=nodes_to_plot, nodes_to_color={'g': seeds, 'r': [best_seed1_neighbour]})

            # not seed = find nodes that surely are not seeds
            nodes_to_plot = seeds + [not_seeds[0], best_seed1_neighbour]
            #draw_graph(g, g_labels, nodes_to_plot=nodes_to_plot, nodes_to_color={'g': seeds, 'r': [not_seeds[0]]})


            # label propagation
            labels = {'seed': seeds, 'not_seed': not_seeds}
            new_labels = multi_rank_walk(g, labels)

            new_seeds = [vertex for vertex, label in new_labels.items() if label == 'seed' and vertex in nodes_to_plot]
            new_not_seeds = [vertex for vertex, label in new_labels.items() if label == 'not_seed' and vertex in nodes_to_plot]
            #draw_graph(g, g_labels, nodes_to_plot=nodes_to_plot, nodes_to_color={'g': new_seeds, 'r': new_not_seeds})

            # go from vertex to page webpage nodes
            new_pred_obj_pairs = []
            for vertex_id, vertex_label in new_labels.items():
                if vertex_label == 'seed':
                    (obj_xpath, pred_xpath) = id_map[vertex_id]

                    obj_text = parsed_page.get_nodes_xpath(obj_xpath, clean=True)[0].text
                    pred_text = parsed_page.get_nodes_xpath(pred_xpath, clean=True)[0].text

                    new_pred_obj_pairs.append({'obj_xpath': obj_xpath, 'pred_xpath': pred_xpath, 'obj_text': obj_text, 'pred_text':pred_text})





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


def evaluate_results(page_service, template=None):
    retrieved_count = 0
    relevant_count = 0
    relevant_retrieved = []
    not_relevant_retrieved = []

    for webpage in page_service.get_all(template=template):
        if 'new_labels' not in webpage:
            continue

        page_retrieved_count = 0

        all_ground_truth_objs = []
        for pred, objs in webpage['ground_truth'].items():
            all_ground_truth_objs.extend(objs)
        page_relevant_count = len(list(set(all_ground_truth_objs)))

        # page_relevant_count = sum([len(objs) for pred, objs in webpage['ground_truth'].items()]) # objs in ground truth

        page_relevant_retrieved = []                     # pred-obj in new_labels that are correct
        page_not_relevant_retrieved = []                 # pred-obj in new_labels that are not correct

        for new_label in webpage['new_labels']:
            page_retrieved_count += 1

            obj_text = new_label['obj_text']
            pred_text = new_label['pred_text']

            new_label['file_name'] = webpage['file_name']
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
    print('         errors: {}'.format([(x['pred_text'], x['obj_text'], x['file_name']) for x in not_relevant_retrieved]))