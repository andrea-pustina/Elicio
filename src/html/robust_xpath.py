#import pyximport; pyximport.install()
#import xslt_rule_extraction as xre

from src.html.webpage_lxml import ParsedPage
from lxml import html

MAX_DISTANCE = 3    #Infinite if None


def get_nodes(string_page, x_path):
    lxml_page = html.fromstring(string_page)
    return lxml_page.xpath(x_path)


def get_annotated_node(string_page, x_path):
    annotated_node = None
    nodes = get_nodes(string_page, x_path)
    if nodes:
        annotated_node = nodes[0]
    return annotated_node


def get_tag_feature(node, distance):
    return [("tag", distance, node.tag)]


def get_id_feature(node, distance):
    if 'id' in node.attrib:
        return [("id", distance, "*"), ("id", distance, node.attrib["id"])]
    else:
        return []


def get_class_feature(node, distance):
    if 'class' in node.attrib:
        return [("class", distance, "*"), ("class", distance, node.attrib["class"])]
    else:
        return []

def get_text_features(node, distance):
    if node.text is not None:
        node_text = node.text.strip()
        return [("text", distance, node_text)]
    else:
        return []


def get_features(annotated_node):
    current_node = annotated_node
    distance = 0
    features = []

    # if is_text -> node has no attribute
    if hasattr(current_node, 'is_text') and current_node.is_text:
        current_node = current_node.getparent()
        distance += 1

    while current_node is not None and (MAX_DISTANCE is None or distance < MAX_DISTANCE):
        tag_feauture = get_tag_feature(current_node, distance)
        id_feature = get_id_feature(current_node, distance)
        class_feature = get_class_feature(current_node, distance)
        text_feature = get_text_features(current_node, distance)

        features.extend(tag_feauture)
        features.extend(id_feature)
        features.extend(class_feature)
        features.extend(text_feature)

        current_node = current_node.getparent()
        distance += 1

    return features


def get_features_xpath(features):
    features = list(features)
    features.sort(reverse=True, key=lambda feature: feature[1])

    x_path = "/"

    max_distance = features[0][1]
    for distance in range(max_distance, -1, -1):
        x_path += '/'

        nodes_at_distance = list(filter(lambda x: x[1]==distance, features))

        nodes_tag_at_distance = list(filter(lambda x: x[0]=='tag', nodes_at_distance))
        nodes_id_at_distance = list(filter(lambda x: x[0]=='id', nodes_at_distance))
        nodes_class_at_distance = list(filter(lambda x: x[0]=='class', nodes_at_distance))
        nodes_text_at_distance = list(filter(lambda x: x[0] == 'text', nodes_at_distance))

        tag_at_distance = list(set([i[2] for i in nodes_tag_at_distance]))
        id_at_distance = list(set([i[2] for i in nodes_id_at_distance]))
        class_at_distance = list(set([i[2] for i in nodes_class_at_distance]))
        text_at_distance = list(set([i[2] for i in nodes_text_at_distance]))

        # add tag
        n_tag = len(tag_at_distance)
        if n_tag==0:
            x_path += "*"
        elif n_tag==1:
            x_path += tag_at_distance[0]
        else:
            x_path += 'invalid_tag'

        # add id
        for id in id_at_distance:
            if id == '*':
                x_path += '[@id]'
            else:
                x_path += '[@id="{}"]'.format(id)

        # add class
        for c in class_at_distance:
            if c == '*':
                x_path += '[@class]'
            else:
                x_path += '[@class="{}"]'.format(c)

        # add text
        for t in text_at_distance:
            x_path += '[contains(text(), "{}")]'.format(t)

    last = x_path[-1]
    if last=='*':
        x_path = x_path[0:-1] + 'node()'
    return x_path


def is_same_node(a, b, tagsame=True):
    if hasattr(a, 'attrib') and hasattr(b, 'attrib'):
        for attrib in a.attrib:
            if a.get(attrib) != b.get(attrib):
                return False
    elif (hasattr(a, 'attrib') and not hasattr(b, 'attrib')) or (not hasattr(a, 'attrib') and hasattr(b, 'attrib')):
        return False

    if a.text != b.text:
        return False
    if tagsame==True:
        if a.tag != b.tag:
            return False
    if a.prefix != b.prefix:
        return False
    if a.tail != b.tail:
        return False
    if a.values()!=b.values(): #may be redundant to the attrib matching
        return False
    if a.keys() != b.keys(): #may also be redundant to the attrib matching
        return False
    return True


def evaluate_precision_recall(annotated_pages, x_path_retrieved):
    true_positive = 0
    n_xpath_nodes = 0
    for html_page, x_path_golden in annotated_pages.items():
        page_xpath_nodes = get_nodes(html_page, x_path_retrieved)
        annotated_node = get_annotated_node(html_page, x_path_golden)
        if annotated_node is not None:
            for node in page_xpath_nodes:
                n_xpath_nodes += 1
                if is_same_node(node, annotated_node):
                    true_positive += 1

    n_annotated_nodes = 0
    for html_page, x_path_golden in annotated_pages.items():
        annotated_node = get_nodes(html_page, x_path_golden)
        if annotated_node:
            n_annotated_nodes += 1

    if n_xpath_nodes == 0:
        precision = 1
    else:
        precision = true_positive/n_xpath_nodes
    recall = true_positive/n_annotated_nodes
    return precision, recall


