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

from .base_plan_node import BasePlanNode

from .aggregate_node import AggregateNode  # aggregate data
from .blob_reader_node import BlobReaderNode  # read file/blob datasets
from .collection_reader_node import CollectionReaderNode  # reader NoSQL datsets
from .column_selection_node import ColumnSelectionNode  # filter for SHOW COLUMNS
from .cross_join_node import CrossJoinNode  # CROSS JOIN
from .distinct_node import DistinctNode  # remove duplicate records
from .explain_node import ExplainNode  # EXPLAIN queries
from .function_dataset_node import FunctionDatasetNode  # Dataset Constructors
from .inner_join_node import InnerJoinNode  # INNER JOIN
from .internal_dataset_node import InternalDatasetNode  # Sample datasets
from .limit_node import LimitNode  # select the first N records
from .offset_node import OffsetNode  # skip a number of records
from .outer_join_node import OuterJoinNode  # LEFT/RIGHT/FULL OUTER JOIN
from .projection_node import ProjectionNode  # remove unwanted columns including renames
from .selection_node import SelectionNode  # filter unwanted rows
from .show_columns import ShowColumnsNode  # column details
from .sort_node import SortNode  # order by selected columns


# map join types to their implementations
_join_nodes = {
    "CrossJoin": CrossJoinNode,
    "CrossJoinUnnest": CrossJoinNode,
    "FullOuter": OuterJoinNode,
    "Inner": InnerJoinNode,
    "LeftOuter": OuterJoinNode,
    "RightOuter": OuterJoinNode,
}

# map reader types to their implementation
_reader_nodes = {
    "Blob": BlobReaderNode,  # (disk, gcs, minio, s3)
    "Collection": CollectionReaderNode,  # (mongodb, firestore)
    "Function": FunctionDatasetNode,
    "Internal": InternalDatasetNode,
    "SubQuery": BlobReaderNode,  # ?? <- this shouldn't be a reader
}


def join_factory(mode):
    return _join_nodes[mode]


def reader_factory(mode):
    return _reader_nodes[mode]
