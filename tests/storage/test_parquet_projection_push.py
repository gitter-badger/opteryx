"""
Test we can read from MinIO
"""
import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], "../.."))

import opteryx

from opteryx.storage.adapters.blob import DiskStorage
from opteryx.storage import register_prefix


def test_parquet_projection_pushdown():

    register_prefix("tests", DiskStorage)

    # with pushdown
    conn = opteryx.connect()
    cur = conn.cursor()
    cur.execute(
        f"SELECT MAX(following) FROM tests.data.formats.parquet WITH(NO_PARTITION);"
    )
    [a for a in cur.fetchall()]
    assert cur.stats["columns_read"] == 1

    conn = opteryx.connect()
    cur = conn.cursor()
    cur.execute(
        f"SELECT MAX(following), MAX(followers) FROM tests.data.formats.parquet WITH(NO_PARTITION);"
    )
    [a for a in cur.fetchall()]
    assert cur.stats["columns_read"] == 2

    # with pushdown disabled
    conn = opteryx.connect()
    cur = conn.cursor()
    cur.execute(
        f"SELECT MAX(following) FROM tests.data.formats.parquet WITH(NO_PARTITION, NO_PUSH_PROJECTION);"
    )
    [a for a in cur.fetchall()]
    assert cur.stats["columns_read"] == 13

    # without pushdown
    conn = opteryx.connect()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM tests.data.formats.parquet WITH(NO_PARTITION);")
    [a for a in cur.fetchall()]
    assert cur.stats["columns_read"] == 13


if __name__ == "__main__":
    test_parquet_projection_pushdown()
    print("✅ okay")