def evaluate_support(string_unannotated_pages, x_path_retrieved):
    n_supported_pages = 0
    for string_page in string_unannotated_pages:
        page_xpath_nodes = get_nodes(string_page, x_path_retrieved)
        if page_xpath_nodes:
            n_supported_pages += 1

    return n_supported_pages/len(string_unannotated_pages)


def evaluate_distance(x_path):
    return x_path.count('/')-2


def get_all_features(annotated_pages):
    features = []
    for annotated_page, xpath in annotated_pages.items():
        annotated_node = get_annotated_node(annotated_page, xpath)

        if annotated_node is not None:
            features.extend(get_features(annotated_node))
    return set(features)


def match_more_than_one_node_in_an_unannootaded_page(not_annotated_pages, x_path_retrieved):
    for string_page in not_annotated_pages:
        page_xpath_nodes = get_nodes(string_page, x_path_retrieved)
        if len(page_xpath_nodes)>1:
            return True
    return False


def extend_L_with_S(S, L):
    if not S:
        return L

    L_extended = set()
    for l in L:
        for s in S:
            if s not in l:
                l_extended = []
                l_extended.extend(l)
                l_extended.append(s)
                l_extended = frozenset(l_extended)
                L_extended.add(l_extended)


    return L_extended


def get_only_sets_wich_subsets_are_in_L(L_extended, L):
    L_pruned = set()
    for l_extended in L_extended:
        if len(l_extended)==1:
            if l_extended in L:
                L_pruned.add(l_extended)
        else:
            is_ok = True
            for feature in l_extended:
                l_extended_copy = l_extended.copy()
                l_extended_copy = set(l_extended_copy)
                l_extended_copy.remove(feature)
                l_extended_copy = frozenset(l_extended_copy)
                if l_extended_copy not in L:
                    is_ok = False
            if is_ok:
                L_pruned.add(l_extended)

    return L_pruned


def generate_c(S, L):
    """
    :param S: set of feature -> { ('id', 14, 'styleguide-v2'), ('id', 5, 'text-v2') }
    :param L: set of set of feature -> { {('id', 14, 'styleguide-v2')}, {('id', 3, 'styleguide-v2')} }
    :return:
    """

    L_extended = extend_L_with_S(S, L)
    L_pruned = get_only_sets_wich_subsets_are_in_L(L_extended, L)

    """
    print("\ngenerate c")
    print("n features: {}".format(len(S)))
    print("n candidates: {}".format(len(L)))
    print("n extended: {}".format(len(L_extended)))
    print("n pruned: {}".format(len(L_pruned)))
    """
    #print(L_pruned)

    return L_pruned


def generate_cluster_xpath(annotated_pages, not_annotated_pages):
    S = get_all_features(annotated_pages)

    C = set()
    for s in S:
        C.add(frozenset([s]))

    max_prec = 0

    max_prec_xpath = None
    min_dist = float("inf")
    max_sup = 0

    best_xpath = None
    min_dist_best_xpath = float("inf")
    max_sup_best_xpath = 0

    while C:
        L = set()
        print("C[{}]: {}".format(len(C),C))

        for c in C:
            c_xpath = get_features_xpath(c)
            precision, recall = evaluate_precision_recall(annotated_pages, c_xpath)
            support = evaluate_support(not_annotated_pages, c_xpath)
            distance = evaluate_distance(c_xpath)


            # print("features: {}".format(c))
            # print("c_path: {}".format(c_xpath))
            # print("precision: {}".format(precision))
            # print("recall: {}".format(recall))
            # print("support: {}".format(support))
            # print("distance: {}\n".format(distance))
            # print("match in annotated pages: {}".format(match_more_than_one_node_in_an_unannootaded_page(not_annotated_pages, c_xpath)))
            # print("min distance: {}".format(min_dist))
            # print("min distance_best_xpath: {}".format(min_dist_best_xpath))
            # print("max_support: {}".format(max_sup))
            # print("max_support_best_xpath: {}".format(max_sup_best_xpath))



            if recall==1:
                print("recall 1, x_path: {}".format(c_xpath))
                if precision<1 or match_more_than_one_node_in_an_unannootaded_page(not_annotated_pages, c_xpath):
                    L.add(c)
                    if precision>max_prec or (precision==max_prec and distance<min_dist) or (precision==max_prec and distance==min_dist and support>max_sup):
                        max_prec = precision
                        max_prec_xpath = c_xpath
                        min_dist = distance
                        max_sup = support
                        print('updated max_prec_x_path')
                elif distance<min_dist_best_xpath or (distance==min_dist_best_xpath and support>max_sup_best_xpath):
                    best_xpath = c_xpath
                    min_dist_best_xpath = distance
                    max_sup_best_xpath = support
                    max_prec = 1
                    print('updated best_x_path')

        for l in L.copy():
            l_xpath = get_features_xpath(l)
            support = evaluate_support(not_annotated_pages, l_xpath)
            distance = evaluate_distance(l_xpath)

            print("l_xpath: {}".format(l_xpath))
            print("support: {}".format(support))
            print("distance: {}".format(distance))

            if best_xpath is not None and (distance>min_dist_best_xpath or (distance==min_dist_best_xpath and support<=max_sup_best_xpath)):
                L.remove(l)

        C = generate_c(S, L)

    if best_xpath is not None:
        return best_xpath
    else:
        return max_prec_xpath


def get_robust_xpath(annotated_pages, not_annotated_pages):
    """

    :param annotated_pages: {html_page: xpath, html_page: xpath}
    :param not_annotated_pages: [html_page, html_page]
    :return:
    """
    x_path = generate_cluster_xpath(annotated_pages, not_annotated_pages)
    return x_path
