# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy

from pyarrow import compute


def list_contains(array, item):
    """
    does array contain item
    """
    if array is None:
        return False
    return item in set(array)


def list_contains_any(array, items):
    """
    does array contain any of the items in items
    """
    if array is None:
        return False
    return set(array).intersection(items) != set()


def list_contains_all(array, items):
    """
    does array contain all of the items in items
    """
    if array is None:
        return False
    return set(array).issuperset(items)


def search(array, item):
    """
    `search` provides a way to look for values across different field types, rather
    than doing a LIKE on a string, IN on a list, `search` adapts to the field type.
    """

    item = item[0]  # [#325]

    if len(array) > 0:
        array_type = type(array[0])
    else:
        return numpy.array([None], dtype=numpy.bool_)
    if array_type == str:
        # return True if the value is in the string
        return compute.match_substring(array, pattern=item, ignore_case=True)
    if array_type == numpy.ndarray:
        # converting to a set is faster for a handful of items which is what we're
        # almost definitely working with here - note compute.index is about 50x slower
        return numpy.array(
            [False if record is None else item in set(record) for record in array],
            dtype=numpy.bool_,
        )
    if array_type == dict:
        return numpy.array(
            [False if record is None else item in record.values() for record in array],
            dtype=numpy.bool_,
        )
    return numpy.array([[False] * array.shape[0]], dtype=numpy.bool_)
