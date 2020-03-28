from src.indexes.term_freq_index import TermFrequencyIndex
from src.html.webpage_beautifulsoup import ParsedPage           # to check
import src.utils.elapsed_timer as timer
import src.utils.string_utils as string_utils


class WebPageIndex:
    def __init__(self, page_service, mongodb):
        self.page_service = page_service
        self.mongodb = mongodb
        self.mongodb_index_collection = 'term_freq_indexes'

        self.all_webpage_templates = page_service.get_all_templates()

        # cache last index retrieved from mongodb
        self.last_template = None
        self.last_template_webpage_count = None
        self.last_index = None

    def _index_web_page(self, index, html):
        parsed_webpage = ParsedPage(html)
        text_fields = parsed_webpage.get_all_text_nodes(clean=True, only_text=True)
        text_fields = [string_utils.stem_sentence(text_field) for text_field in text_fields]

        # we don't want freq of terms on all webpages, but we want the numer of pages where the term appears
        text_fields = list(set(text_fields))

        for text_field in text_fields:
            index.index_term(text_field)

    def index_webpages_grouping_by_template(self):
        """
        creates a term-frequency index foreach webpage template, and save in mongodb
        :return:
        """
        print('indexing web pages...')

        page_service = self.page_service
        mongodb = self.mongodb

        mongodb.drop_collection(self.mongodb_index_collection)

        total_operation_count = page_service.count_all()
        status_printer = timer.StatusPrinter(total_operation_count, padding='      ')
        webpage_templates = self.all_webpage_templates
        for template in webpage_templates:
            index = TermFrequencyIndex(mongodb, template, self.mongodb_index_collection)
            template_pages = page_service.get_all(template=template)
            for page in template_pages:
                self._index_web_page(index, page['html'])
                status_printer.operation_done()
            index.save_index()
        status_printer.finish()

    def get_term_freq(self, webpage_template, term, normalized=False):
        if webpage_template not in self.all_webpage_templates:
            return None

        # reload index if cache_index is not the correct one
        if not webpage_template == self.last_template:
            self.last_index = TermFrequencyIndex(self.mongodb, webpage_template, self.mongodb_index_collection)
            self.last_template = webpage_template
            self.last_template_webpage_count = self.page_service.count_all(template=webpage_template)

        term = string_utils.clean_string(term)
        term = string_utils.stem_sentence(term)
        frequency = self.last_index.get_frequency(term)

        if normalized:
            return frequency / self.last_template_webpage_count
        else:
            return frequency




