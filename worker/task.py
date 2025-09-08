from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TaskState(Enum):
    # Discarded is the state for tasks that have errored enough times
    # that they're no longer eligible to be retried. Manual user intervention
    # is required for them to be tried again.
    DISCARDED = -101
    # Cancelled is the state for tasks that have been manually cancelled
    # by user request.
    CANCELLED = -100
    # Pending is a state for tasks to be parked while waiting for some
    # external action before they can be worked. Tasks in pending will never be
    # worked or deleted unless moved out of this state by the user.
    PENDING = 0
    # Processing is the state for tasks tasks which are actively running.
    PROCESSING = 1
    # Completed is the state for tasks that have successfully run to completion.
    COMPLETED = 100
    # Retryable is the state for tasks that have errored, but will be retried.
    RETRYABLE = 101

    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns metadata for the task state including name, value, and description.
        
        Returns:
            Dictionary containing name, value, and description of the state.
        """
        descriptions = {
            TaskState.DISCARDED: "Tasks that have errored too many times and require manual intervention",
            TaskState.CANCELLED: "Tasks that have been manually cancelled by user request", 
            TaskState.PENDING: "Tasks waiting for external action before they can be processed",
            TaskState.PROCESSING: "Tasks that are currently being processed",
            TaskState.COMPLETED: "Tasks that have successfully completed",
            TaskState.RETRYABLE: "Tasks that have failed but will be retried automatically",
        }
        
        return {
            "name": self.name.lower(),
            "value": self.value,
            "description": descriptions[self]
        }


class TaskItem(BaseModel):
    request: Any
    response_url: str

    def to_json(self) -> str:
        """
        Converts a TaskItem object into a JSON string.
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_string: str) -> "TaskItem":
        """
        Parses a JSON string into a TaskItem object.
        """
        return cls.model_validate_json(json_string)


class Task(BaseModel):
    id: str
    state: TaskState
    schedule_at: int
    attempt_count: int = 0
    attempted_at: Optional[int] = None
    attempted_error: List[str] = []
    finalized_at: Optional[int] = None
    items: List[TaskItem] = []
    created_at: int
    updated_at: int

    def to_json(self) -> str:
        """
        Converts a Task object into a JSON string.
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_string: str) -> "Task":
        """
        Parses a JSON string into a Task object.
        """
        return cls.model_validate_json(json_string)
