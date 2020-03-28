import re
from similarity.levenshtein import Levenshtein
import hashlib
import fasttext
import numpy
import time

import nltk.data as nltk_data
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize

# print(string_utils.clean_string("Scree\"n saver 'Discovering\ Dengue/ Drugs â Together"))


nltk_data.path = ['./input_data/nltk']
stop_words = set(stopwords.words('english'))
stemmer = SnowballStemmer("english")


def clean_string(text):
    text = str(text)
    text = text.lower()

    # replace '-' with ' '
    text = text.replace('-', ' ')

    # replace '\n' with ' '
    text = text.replace('\n', ' ')

    # remove " \ / ' ; \n | $:
    regex = re.compile('["\\\\/\',;.\\|\-:\$]')
    clean_string = regex.sub('', text)

    # remove no utf8 char
    clean_string = clean_string.encode('utf-8', errors='ignore')
    regex = re.compile('\\\\...')
    clean_string = regex.sub('', str(clean_string))[2:-1]

    # remove first and last whitespaces
    clean_string = clean_string.strip()

    # remove multiple whitespaces
    clean_string = re.sub(' +', ' ', clean_string)

    # remove html entities
    clean_string = remove_substring_by_regex(clean_string, '&nbsp#[0-9]*')
    clean_string = remove_substring_by_regex(clean_string, '&nbs.*$')
    clean_string = clean_string.replace('&nbsp', '')
    clean_string = clean_string.replace('&nbspf', '')
    clean_string = clean_string.replace('&nbsppg', '')

    return clean_string


def compare_string(string1, string2, clean=False):
    if clean:
        string1 = clean_string(string1)
        string2 = clean_string(string2)

    if len(string1) < 10 and len(string2) < 10:
        equal_threshold = 0.85
    else:
        equal_threshold = 0.80

    # equal_threshold = equal_threshold * 100
    # similarity = fuzz.token_set_ratio(string1, string2)

    # remove substrings in brackets
    string1_cleaned = remove_substring_by_regex(string1, '\(.*\)').strip()
    string2_cleaned = remove_substring_by_regex(string2, '\(.*\)').strip()
    if string1_cleaned != '' and string2_cleaned != '':
        string1 = string1_cleaned
        string2 = string2_cleaned

    if string1=='' or string2=='':
        return False

    # calculate similarity
    total_len = len(string1)+len(string2)
    sim_engine = Levenshtein()
    distance = sim_engine.distance(string1, string2)
    similarity = (total_len - distance) / total_len

    # print("'{}' - '{}' -> {} [{}]".format(string1, string2, str(similarity >= equal_threshold), similarity))
    return similarity >= equal_threshold


def compare_string_meaning(s1, s2):
    # remove substrings in brackets
    string1_cleaned = remove_substring_by_regex(s1, '\(.*\)').strip()
    string2_cleaned = remove_substring_by_regex(s2, '\(.*\)').strip()
    if string1_cleaned != '' and string2_cleaned != '':
        s1 = string1_cleaned
        s2 = string2_cleaned
    else:
        s1 = s1.replace('(', '').replace(')', '')
        s2 = s2.replace('(', '').replace(')', '')

    s1 = clean_string(s1)
    s2 = clean_string(s2)

    s1 = remove_stop_word(s1)
    s2 = remove_stop_word(s2)

    s1 = stem_sentence(s1)
    s2 = stem_sentence(s2)

    equals = compare_string(s1, s2)
    # print(' {} - {} -> {}'.format(s1, s2, equals))
    return equals


def remove_stop_word(text):
    text = split_text_in_words(text)
    text = [w for w in text if not w in stop_words]
    return ' '.join(text)


def split_text_in_words(text):
    return word_tokenize(text)


def stem_word(word):
    return stemmer.stem(word)


def stem_sentence(sentence):
    tokenized_sentence = split_text_in_words(sentence)
    sentence = [stem_word(word) for word in tokenized_sentence]
    return ' '.join(sentence)


def stringify_time(time1, with_date=False):
    if with_date:
        return time.strftime("%H:%M:%S (%d/%m/%Y)", time.localtime(time1))
    else:
        return time.strftime("%H:%M:%S", time.localtime(time1))


def stringify_time_delta(seconds):
    seconds = int(seconds)

    if seconds is -1:
        return "-"

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if days > 0:
        return '%dd:%dh:%dm:%ds' % (days, hours, minutes, seconds)
    elif hours > 0:
        return '%dh:%dm:%ds' % (hours, minutes, seconds)
    elif minutes > 0:
        return '%dm:%ds' % (minutes, seconds)
    else:
        return '%ds' % (seconds,)


def stringify_int(number):
    if number >= 10000:
        return str(f'{number:,}')
    else:
        return str(number)


def get_bool(text):
    return text in ['true', '1', 't', 'y', 'yes', 'True', 'TRUE']


def remove_substring_by_regex(text, regex):
    return re.sub(regex, '', text)


def get_substring_by_regex(text, regex):
    return re.search(regex, text).group(0)


def hash_string(s, len=16):
    """

    :param s:
    :param len: max 48
    :return:
    """
    s = s.encode('utf-8')
    return int(hashlib.sha1(s).hexdigest(), 16) % (10 ** len)


class FastTextEmbedder():
    def __init__(self):
        self.model = fasttext.load_model("input_data/fasttext/dbpedia.bin")

    @staticmethod
    def get_euclidean_distance(v1, v2):
        return float(numpy.linalg.norm(v1 - v2))

    def get_embedding(self, s):
        return self.model[s.lower()]

    def get_distance(self, s1, s2):
        e1 = self.get_embedding(s1)
        e2 = self.get_embedding(s2)
        return self.get_euclidean_distance(e1, e2)


def insert_string_after_substring(string, substring, string_to_add):
    try:
        idx = string.index(substring) + len(substring)
        result = string[:idx] + string_to_add + string[idx:]
    except ValueError:
        result = string

    return result


def get_only_number(string1):
    return re.findall("\d+", string1)[0]