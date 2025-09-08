from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from tts import TextToSpeechRequest, TextToSpeechResponse
from worker import Task, TaskItem, TaskState

router = APIRouter()


@router.post(
    "/api/tts",
    response_model=TextToSpeechResponse,
    tags=["tts"],
    summary="Convert Text to Speech",
    description="Synthesize text into speech using the specified voice",
    response_description="Audio data encoded as base64 along with the original request",
    responses={
        200: {
            "description": "Successfully generated speech audio",
            "content": {
                "application/json": {
                    "example": {
                        "audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqF...",
                        "request": {"text": "Hello, world!", "voice_id": "kokoro.af_heart", "metadata": {}},
                    }
                }
            },
        },
        400: {
            "description": "Invalid request parameters",
            "content": {"application/json": {"example": {"detail": "Invalid voice_id provided"}}},
        },
        500: {
            "description": "Internal server error during synthesis",
            "content": {"application/json": {"example": {"detail": "Failed to generate speech audio"}}},
        },
    },
)
async def text_to_speech(request: TextToSpeechRequest) -> TextToSpeechResponse:
    """
    Convert text to speech using the specified voice.

    **Parameters:**
    - **text**: The text to convert to speech (required)
    - **voice_id**: The voice identifier to use for synthesis (required)
    - **metadata**: Additional metadata for the request (optional)

    **Voice IDs:**
    Use one of the available voice identifiers. Examples:
    - `kokoro.af_heart` - American Female, warm and friendly
    - `kokoro.am-adam` - American Male, clear and professional
    - `kokoro.bf-emma` - British Female, elegant and refined
    - `kokoro.bm-george` - British Male, authoritative and clear

    **Returns:**
    - **audio**: Base64-encoded audio data (WAV format)
    - **request**: Echo of the original request for reference

    **Example Usage:**
    ```json
    {
        "text": "Hello, how are you today?",
        "voice_id": "kokoro.af_heart",
        "metadata": {"session_id": "abc123"}
    }
    ```
    """

    try:
        response = await request.execute_async()
        return response
    except Exception:
        raise


# Legacy endpoint for backward compatibility
@router.post(
    "/tts",
    response_model=TextToSpeechResponse,
    tags=["tts"],
    summary="Convert Text to Speech (Legacy)",
    description="Legacy endpoint - use /api/tts instead",
    deprecated=True,
)
async def text_to_speech_legacy(request: TextToSpeechRequest) -> TextToSpeechResponse:
    """Legacy endpoint - use /api/tts instead"""
    return await text_to_speech(request)


class PublishTasksRequest(BaseModel):
    items: List[TextToSpeechRequest] = Field(..., min_length=1, description="List of request items to enqueue")


class PublishTasksResponse(BaseModel):
    task_ids: List[str]


class TaskListResponse(BaseModel):
    tasks: List[Task]
    next_cursor: Optional[int] = Field(None, description="Cursor for next page (schedule_at value)")


@router.post(
    "/api/tasks",
    response_model=PublishTasksResponse,
    tags=["tasks"],
    summary="Create a new TTS task",
    description="Create a new TTS task containing multiple text-to-speech requests",
    responses={
        200: {"description": "Task created successfully"},
        400: {"description": "Invalid request"},
    },
)
async def create_task(req: Request, body: PublishTasksRequest) -> PublishTasksResponse:
    """
    Create a new TTS task with multiple items.
    
    **Parameters:**
    - **items**: List of text-to-speech requests to include in the task
    
    **Returns:**
    - **task_ids**: List of created task IDs
    """
    items: List[TaskItem] = [TaskItem(request=ti, response_url="") for ti in body.items]

    if not items:
        return PublishTasksResponse(task_ids=[])

    task = Task(
        id="",  # let queue assign ULID
        state=TaskState.PENDING,
        schedule_at=0,  # will be set by queue
        items=items,
        item_count=len(items),
        created_at=0,
        updated_at=0,
    )

    worker_queue = req.app.state.worker_queue  # type: ignore[attr-defined]
    task_ids = await worker_queue.enqueue([task])
    return PublishTasksResponse(task_ids=task_ids)


