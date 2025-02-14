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


class QueryStatistics:
    """
    Data object to collect information during query execution
    """

    def __init__(self):

        self._warnings = []

        self.count_blobs_found: int = 0
        self.count_data_blobs_read: int = 0
        self.count_non_data_blobs_read: int = 0
        self.bytes_read_data: int = 0
        self.bytes_processed_data: int = 0
        self.count_blobs_ignored_frames: int = 0
        self.rows_read: int = 0
        self.columns_read: int = 0

        self.read_errors: int = 0

        self.count_unknown_blob_type_found: int = 0
        self.count_control_blobs_found: int = 0
        self.bytes_read_control: int = 0

        self.partitions_found: int = 0
        self.partitions_scanned: int = 0
        self.partitions_read: int = 0
        self.time_scanning_partitions: int = 0

        self.segments_scanned: int = 0

        self.collections_read: int = 0
        self.document_pages: int = 0

        self.time_data_read: int = 0

        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.cache_oversize: int = 0
        self.cache_errors: int = 0

        # time spent on various steps
        self.time_planning: int = 0
        self.time_selecting: float = 0
        self.time_aggregating: float = 0
        self.time_ordering: float = 0

        self.start_time: int = 0
        self.end_time: int = 0

        self.page_splits: int = 0
        self.page_merges: int = 0

    def _ns_to_s(self, nano_seconds):
        """convert elapsed ns to s"""
        if nano_seconds == 0:
            return 0
        return nano_seconds / 1e9

    def warn(self, warning_text: str):
        """collect warnings"""
        if warning_text not in self._warnings:
            self._warnings.append(warning_text)

    @property
    def has_warnings(self):
        return len(self._warnings) > 0

    @property
    def warnings(self):
        return self._warnings

    def as_dict(self):
        """
        Return statistics as a dictionary
        """
        return {
            "count_blobs_found": self.count_blobs_found,
            "count_data_blobs_read": self.count_data_blobs_read,
            "count_non_data_blobs_read": self.count_non_data_blobs_read,
            "count_blobs_ignored_frames": self.count_blobs_ignored_frames,
            "count_unknown_blob_type_found": self.count_unknown_blob_type_found,
            "count_control_blobs_found": self.count_control_blobs_found,
            "read_errors": self.read_errors,
            "bytes_read_control": self.bytes_read_control,
            "bytes_read_data": self.bytes_read_data,
            "bytes_processed_data": self.bytes_processed_data,
            "rows_read": self.rows_read,
            "columns_read": self.columns_read,
            "time_data_read": self._ns_to_s(self.time_data_read),
            "time_total": self._ns_to_s(self.end_time - self.start_time),
            "time_planning": self._ns_to_s(self.time_planning),
            "time_scanning_partitions": self._ns_to_s(self.time_scanning_partitions),
            "time_selecting": self._ns_to_s(self.time_selecting),
            "time_aggregating": self._ns_to_s(self.time_aggregating),
            "time_ordering": self._ns_to_s(self.time_ordering),
            "partitions_found": self.partitions_found,
            "partitions_scanned": self.partitions_scanned,
            "partitions_read": self.partitions_read,
            "segments_scanned": self.segments_scanned,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_oversize": self.cache_oversize,
            "cache_errors": self.cache_errors,
            "collections_read": self.collections_read,
            "document_pages": self.document_pages,
            "page_splits": self.page_splits,
            "page_merges": self.page_merges,
        }
