from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import math
import src.utils.string_utils as string_utils
import src.utils.files as files
import re
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.color import Color
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from src.html.webpage_lxml import ParsedPage
from shapely.geometry import Polygon
import src.html.webpage_lxml as webpage_lxml
from lxml import etree
from io import StringIO


import random
import colorsys


def two_point_distance(x1, y1, x2, y2, increase_vertical_relevance=False):
    dy = y2 - y1
    dx = x2 - x1

    if increase_vertical_relevance:
        dy = dy * 1.5

    return math.sqrt((dy) ** 2 + (dx) ** 2)


def rect_distance(a_x1, a_y1, a_x2, a_y2, b_x1, b_y1, b_x2, b_y2, increase_vertical_relevance=False):
    """
    min distance between rect a and rect b
    """

    left = b_x2 < a_x1
    right = a_x2 < b_x1
    bottom = b_y2 < a_y1
    top = a_y2 < b_y1

    if top and left:
        return two_point_distance(a_x1, a_y2, b_x2, b_y1, increase_vertical_relevance)
    elif left and bottom:
        return two_point_distance(a_x1, a_y1, b_x2, b_y2, increase_vertical_relevance)
    elif bottom and right:
        return two_point_distance(a_x2, a_y1, b_x1, b_y2, increase_vertical_relevance)
    elif right and top:
        return two_point_distance(a_x2, a_y2, b_x1, b_y1, increase_vertical_relevance)
    elif left:
        return a_x1 - b_x2
    elif right:
        return b_x1 - a_x2
    elif bottom:
        d = a_y1 - b_y2
        if increase_vertical_relevance:
            d = d * 1.5
        return d
    elif top:
        d = b_y1 - a_y2
        if increase_vertical_relevance:
            d = d * 1.5
        return d
    else:             # rectangles intersect
        return 0.


