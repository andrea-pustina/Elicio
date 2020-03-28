import time
from pymongo import MongoClient


class MongoDB():
    def __init__(self, host, user, psw, db_name):
        self.host = host
        self.user = user
        self.psw = psw
        self.db_name = db_name
        self.client = None
        self.db = None

    def connect(self):
        self.client = MongoClient(self.host, username=self.user, password=self.psw)
        self.db = self.client[self.db_name]

    def wait_and_connect(self, max_retry=10):
        print('connecting to mongodb... [.', end='')
        count = 0
        while True:
            try:
                count += 1
                if count > max_retry:
                    break
                self.connect()
                break
            except Exception:
                print('.', end='')
                time.sleep(2)
        print('] done')

    def disconnect(self):
        self.client.close()

    def insert_doc(self, collection, doc):
        collection = self.db[collection]
        doc_id = collection.insert_one(doc).inserted_id
        return doc_id

    def get_field_values(self, collection, field_name):
        collection = self.db[collection]
        return collection.distinct(field_name)

    def get_doc_one(self, collection, query):
        collection = self.db[collection]
        return collection.find_one(query)

    def get_doc_many(self, collection, query, no_cursor_timeout=False):
        collection = self.db[collection]
        return collection.find(query, no_cursor_timeout=no_cursor_timeout)

    def get_doc_all(self, collection, no_cursor_timeout=False):
        collection = self.db[collection]
        return collection.find(no_cursor_timeout=no_cursor_timeout)

    def count(self, collection, query):
        collection = self.db[collection]
        return collection.count_documents(query)

    def count_all(self, collection):
        return self.count(collection, {})

    def save_document(self, collection, document):
        collection = self.db[collection]
        return collection.save(document)

    def drop_collection(self, collection):
        try:
            self.db.drop_collection(collection)
        except:
            return False
        return True

    def remove_field(self, collection, field_name, query):
        collection = self.db[collection]
        return collection.update(query, {'$unset': {field_name: 1}}, multi=True)

    def remove_field_all(self, collection, field_name):
        return self.remove_field(collection, field_name, {})

    def delete_doc(self, collection, query):
        collection = self.db[collection]
        return collection.delete_one(query)