# Legacy endpoint for backward compatibility
@router.post(
    "/tts/queue/task",
    response_model=PublishTasksResponse,
    tags=["tasks"],
    summary="Publish a TTS task to queue with multiple items (Legacy)",
    description="Legacy endpoint - use /api/tasks instead",
    deprecated=True,
)
async def publish_tts_task_legacy(req: Request, body: PublishTasksRequest) -> PublishTasksResponse:
    """Legacy endpoint - use /api/tasks instead"""
    return await create_task(req, body)


class TaskStateInfo(BaseModel):
    name: str = Field(..., description="The state name (e.g., 'PENDING')")
    value: int = Field(..., description="The numeric value of the state")
    description: str = Field(..., description="Human-readable description of the state")

class AllStatesResponse(BaseModel):
    states: List[TaskStateInfo]

@router.get(
    "/api/task-states",
    response_model=AllStatesResponse,
    tags=["tasks"],
    summary="List all available task states",
    description="Retrieve information about all available task states",
    responses={
        200: {"description": "List of all available task states"},
    },
)
async def list_task_states() -> AllStatesResponse:
    """
    Get information about all available task states.
    
    **Returns:**
    List of all task states with their names, numeric values, and descriptions.
    """
    states = []
    for task_state in TaskState:
        metadata = task_state.get_metadata()
        state_info = TaskStateInfo(**metadata)
        states.append(state_info)
    
    return AllStatesResponse(states=states)


@router.get(
    "/api/tasks",
    response_model=TaskListResponse,
    tags=["tasks"],
    summary="List tasks",
    description="Retrieve tasks with cursor-based pagination",
    responses={
        200: {"description": "List of tasks"},
        400: {"description": "Invalid query parameter"},
    },
)
async def list_tasks(
    req: Request,
    limit: int = Query(default=50, ge=1, le=100, description="Number of tasks to return (max 100)"),
    cursor: Optional[int] = Query(default=None, description="Cursor for pagination (schedule_at timestamp)"),
    state: Optional[str] = Query(default=None, description="Filter by task state")
) -> TaskListResponse:
    """
    List tasks with optional state filtering and cursor-based pagination.
    
    **Parameters:**
    - **limit**: Number of tasks to return (1-100, default: 50)
    - **cursor**: Pagination cursor (schedule_at timestamp)
    - **state**: Optional state filter. Valid values:
      - DISCARDED (-101): Tasks that have errored too many times
      - CANCELLED (-100): Manually cancelled tasks  
      - PENDING (0): Tasks waiting for external action
      - PROCESSING (1): Currently running tasks
      - COMPLETED (100): Successfully completed tasks
      - RETRYABLE (101): Failed tasks that will be retried
    
    **Returns:**
    - **tasks**: List of tasks
    - **next_cursor**: Cursor for next page (null if no more pages)
    """
    worker_queue = req.app.state.worker_queue  # type: ignore[attr-defined]
    
    if state:
        # Filter by state
        try:
            # Handle both numeric and string values
            if state.isdigit() or (state.startswith('-') and state[1:].isdigit()):
                task_state = TaskState(int(state))
            else:
                task_state = TaskState[state.upper()]
        except (ValueError, KeyError):
            valid_states = [f"{s.name} ({s.value})" for s in TaskState]
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid state '{state}'. Valid states: {', '.join(valid_states)}"
            )
        
        tasks = await worker_queue.list_tasks_by_state(task_state, limit, cursor)
    else:
        # List all tasks
        tasks = await worker_queue.list_tasks(limit, cursor)

    # Calculate next cursor from the last task
    next_cursor = None
    if tasks and len(tasks) == limit:
        if state:
            next_cursor = tasks[-1].schedule_at
        else:
            next_cursor = tasks[-1].schedule_at

    return TaskListResponse(tasks=tasks, next_cursor=next_cursor)


@router.get(
    "/api/tasks/{task_id}",
    response_model=Task,
    tags=["tasks"],
    summary="Get task details",
    description="Retrieve detailed information about a specific task",
    responses={
        200: {"description": "Task details"},
        404: {"description": "Task not found"},
    },
)
async def get_task(req: Request, task_id: str) -> Task:
    """
    Get detailed information about a specific task.
    
    **Parameters:**
    - **task_id**: Unique identifier of the task
    
    **Returns:**
    Complete task information including state, schedule time, items, and metadata.
    """
    worker_queue = req.app.state.worker_queue  # type: ignore[attr-defined]
    task = await worker_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
    
    return task
