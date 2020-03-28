from collections import defaultdict
import src.utils.iterators as iterators
import src.utils.string_utils as string_utils
from statistics import mean
from src.html.webpage_lxml import ParsedPage
import src.utils.plotter as plot


def get_pages_preds(page_service, cfg, debug, templates=None):
    """
    get all pred_candidates of all pages grouping them by relation of them object with page topic
    :param page_service:
    :param debug:
    :return:
    """

    min_redundancy_pages = cfg['seed_labels']['min_redundancy_pages']

    if templates is None:
        templates = [None]

    all_preds = defaultdict(list)
    for template in templates:
        for page in page_service.get_all(template=template):
            if 'topic_related_candidate_pairs' not in page:
                continue

            page_pred_candidates = page['topic_related_candidate_pairs']

            # if an object compare more than one time in a page all his pred_candidates have to be merged
            # page preds grouped by (rel_with_topic, obj_id)
            # grouping by obj_id grant that preds of the same obj (that compare multiple time in the same page) will be merged together
            page_preds = defaultdict(list)
            for obj_node, obj_node_metadata in page_pred_candidates.items():
                obj_id = obj_node_metadata['obj_id']
                obj_kb_relations = obj_node_metadata['rel_types']

                node_pred_candidates_text = [pred_candidate['text'] for pred_candidate in obj_node_metadata['pred_candidates']]
                node_pred_candidates_text = list(set(node_pred_candidates_text))

                for rel_type_id, rel_type_text in obj_kb_relations.items():
                    # more relations an obj has, more we don't know which of them is the correct one
                    weight = 1 / len(obj_kb_relations)

                    page_preds[(rel_type_id, rel_type_text, obj_id, weight)].extend(node_pred_candidates_text)

            # add page preds to all_preds
            for (rel_type_id, rel_type_text, obj_id, weight), pred_candidates in page_preds.items():
                pred_candidates = list(set(pred_candidates))
                all_preds[(rel_type_id, rel_type_text)].append({'pred_cand': pred_candidates, 'weight': weight, 'page': page['file_name']})

    # remove preds where there are not pred_candidates from at least 3 different pages
    all_preds = {(rel_type_id, rel_type_text): pages_candidate_preds for (rel_type_id, rel_type_text), pages_candidate_preds in all_preds.items() if len(pages_candidate_preds) >= min_redundancy_pages}

    # stem all pred candidates
    all_preds = iterators.map_nested_dicts(all_preds, lambda obj: string_utils.stem_sentence(obj) if isinstance(obj, str) else obj)

    if debug:
        print('         all_pred_candidates:')
        for (pred_id, pred_text), pred_candidates in all_preds.items():
            print('                {}: {}'.format(pred_text, pred_candidates))

    return all_preds


