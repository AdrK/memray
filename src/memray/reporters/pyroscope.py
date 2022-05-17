import linecache

from typing import Any
from typing import Dict
from typing import Iterable

from memray import MemoryRecord
from memray import AllocationRecord

from memray.reporters.frame_tools import StackFrame
from memray.reporters.frame_tools import is_cpython_internal


def with_converted_children_dict(node: Dict[str, Any]) -> Dict[str, Any]:
    stack = [node]
    while stack:
        the_node = stack.pop()
        the_node["children"] = [child for child in the_node["children"].values()]
        stack.extend(the_node["children"])
    return node


def create_framegraph_node_from_stack_frame(stack_frame: StackFrame) -> Dict[str, Any]:
    function, filename, lineno = stack_frame

    name = (
        # Use the source file line.
        linecache.getline(filename, lineno)
        # Or just describe where it is from
        or f"{function} at {filename}:{lineno}"
    )
    return {
        "name": name,
        "location": [str(part) for part in stack_frame],
        "value": 0,
        "children": {},
        "n_allocations": 0,
        "thread_id": 0,
        "interesting": True,
    }


class Pyroscope:

    def __init__(
        self,
        data: Dict[str, Any],
        *,
        memory_records: Iterable[MemoryRecord],
    ) -> None:
        super().__init__()
        self.data = data
        self.memory_records = memory_records

    @classmethod
    def update_snapshot(cls, snapshot: Iterable[AllocationRecord], native: bool) -> None:
        data: Dict[str, Any] = {
            "name": "<root>",
            "location": ["<tracker>", "<b>memray</b>", 0],
            "value": 0,
            "children": {},
            "n_allocations": 0,
            "thread_id": "0x0",
            "interesting": True,
        }

        unique_threads = set()
        for record in snapshot:
            size = record.size
            thread_id = record.thread_name

            data["value"] += size
            data["n_allocations"] += record.n_allocations

            current_frame = data
            stack = (
                tuple(record.hybrid_stack_trace())
                if native
                else record.stack_trace()
            )
            for index, stack_frame in enumerate(reversed(stack)):
                if is_cpython_internal(stack_frame):
                    continue
                if (stack_frame, thread_id) not in current_frame["children"]:
                    node = create_framegraph_node_from_stack_frame(stack_frame)
                    current_frame["children"][(stack_frame, thread_id)] = node

                current_frame = current_frame["children"][(stack_frame, thread_id)]
                current_frame["value"] += size
                current_frame["n_allocations"] += record.n_allocations
                current_frame["thread_id"] = thread_id
                unique_threads.add(thread_id)

        transformed_data = with_converted_children_dict(data)
        transformed_data["unique_threads"] = sorted(unique_threads)
