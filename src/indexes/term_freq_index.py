import src.utils.string_utils as string_utils

class TermFrequencyIndex:
    def __init__(self, mongodb, index_name, mongodb_index_collection):
        self.mongodb = mongodb
        self.mongodb_index_collection = mongodb_index_collection
        self.index_name = index_name

        self.load_index()

    def index_term(self, term):
        self.index['term_count'] += 1

        term = string_utils.clean_string(term)

        if term not in self.index['terms_freq']:
            self.index['different_terms'] += 1
            self.index['terms_freq'][term] = 1
        else:
            self.index['terms_freq'][term] += 1

    def is_in_index(self, term):
        term = string_utils.clean_string(term)
        return term in self.index['terms_freq']

    def get_frequency(self, term):
        term = string_utils.clean_string(term)
        if not self.is_in_index(term):
            return 0
        else:
            return self.index['terms_freq'][term]

    def load_index(self):
        self.index = self.mongodb.get_doc_one(self.mongodb_index_collection, {'index_name': self.index_name})
        if self.index is None:
            self.index = {'index_name': self.index_name, 'term_count': 0, 'different_terms': 0, 'terms_freq': {}}

    def save_index(self):
        self.mongodb.save_document(self.mongodb_index_collection, self.index)

    def clear_index(self):
        self.mongodb.delete_doc(self.mongodb_index_collection, {'index_name': self.index_name})
        self.load_index()
        self.save_index()

    def __repr__(self):
        return "Index: " + str(self.index)