def compute_redundancy_pred_score(all_preds, debug):
    """
    this score is computed considering all pages of same template. In kb there is relation A -R-> B and in the page
    A is the topic. If we find many different pages with some "objs B" (that in kb are related to page_topic by R)
    we can filter their pred candidate computing a score that consider frequencies of pred candidates for all that "objs B".
    If there is a pred cand that is in all objs B, that probably will be correct
    :param all_preds:
    :param debug:
    :return:
    """

    # calculate weighted frequency foreach pred_candidate (weighted by number_of_relations score)
    # frequency is how many times that pred is a pred_candidate of an object that is in relation R with page topic
    all_preds_freq = defaultdict(dict)
    for (pred_id, pred_text), candidate_synonims in all_preds.items():
        for page_candidate_synonims in candidate_synonims:
            for page_candidate_synonim in page_candidate_synonims['pred_cand']:
                if page_candidate_synonim not in all_preds_freq[(pred_id, pred_text)]:
                    all_preds_freq[(pred_id, pred_text)][page_candidate_synonim] = 0
                all_preds_freq[(pred_id, pred_text)][page_candidate_synonim] += (1 * page_candidate_synonims['weight'])

    if debug:
        print('         all_preds weighted freq:')
        for (pred_id, pred_text), candidate_synonims in all_preds_freq.items():
            print('                {}: {{'.format(pred_text), end='')

            sorted_candidate_synonims = sorted(candidate_synonims, key=candidate_synonims.get, reverse=True)
            for candidate_synonim in sorted_candidate_synonims:
                print('{}: {}, '.format(candidate_synonim, candidate_synonims[candidate_synonim]), end='')
            print('}')

    # calculate score (normalizing weighted freq)
    all_preds_score = defaultdict(dict)
    for (pred_id, pred_text), candidate_synonims in all_preds_freq.items():
        for candidate_synonim_text, candidate_synonim_freq in candidate_synonims.items():
            score = candidate_synonim_freq / len(all_preds[(pred_id, pred_text)])
            #score = 1 - score
            all_preds_score[(pred_id, pred_text)][candidate_synonim_text] = score

    if debug:
        print('         redundancy scores:')
        for (pred_id, pred_text), candidate_synonims in all_preds_score.items():
            print('                {}: {{'.format(pred_text), end='')

            sorted_candidate_synonims = sorted(candidate_synonims, key=candidate_synonims.get, reverse=True)
            for candidate_synonim in sorted_candidate_synonims:
                print('{}: {}, '.format(candidate_synonim, candidate_synonims[candidate_synonim]), end='')
            print('}')

    return all_preds_score


def compute_pred_synonim_scores(page_service, selenium_driver, cfg, debug, templates=None):
    print('      compute_pred_synonims...')
    print('         templates: {}'.format(templates))

    filter_pred_syns_factor = cfg['seed_labels']['filter_pred_syns_factor']

    # all_pred: {(pred_id, pred_text): [ {'pred_candidates': [pred_candidates_from_page_1], 'score': score}, ], ...}
    all_candidate_preds = get_pages_preds(page_service, cfg, debug, templates)
    #print(all_candidate_preds)

    # pred_redundancy_scores: {(pred_id, pred_text): {pred_candidate1: score, pred_candidate2: score}, ...}
    pred_scores = compute_redundancy_pred_score(all_candidate_preds, debug)

    if debug:
        print('         pred_scores:')
        for (pred_id, pred_text), candidate_preds in pred_scores.items():
            print('                {}: {{'.format(pred_text), end='')

            sorted_candidate_preds = sorted(candidate_preds, key=candidate_preds.get, reverse=True)
            for candidate_pred in sorted_candidate_preds:
                print("'{}': {}, ".format(candidate_pred, candidate_preds[candidate_pred]), end='')
            print('}')

        # plot predicate synonyms scores
        if cfg['seed_labels']['plot_redundancy_score_histogram']:
            scores = []
            for (pred_id, pred_text), candidate_preds in pred_scores.items():
                scores.extend(candidate_preds.values())
            plot.plot_histogram(list(scores), title=', '.join(templates))

    # foreach (pred_id, pred_text) get only best scores
    # get only cand_syn that have score>min_score
    # min score depend on max_score of candidate_synonims for that pred
    best_preds = defaultdict(dict)
    for (pred_id, pred_text), candidate_synonims in pred_scores.items():
        max_score = max(candidate_synonims.values())

        min_score_factor = filter_pred_syns_factor
        min_score = max_score * min_score_factor
        #min_score = 0.6
        #min_score = mean(candidate_synonims.values())

        candidate_synonims = {candidate_synonim: score for candidate_synonim, score in candidate_synonims.items() if score >= min_score}
        best_preds[(pred_id, pred_text)] = candidate_synonims

    if debug:
        print('         best_preds:')
        for (pred_id, pred_text), candidate_synonims in best_preds.items():
            print('                {}: {}'.format(pred_text, candidate_synonims))



    return {pred_id: candidate_preds for (pred_id, pred_text), candidate_preds in best_preds.items()}

