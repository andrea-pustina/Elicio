from src.html.webpage_lxml import ParsedPage
from src.utils import string_utils


class WebpageService:
    def __init__(self, mongodb, webpage_collection):
        self.mongodb = mongodb
        self.collection = webpage_collection

    def get_all(self, template=None, domain=None, no_cursor_timeout=False):
        if template:
            return self.mongodb.get_doc_many(self.collection, {'template': template}, no_cursor_timeout=no_cursor_timeout).batch_size(1)
        elif domain:
            return self.mongodb.get_doc_many(self.collection, {'domain': domain}, no_cursor_timeout=no_cursor_timeout).batch_size(1)
        else:
            return self.mongodb.get_doc_all(self.collection, no_cursor_timeout=no_cursor_timeout).batch_size(2)

    def get_all_field_values(self, field_name):
        return self.mongodb.get_field_values(self.collection, field_name)

    def get_all_templates(self):
        return self.get_all_field_values('template')

    def count_all(self, template=None, domain=None):
        if template:
            return self.mongodb.count(self.collection, {'template': template})
        elif domain:
            return self.mongodb.count(self.collection, {'domain': domain})
        else:
            return self.mongodb.count_all(self.collection)

    def remove_field_all(self, field_name):
        return self.mongodb.remove_field_all(self.collection, field_name)

    def save(self, webpage):
        return self.mongodb.save_document(self.collection, webpage)


def get_seed_labels(webpage, clean=False):
    parsed_page = ParsedPage(webpage['html'])
    seed_label_xpath = webpage['seed_labels']

    seed_label = {}
    for xpath_obj, xpath_pred in seed_label_xpath.items():
        node_obj = parsed_page.get_nodes_xpath(xpath_obj, clean=clean)[0]
        node_pred = parsed_page.get_nodes_xpath(xpath_pred, clean=clean)[0]

        seed_label[node_obj] = node_pred

    return seed_label


def get_true_preds(webpage, obj_text):
    ground_truth = webpage['ground_truth']
    ground_truth = {key: value for key, value in ground_truth.items() if key != "topic_entity_name"}

    true_preds = []
    for true_pred, true_objs in ground_truth.items():
        true_pred = string_utils.clean_string(true_pred)
        for true_obj in true_objs:
            if string_utils.compare_string(obj_text, true_obj, clean=True):
                # print('{} - {}'.format(obj_text, true_pred))
                true_preds.append(true_pred)

    return true_preds


def check_pred_obj_pair(webpage, pred_text, obj_text):
    true_preds = get_true_preds(webpage, obj_text)

    for true_pred in true_preds:
        if string_utils.compare_string(pred_text, true_pred, clean=True):
            return True

    return False


