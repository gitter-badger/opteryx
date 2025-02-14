"""
The best way to test a SQL engine is to throw queries at it.

This tests substitutions passed to the connection
"""
from datetime import datetime
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], "../.."))
import pyarrow
import pytest

import opteryx
from opteryx.storage.adapters import DiskStorage
from opteryx.utils.arrow import fetchmany
from opteryx.utils.display import ascii_table

# fmt:off
STATEMENTS = [
        ("SELECT * FROM $planets WHERE name = %s", ["Earth"], 1, 20),
        ("SELECT * FROM $planets WHERE id = %s", [4], 1, 20),
        ("SELECT * FROM $planets WHERE id > %s", [4], 5, 20),
        ("SELECT * FROM $planets WHERE name LIKE %s", ['%t%'], 5, 20),
        ("SELECT * FROM $planets WHERE name LIKE %s AND id > %s", ['%t%', 4], 4, 20),
        ("SELECT * FROM $planets WHERE id > %s AND name LIKE %s", [4, '%t%'], 4, 20),
        ("SELECT * FROM $planets WHERE id IN %s", [(1,2,3,)], 3, 20),
#        ("SELECT * FROM $planets WHERE %s = 9", [None], 9, 20),
        ("SELECT * FROM $planets WHERE BOOLEAN(id) IS %s", [True], 9, 20),
#        ("SELECT * FROM $planets WHERE \"'\" = %s", ["'"], 9, 20),
        ("SELECT * FROM $astronauts WHERE birth_date = %s", [datetime(year=1967, month=5, day=17)], 1, 19),
    ]
# fmt:on


@pytest.mark.parametrize("statement, subs, rows, columns", STATEMENTS)
def test_sql_battery(statement, subs, rows, columns):
    """
    Test an battery of statements
    """
    conn = opteryx.connect(reader=DiskStorage(), partition_scheme=None)
    cursor = conn.cursor()
    cursor.execute(statement, subs)

    cursor._results = list(cursor._results)
    if cursor._results:
        result = pyarrow.concat_tables(cursor._results, promote=True)
        actual_rows, actual_columns = result.shape
    else:  # pragma: no cover
        result = None
        actual_rows, actual_columns = 0, 0

    assert (
        rows == actual_rows
    ), f"Query returned {actual_rows} rows but {rows} were expected, {statement}\n{ascii_table(fetchmany(result, limit=10))}"
    assert (
        columns == actual_columns
    ), f"Query returned {actual_columns} cols but {columns} were expected, {statement}\n{ascii_table(fetchmany(result, limit=10))}"


if __name__ == "__main__":  # pragma: no cover

    print(f"RUNNING BATTERY OF {len(STATEMENTS)} CONNECTION TESTS")
    for statement, subs, rows, cols in STATEMENTS:
        print(statement)
        test_sql_battery(statement, subs, rows, cols)

    print("✅ okay")
