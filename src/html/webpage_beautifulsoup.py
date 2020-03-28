import bs4 as bs
import lxml as lxml
import itertools
import src.utils.string_utils as string_utils


def get_clean_soup(html):
    soup = bs.BeautifulSoup(html, 'lxml')

    # remove all script and style elements
    for script in soup(["script", "style"]):
        script.extract()  # rip it out

    # remove comments in html
    comments = soup.findAll(text=lambda text: isinstance(text, bs.Comment))
    [comment.extract() for comment in comments]

    return soup


class ParsedPage:
    def __init__(self, html):
        self.html = html
        self.soup = get_clean_soup(html)

    def get_tags(self, name):
        return self.soup.find_all(name)

    def remove_tags(self, name):
        tags = self.get_tags(name)
        [tag.extract() for tag in tags]

    def get_html(self):
        return self.soup.prettify()

    def get_all_text_nodes(self, clean=False, only_text=False):
        nodes = self.soup.html.findAll(text=True)

        if clean:
            for node in nodes:
                node.string = string_utils.clean_string(node.string)
            nodes = filter(lambda x: x.string is not '', nodes)      # remove nodes with empty string
            nodes = filter(lambda x: len(x.string) > 1, nodes)       # remove nodes with only one char

        if only_text:
            return [node.string for node in nodes]
        else:
            return list(nodes)

    @staticmethod
    def xpath(element):
        """
            Generate xpath of soup element
            :param element: bs4 text or node
            :return: xpath as string
            """
        components = []
        child = element if element.name else element.parent
        for parent in child.parents:
            """
            @type parent: bs4.element.Tag
            """
            previous = itertools.islice(parent.children, 0, parent.contents.index(child))
            xpath_tag = child.name
            xpath_index = sum(1 for i in previous if i.name == xpath_tag) + 1
            components.append(xpath_tag if xpath_index == 1 else '%s[%d]' % (xpath_tag, xpath_index))
            child = parent
        components.reverse()
        return '/%s' % '/'.join(components)

    def get_element(self, xpath):
        css_selector = cssify.cssify(xpath)
        return self.soup.select(css_selector)
