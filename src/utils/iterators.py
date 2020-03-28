import itertools
import operator


def map_nested_dicts(ob, func, map_also_dict_keys=False):
    if isinstance(ob, dict):
        if map_also_dict_keys:
            return {func(k): map_nested_dicts(v, func) for k, v in ob.items()}
        else:
            return {k: map_nested_dicts(v, func) for k, v in ob.items()}
    elif isinstance(ob, list):
        return [map_nested_dicts(elem, func) for elem in ob]
    else:
        return func(ob)


def flatten_list_of_lists(ll):
    return list(itertools.chain.from_iterable(ll))


def get_elements_frequency(list1, normalized=False):
    if normalized:
        list_len = len(list1)
        return {x: list1.count(x) / list_len for x in list1}
    else:
        return {x: list1.count(x) for x in list1}


def get_key_with_max_value(dict1):
    return max(dict1, key=dict1.get)


def get_keys_with_value(dict1, search_value):
    return [key for key, value in dict1.items() if value == search_value]


def get_max_int_value_in_nested_dictionary(d, curr_max=-float('inf'), absolute=False):
    if isinstance(d, int):
        if absolute:
            d = abs(d)
        return max(curr_max, d)
    elif isinstance(d, dict):
        for k, v in d.items():
            nested_max = get_max_int_value_in_nested_dictionary(v, curr_max, absolute=absolute)
            curr_max = max(curr_max, nested_max)
    elif isinstance(d, list):
        nested_max = max([get_max_int_value_in_nested_dictionary(v, curr_max, absolute=absolute) for v in d])
        curr_max = max(curr_max, nested_max)

    return curr_max


def merge_two_dicts(d1, d2):
    return {**d1, **d2}


def get_first(iterable, condition=lambda x: True):
    """
    Returns the first item in the `iterable` that
    satisfies the `condition`.

    If the condition is not given, returns the first item of
    the iterable.

    Raises `StopIteration` if no item satysfing the condition is found.

    >>> first( (1,2,3), condition=lambda x: x % 2 == 0)
    2
    >>> first(range(3, 100))
    3
    >>> first( () )
    Traceback (most recent call last):
    ...
    StopIteration
    """

    return next(x for x in iterable if condition(x))