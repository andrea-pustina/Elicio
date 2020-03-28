from lxml import etree
import src.utils.string_utils as string_utils
from io import StringIO
import src.utils.iterators as iterators
import random

from lxml.html.clean import Cleaner


class ParsedPage:
    def __init__(self, html):
        self.html = html
        parser = etree.HTMLParser(remove_comments=True)
        self.tree = etree.parse(StringIO(html), parser)

    @staticmethod
    def clean_html(html):
        # cleaner = Cleaner()
        # cleaner.javascript = False              # This is True because we want to activate the javascript filter
        # cleaner.style = False                   # This is True because we want to activate the styles & stylesheet filter
        # cleaner.remove_tags = ['noscript']      # remove -> content pulled to father
        # cleaner.kill_tags = ['noscript']        # kill -> content deleted
        # return cleaner.clean_html(html)

        # parser = etree.HTMLParser()
        # tree = etree.parse(StringIO(html), parser)
        # for elem in tree.findall("noscript"):
        #     elem.tag = "div"
        # #etree.strip_tags(tree, 'noscript')
        # return etree.tostring(tree).decode("utf-8")
        return html

    @staticmethod
    def clean_nodes_text(nodes):
        for node in nodes:
            node.text = string_utils.clean_string(node.text)
        nodes = list(filter(lambda x: x.text is not '', nodes))  # remove nodes with empty string
        return nodes

    def _filter_only_text_nodes(self, nodes):
        return list(filter(lambda x: x.text is not None and x.text != 'none' and 'select' not in self.get_xpath(x) and x.tag != 'style', nodes))  # remove nodes without text

    def check_if_node_has_parent_with_tag(self, parent_tag, node):
        parent = node.getparent()
        while parent is not None:
            if parent.tag == parent_tag:
                return True
            parent = parent.getparent()
        return False

    def get_nodes_all(self):
        # return list(self.tree.getroot().iter())
        return self.get_nodes_xpath('//*')   # credo ritorni leaf nodes

    def get_nodes_name(self, name):
        return self.get_nodes_xpath('//*[self::{}]'.format(name))

    def get_nodes_xpath(self, xpath, clean=True):
        try:
            nodes = self.tree.xpath(xpath)
        except etree.XPathEvalError:
            nodes = []

        if clean:
            nodes = self.clean_nodes_text(nodes)

        return nodes

    def get_html(self):
        return etree.tostring(self.tree)

    def get_leaf_nodes(self):
        return self.get_nodes_xpath('// *[not (*)]')

    def get_all_text_nodes(self, clean=False, only_text=False):
        text_nodes = self.get_nodes_all()
        text_nodes = self._filter_only_text_nodes(text_nodes)

        if clean:
            text_nodes = self.clean_nodes_text(text_nodes)

        if only_text:
            return [node.text for node in text_nodes]
        else:
            return list(text_nodes)

    def get_previous_text_nodes(self, node, clean=False, remove_ancestors=False):
        previous_nodes = []
        for curr_node in self.tree.iter():
            if self.elements_equal(node, curr_node):
                break
            previous_nodes.append(curr_node)

        previous_nodes = self._filter_only_text_nodes(previous_nodes)

        if remove_ancestors:
            ancestors = [node for node in curr_node.iterancestors()]
            previous_nodes = [node for node in previous_nodes if not any([self.elements_equal(node, ancestor) for ancestor in ancestors])]

        if clean:
            previous_nodes = self.clean_nodes_text(previous_nodes)

        previous_nodes.reverse()
        return previous_nodes

    def get_successor_text_nodes(self, node, clean=False):
        successor_nodes = []
        curr_node_found = False
        for curr_node in self.tree.iter():
            if curr_node_found:
                successor_nodes.append(curr_node)
            elif self.elements_equal(node, curr_node):
                curr_node_found = True

        successor_nodes = self._filter_only_text_nodes(successor_nodes)

        if clean:
            successor_nodes = self.clean_nodes_text(successor_nodes)

        return successor_nodes

    def get_xpath(self, node):
        return self.tree.getpath(node)

    def elements_equal(self, node1, node2):
        if node1.tag != node2.tag: return False
        if node1.text != node2.text: return False
        if node1.tail != node2.tail: return False
        if node1.attrib != node2.attrib: return False
        if len(node1) != len(node2): return False
        return all(self.elements_equal(c1, c2) for c1, c2 in zip(node1, node2))

    def xpath1_contains_xpath2(self, xpath1, xpath2):
        elt1 = self.get_nodes_xpath(xpath2)[0]
        elt2 = self.get_nodes_xpath(xpath1 + '/descendant::*')
        return elt1 in elt2

    def convert_all_lxml_nodes_to_xpath_in_nested_dict(self, ob):
        return iterators.map_nested_dicts(ob, lambda ob: self.get_xpath(ob) if isinstance(ob, etree._Element) else ob, map_also_dict_keys=True)

    # def get_elements_distance(self, elem1, elem2, normalized=False):
    #     founded_1 = False
    #     founded_2 = False
    #     distance = 0
    #     for curr_node in self.tree.iter():
    #         if self.elements_equal(elem1, curr_node):
    #             founded_1 = True
    #         if self.elements_equal(elem2, curr_node):
    #             founded_2 = True
    #
    #         if founded_1 and founded_2:
    #             break
    #         elif founded_1 or founded_2:
    #             distance += 1
    #
    #     if founded_1 and founded_2:
    #         if normalized:
    #             all_elem_count = len(self.get_all_text_nodes())
    #             return distance / all_elem_count
    #         else:
    #             return distance
    #     else:
    #         return None

    def get_previous_nodes_xpaths(self, xpath):
        previous_xpaths = []

        xpath = xpath.split('/')[1:]
        last_xpath = '/'
        for x in xpath:
            last_xpath += x
            previous_xpaths.append(last_xpath)
            last_xpath += '/'

        return previous_xpaths

    def get_node_dom_distance(self, xpath1, xpath2):
        node1_ancestors = set(self.get_previous_nodes_xpaths(xpath1))
        node2_ancestors = set(self.get_previous_nodes_xpaths(xpath2))

        return len(node1_ancestors.union(node2_ancestors) - node1_ancestors.intersection(node2_ancestors))




    def get_random_element(self, xpath=False):
        all_elements = list(self.tree.iter())
        random_element = random.choice(all_elements)

        if xpath:
            return self.get_xpath(random_element)
        else:
            return random_element


