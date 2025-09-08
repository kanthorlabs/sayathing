import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from tts import TextToSpeechRequest, Voice, Voices
from worker import Task, TaskItem, TaskState, WorkerQueue

router = APIRouter()

# Initialize templates
templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_path)


class TaskListResponse(BaseModel):
    tasks: List[Task]
    next_cursor: Optional[int] = None
    has_more: bool = False


class TaskStatesResponse(BaseModel):
    states: List[dict]


class EnqueueTaskRequest(BaseModel):
    items: List[TextToSpeechRequest]


class EnqueueTaskResponse(BaseModel):
    task_ids: List[str]
    message: str


@router.get("/ui/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": "Task Dashboard"}
    )


@router.get("/ui/api/voices", response_model=List[Voice])
async def get_voices():
    """Get all available voices for the enqueue form"""
    try:
        voices = Voices.get_all()
        items = []
        
        for voice_id, voice_data in voices.items():
            item = Voice.from_dict({**voice_data, "id": voice_id})
            items.append(item)
        
        # Sort by language, gender, then name for better UX
        sorted_voices = sorted(items, key=lambda x: (x.language, x.gender, x.name))
        return sorted_voices
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load voices: {str(e)}")


@router.post("/ui/api/enqueue", response_model=EnqueueTaskResponse)
async def enqueue_task(request: Request, body: EnqueueTaskRequest):
    """Enqueue a new task with multiple TTS items"""
    try:
        if not body.items:
            raise HTTPException(status_code=400, detail="At least one item is required")
        
        # Get worker queue from app state
        worker_queue: WorkerQueue = request.app.state.worker_queue
        
        # Create task items
        task_items = [TaskItem(request=item, response_url="") for item in body.items]
        
        # Create task
        task = Task(
            id="",  # Will be assigned by queue
            state=TaskState.PENDING,
            schedule_at=0,  # Will be set by queue
            items=task_items,
            item_count=len(task_items),
            created_at=0,  # Will be set by queue
            updated_at=0,  # Will be set by queue
        )
        
        # Enqueue task
        task_ids = await worker_queue.enqueue([task])
        
        return EnqueueTaskResponse(
            task_ids=task_ids,
            message=f"Successfully enqueued task with {len(body.items)} items"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {str(e)}")
async def get_task_states():
    """Get all available task states with metadata"""
    states = []
    for state in TaskState:
        states.append(state.get_metadata())
    
    return TaskStatesResponse(states=states)


@router.get("/ui/api/tasks", response_model=TaskListResponse)
async def get_tasks(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by task state (e.g., 'pending', 'completed')"),
    limit: int = Query(25, ge=1, le=100, description="Number of tasks to return"),
    cursor: Optional[int] = Query(None, description="Cursor for pagination (schedule_at timestamp)")
):
    """Get tasks with optional state filtering and cursor-based pagination"""
    # Get worker queue from app state
    worker_queue: WorkerQueue = request.app.state.worker_queue
    
    try:
        # If state is provided, filter by state
        if state:
            # Convert state name to TaskState enum
            try:
                task_state = None
                for ts in TaskState:
                    if ts.name.lower() == state.lower():
                        task_state = ts
                        break
                
                if task_state is None:
                    raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
                tasks = await worker_queue.list_tasks_by_state(
                    state=task_state,
                    limit=limit + 1,  # Get one extra to check if there are more
                    cursor=cursor
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to fetch tasks by state: {str(e)}")
        else:
            # Get all tasks
            try:
                tasks = await worker_queue.list_tasks(
                    limit=limit + 1,  # Get one extra to check if there are more
                    cursor=cursor
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to fetch tasks: {str(e)}")
        
        # Check if there are more tasks
        has_more = len(tasks) > limit
        if has_more:
            tasks = tasks[:limit]  # Remove the extra task
        
        # Get next cursor from the last task
        next_cursor = None
        if has_more and tasks:
            if state:
                # For state-filtered queries, use schedule_at
                next_cursor = tasks[-1].schedule_at
            else:
                # For all tasks, use id as cursor - convert to int for consistency
                # Since we're using ULID, we'll use schedule_at instead for simplicity
                next_cursor = tasks[-1].schedule_at
        
        return TaskListResponse(
            tasks=tasks,
            next_cursor=next_cursor,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/ui/api/tasks/{task_id}", response_model=Task)
async def get_task(request: Request, task_id: str):
    """Get detailed information about a specific task including all items"""
    # Get worker queue from app state
    worker_queue: WorkerQueue = request.app.state.worker_queue
    
    try:
        task = await worker_queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch task: {str(e)}")