class SeleniumDriver:
    def __init__(self, load_page_timeout):
        self.load_page_timeout = load_page_timeout
        self.driver = None

    def init(self):
        #self.driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
        self.driver = webdriver.Chrome(ChromeDriverManager().install())

        # options = webdriver.ChromeOptions()
        # options.add_argument("--enable-javascript")
        # self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        # define strategy to understand when page is loaded
        # caps = DesiredCapabilities().CHROME
        # # caps["pageLoadStrategy"] = "normal"  # complete
        # caps["pageLoadStrategy"] = "eager"  # interactive
        # # caps["pageLoadStrategy"] = "none"
        # self.driver = webdriver.Chrome(ChromeDriverManager().install(), desired_capabilities=caps)

        self.driver.set_window_size(1024, 768)
        self.driver.set_page_load_timeout(self.load_page_timeout)


        # self.driver.implicitly_wait(10)

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def open_tab(self, number):
        if self.driver is None:
            self.init()

        self.driver.execute_script("window.open('about:blank', 'tab{}');".format(number))

    def select_tab(self, number):
        self.driver.switch_to.window("tab{}".format(number))

    def set_page(self, html):
        if self.driver is None:
            self.init()

        #print(html)

        files.create_dir('./generated_data/selenium/')
        with open("./generated_data/selenium/tmp_webpage_file.html", "w") as text_file:
            text_file.write(html)

        webpage_file_full_path = files.get_file_absolute_path('./generated_data/selenium/tmp_webpage_file.html')

        try:
            self.driver.get("file://" + webpage_file_full_path)

            # from selenium.webdriver.support.wait import WebDriverWait
            # from selenium.webdriver.support import expected_conditions as EC
            # from selenium.webdriver.common.by import By
            # parsed_page = ParsedPage(html)
            # random_node = parsed_page.get_all_text_nodes()[15]
            # wait = WebDriverWait(self.driver, 10)
            # wait.until(EC.visibility_of_element_located((By.XPATH, '//+[text()="{}"'.format(random_node.text))))

        except TimeoutException:
            pass

        #print(self.page_has_loaded())

    def get_element(self, xpath):
        # xpath = xpath.replace('svg', '*[local-name()="svg"]')
        #if 'comment()' in xpath:
        #    return None

        return self.driver.find_element_by_xpath(xpath)

    def get_elements(self, xpath):
        return self.driver.find_elements_by_xpath(xpath)

    def get_element_size(self, element):
        width = element.size['width']
        height = element.size['height']
        return width, height

    def get_element_corners(self, element):
        width, height = self.get_element_size(element)

        x1 = element.location['x']
        y1 = element.location['y']

        x2 = element.location['x'] + width
        y2 = element.location['y']

        x3 = element.location['x']
        y3 = element.location['y'] + height

        x4 = element.location['x'] + width
        y4 = element.location['y'] + height

        return [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]

    def get_elements_distance(self, xpath1, xpath2, normalized=False, increase_vertical_relevance=False):
        element1 = self.get_element(xpath1)
        element2 = self.get_element(xpath2)

        x1 = element1.location['x']
        y1 = element1.location['y']

        x2 = element2.location['x']
        y2 = element2.location['y']

        if normalized:
            window_size = self.driver.get_window_size()
            width = window_size['width']
            height = window_size['height']

            x1 /= width
            x2 /= width
            y1 /= height
            y2 /= height

        dy = y2 - y1
        dx = x2 - x1

        if increase_vertical_relevance:
            dy *= 1.5

        distance = math.sqrt((dy) ** 2 + (dx) ** 2)
        return distance

    # def get_elements_distance(self, xpath1, xpath2, normalized=False, increase_vertical_relevance=False):
    #     element1 = self.get_element(xpath1)
    #     element2 = self.get_element(xpath2)
    #
    #     x1 = element1.location['x']
    #     y1 = element1.location['y']
    #
    #     x2 = element2.location['x']
    #     y2 = element2.location['y']
    #
    #     distance = two_point_distance(x1, y1, x2, y2, increase_vertical_relevance=increase_vertical_relevance)
    #
    #     return distance

    def get_elements_min_distance(self, corners1, corners2):
        distance = rect_distance(corners1[0][0], corners1[0][1], corners1[3][0], corners1[3][1], corners2[0][0], corners2[0][1], corners2[3][0], corners2[3][1])
        return distance

    def get_elements_distances(self, xpath1, xpath2):
        elem1 = self.get_element(xpath1)
        elem2 = self.get_element(xpath2)

        corners1 = self.get_element_corners(elem1)
        corners2 = self.get_element_corners(elem2)

        # print(self.get_element_size(elem1))
        # print(self.get_element_size(elem2))
        #
        # print(corners1)
        # print(corners2)

        horizontal_distances = {'left-left': (corners1[0][0] - corners2[0][0]),
                                'left-right': (corners1[0][0] - corners2[1][0]),
                                'right-left': (corners1[1][0] - corners2[0][0]),
                                'right-right': (corners1[1][0] - corners2[1][0])}

        vertical_distances = {'up-up': (corners1[0][1] - corners2[0][1]),
                              'up-down': (corners1[0][1] - corners2[2][1]),
                              'down-up': (corners1[2][1] - corners2[1][1]),
                              'down-down': (corners1[2][1] - corners2[2][1])}

        origin_distance = two_point_distance(corners1[0][0], corners1[0][1], corners2[0][0], corners2[0][1])
        min_distance = self.get_elements_min_distance(corners1, corners2)

        distances = {'horizontal': horizontal_distances,
                     'vertical': vertical_distances,
                     'min_distance': min_distance,
                     'origin_distance': origin_distance}

        return distances


    def get_elements_vertical_distance(self, elem1, elem2):
        y1 = elem1.location['y']
        y2 = elem2.location['y']

        return abs(y2 - y1)

    def is_above_and_on_the_left(self, xpath1, xpath2):
        """ check if elem1 is on the left and above of elem2 """

        element1 = self.get_element(xpath1)
        element2 = self.get_element(xpath2)

        x1 = element1.location['x']
        y1 = element1.location['y']
        x2 = element2.location['x']
        y2 = element2.location['y']

        # print('({}, {}) ({}, {})'.format(x1, y1, x2, y2))

        if x1 <= x2 and y1 <= y2:
            return True
        else:
            return False

    def get_font_size(self, element):
        font_size = element.value_of_css_property("font-size")
        return string_utils.get_only_number(font_size)

    def get_font_family(self, element):
        return element.value_of_css_property("font-family")

    def get_font_weight(self, element):
        return element.value_of_css_property("font-weight")

    def get_text_alignment(self, element):
        return element.value_of_css_property("text-align")

    def get_color(self, element):
        rgb = element.value_of_css_property("color")
        return Color.from_string(rgb).hex

    def get_corrected_html(self):
        # style_elements = self.get_elements('//style')
        # style_contents = [element.get_attribute('innerHTML') for element in style_elements]
        #
        # print(len(style_contents))
        #
        # html_without_css = self.driver.execute_script("return document.documentElement.outerHTML;")
        #
        # parser = etree.HTMLParser(remove_comments=True)
        # tree = etree.parse(StringIO(html_without_css), parser)
        #
        # head = tree.find("//head")
        # for style_content in style_contents:
        #     head.append(etree.XML("<style>{}</style>".format(style_content)))
        #
        # html_with_css = etree.tostring(tree)
        #
        # print(len(html_without_css))
        # print(len(html_with_css))
        #
        # return html_with_css

        return self.driver.execute_script("return document.documentElement.outerHTML;")
        #return self.driver.page_source

    def color_elements(self, xpaths):
        xpaths = list(filter(lambda xpath: 'svg' not in xpath, xpaths))

        # bright random color
        r = lambda: random.randint(100, 255)
        random_color = '#%02X%02X%02X' % (r(), r(), r())

        for xpath in xpaths:
            try:
                element = self.get_element(xpath)
                self.driver.execute_script("arguments[0].setAttribute('style', 'background-color: %s')" % random_color, element)
            except NoSuchElementException:
                print('{} not colored!'.format(xpath))

    def get_elements_in_the_middle(self, xpath1, xpath2, only_text=False):
        """
        element1 is up-left of elem2
        """
        try:
            elem1 = self.get_element(xpath1)
            elem2 = self.get_element(xpath2)
        except NoSuchElementException:
            return []

        # get elements that are in the middle considering DOM
        parsed_page = webpage_lxml.ParsedPage(self.get_corrected_html())
        try:
            elem1_successors = parsed_page.get_successor_text_nodes(parsed_page.get_nodes_xpath(xpath1)[0])
            elem2_previous = parsed_page.get_previous_text_nodes(parsed_page.get_nodes_xpath(xpath2)[0], remove_ancestors=True)
        except IndexError:
            return []

        elem1_successors = [parsed_page.get_xpath(node) for node in elem1_successors]
        elem2_previous = [parsed_page.get_xpath(node) for node in elem2_previous]

        dom_middle_nodes = list(set(elem1_successors).intersection(set(elem2_previous)))
        dom_middle_nodes = list(filter(lambda xpath: 'noscript' not in xpath, dom_middle_nodes))
        #print(dom_middle_nodes)
        #return (dom_middle_nodes)

        elem1_corners = self.get_element_corners(elem1)
        elem2_corners = self.get_element_corners(elem2)

        quadrangle = [elem1_corners[2], elem1_corners[3], elem2_corners[0], elem2_corners[1]]
        middle_nodes = []
        for dom_middle_node in dom_middle_nodes:
            dom_middle_node_elem = self.get_element(dom_middle_node)
            dom_middle_node_corners = self.get_element_corners(dom_middle_node_elem)
            if check_if_node_is_in_quadrangle(quadrangle, dom_middle_node_corners):
                middle_nodes.append(dom_middle_node)

        if only_text:
            middle_nodes_text = []
            for middle_node_xpath in middle_nodes:
                middle_node = parsed_page.get_nodes_xpath(middle_node_xpath)
                if len(middle_node) > 0:
                    middle_node_text = middle_node[0].text
                    middle_nodes_text.append(middle_node_text)
            return middle_nodes_text

            # return [parsed_page.get_nodes_xpath(middle_node)[0].text for middle_node in middle_nodes]
        else:
            return middle_nodes


def check_if_node_is_in_quadrangle(quadrangle, node_corners):
    """
    v = vertex
    :param quadrangle: [v1, v2, v3, v4]
    :param node: [v1, v2, v3, v4]
    :return:
    """

    p1 = Polygon(quadrangle)
    p2 = Polygon(node_corners)
    return p1.intersects(p2) > 0
