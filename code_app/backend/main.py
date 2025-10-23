import uuid
import os
import json
import subprocess
import asyncio
import math
import csv
import re
import shutil
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
import aiohttp
import logging

# Ensure the project root is in the Python path
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try to import the custom ranking function at module level
try:
    from code_app.backend.data_ranking.custom_model_ranking import run_custom_ranking
    CUSTOM_RANKING_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import custom ranking function: {e}")
    CUSTOM_RANKING_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory for jobs and uploads (shared disk on Render)
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))
JOBS_DIR = os.path.join(DATA_DIR, 'jobs')
AGENT_UPLOADS_DIR = os.path.join(DATA_DIR, 'agent_uploads')
R_SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../demo_r/ranking_cli.R'))

os.makedirs(JOBS_DIR, exist_ok=True)
os.makedirs(AGENT_UPLOADS_DIR, exist_ok=True)

# OpenAI API configuration from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

def _get_agent_file_path(file_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", file_id)
    return os.path.join(AGENT_UPLOADS_DIR, f"{safe_id}.csv")

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]

class ChatResponse(BaseModel):
    messages: List[Dict[str, Any]]
    assistant_message: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

def run_ranking_script(job_id: str):
    job_dir = os.path.join(JOBS_DIR, job_id)
    input_dir = os.path.join(job_dir, 'input')
    output_dir = os.path.join(job_dir, 'output')
    
    params_path = os.path.join(job_dir, 'params.json')
    status_path = os.path.join(job_dir, 'status.json')
    
    try:
        # Validate Rscript and script availability early for clearer errors on Azure
        if not shutil.which('Rscript'):
            raise FileNotFoundError("Rscript executable not found. Ensure R is installed in the backend environment.")
        if not os.path.exists(R_SCRIPT_PATH):
            raise FileNotFoundError(f"R script not found at {R_SCRIPT_PATH}")
        with open(params_path, 'r') as f:
            params = json.load(f)
        
        input_csv_path = os.path.join(input_dir, 'data.csv')

        cmd = [
            'Rscript',
            R_SCRIPT_PATH,
            '--csv', input_csv_path,
            '--bigbetter', "1" if params['bigbetter'] else "0",
            '--B', str(params['B']),
            '--seed', str(params['seed']),
            '--out', output_dir,
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Using subprocess.run for simplicity in a background task.
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            with open(status_path, 'w') as f:
                json.dump({'status': 'succeeded'}, f)
            logger.info(f"Job {job_id} succeeded.")
        else:
            error_message = result.stderr or result.stdout
            with open(status_path, 'w') as f:
                json.dump({'status': 'failed', 'message': error_message}, f)
            logger.error(f"Job {job_id} failed: {error_message}")

    except Exception as e:
        error_message = str(e)
        with open(status_path, 'w') as f:
            json.dump({'status': 'failed', 'message': error_message}, f)
        logger.error(f"Job {job_id} failed with exception: {error_message}")


@app.post("/api/ranking/jobs")
async def create_ranking_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    bigbetter: bool = Form(...),
    B: int = Form(...),
    seed: int = Form(...),
):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(JOBS_DIR, job_id)
    
    input_dir = os.path.join(job_dir, 'input')
    output_dir = os.path.join(job_dir, 'output')
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Save uploaded file
    input_csv_path = os.path.join(input_dir, 'data.csv')
    with open(input_csv_path, 'wb') as f:
        content = await file.read()
        f.write(content)
        
    # Save parameters
    params = {'bigbetter': bigbetter, 'B': B, 'seed': seed}
    params_path = os.path.join(job_dir, 'params.json')
    with open(params_path, 'w') as f:
        json.dump(params, f)
        
    # Set initial status
    status_path = os.path.join(job_dir, 'status.json')
    with open(status_path, 'w') as f:
        json.dump({'status': 'running'}, f)
        
    # Run R script in the background
    background_tasks.add_task(run_ranking_script, job_id)
    
    return {"job_id": job_id}


@app.get("/api/ranking/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    job_dir = os.path.join(JOBS_DIR, job_id)
    status_path = os.path.join(job_dir, 'status.json')
    
    if not os.path.exists(status_path):
        raise HTTPException(status_code=404, detail="Job not found")
        
    with open(status_path, 'r') as f:
        status = json.load(f)
        
    return status


@app.get("/api/ranking/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    job_dir = os.path.join(JOBS_DIR, job_id)
    status_path = os.path.join(job_dir, 'status.json')
    results_path = os.path.join(job_dir, 'output', 'ranking_results.json')
    
    if not os.path.exists(status_path):
        raise HTTPException(status_code=404, detail="Job not found")
        
    with open(status_path, 'r') as f:
        status = json.load(f)

    if status['status'] == 'running':
        return JSONResponse(status_code=202, content={"status": "running", "message": "Job is still processing."})
    
    if status['status'] == 'failed':
        return JSONResponse(status_code=500, content=status)
        
    if status['status'] == 'succeeded':
        if not os.path.exists(results_path):
            raise HTTPException(status_code=404, detail="Results file not found, though job succeeded.")
        
        with open(results_path, 'r') as f:
            results = json.load(f)
        return results
    
    raise HTTPException(status_code=500, detail=f"Unknown job status: {status.get('status')}")


@app.post("/api/ranking/custom")
async def custom_model_ranking(
    model_name: str = Form(...),
    scores: str = Form(...)  # JSON string of scores dict
):
    """Handle custom model ranking requests from frontend"""
    try:
        if not CUSTOM_RANKING_AVAILABLE:
            raise HTTPException(status_code=500, detail="Custom ranking function not available")

        # Parse scores from JSON string
        scores_dict = json.loads(scores)

        # Run the custom ranking function (already imported at module level)
        result = await run_custom_ranking(model_name, scores_dict)

        return result
    except Exception as e:
        logger.error(f"Custom ranking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Custom ranking failed: {str(e)}")


@app.get("/api/health")
def health():
    return {"status": "ok"} 


# -----------------------------
# Agent: Upload endpoint
# -----------------------------
@app.post("/api/agent/upload")
async def agent_upload(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        dest_path = _get_agent_file_path(file_id)
        content = await file.read()
        with open(dest_path, "wb") as f:
            f.write(content)
        return {"file_id": file_id, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/agent/files/{file_id}")
async def get_agent_file(file_id: str):
    """Get uploaded agent file content"""
    try:
        dest_path = _get_agent_file_path(file_id)
        if not os.path.exists(dest_path):
            raise HTTPException(status_code=404, detail="File not found")

        with open(dest_path, "rb") as f:
            content = f.read()
        return Response(content=content, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


# -----------------------------
# Agent: Tool implementations
# -----------------------------
async def tool_inspect_dataset(file_id: str, max_rows: int = 200) -> Dict[str, Any]:
    """Enhanced dataset inspection with better error handling and user-friendly feedback"""
    path = _get_agent_file_path(file_id)
    if not os.path.exists(path):
        return {"error": "File not found. Please ensure you've uploaded a CSV file first."}

    num_rows = 0
    header: List[str] = []
    missing_per_col: List[int] = []
    numeric_counts: List[int] = []
    sample_rows_checked = 0

    try:
        with open(path, "r", newline="", encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    header = row
                    missing_per_col = [0] * len(header)
                    numeric_counts = [0] * len(header)
                    continue
                num_rows += 1
                # Count missing and numeric in a sampled fashion for efficiency
                if sample_rows_checked < max_rows:
                    for c, val in enumerate(row):
                        if val is None or val == "" or val.lower() in ("na", "nan", "null"):
                            missing_per_col[c] += 1
                        else:
                            try:
                                float(val)
                                numeric_counts[c] += 1
                            except (ValueError, TypeError):
                                pass
                    sample_rows_checked += 1

        if not header:
            return {"error": "CSV file appears to be empty or has no header row."}

        n_cols = len(header)
        numeric_candidates = [header[i] for i in range(n_cols)
                            if sample_rows_checked > 0 and numeric_counts[i] / sample_rows_checked >= 0.7]
        missing_ratio = {header[i]: (missing_per_col[i] / max(1, sample_rows_checked)) for i in range(n_cols)}

        # Enhanced analysis summary
        analysis_summary = {
            "data_quality": "good" if sum(missing_per_col) / (sample_rows_checked * n_cols) < 0.1 else "moderate",
            "recommended_columns": numeric_candidates[:5],  # Top 5 candidates
            "potential_issues": []
        }

        if num_rows > 10000:
            analysis_summary["potential_issues"].append("Large dataset - analysis may take longer")
        if analysis_summary["data_quality"] == "moderate":
            analysis_summary["potential_issues"].append("Some missing values detected - consider data cleaning")

        return {
            "n_rows": num_rows,
            "n_cols": len(header),
            "columns": header,
            "numeric_candidates": numeric_candidates,
            "missing_ratio_sample": missing_ratio,
            "analysis_summary": analysis_summary,
            "inspection_status": "success"
        }
    except UnicodeDecodeError:
        return {"error": "File encoding issue. Please ensure your CSV file is saved in UTF-8 format."}
    except Exception as e:
        return {"error": f"Inspection failed: {str(e)}. Please check your CSV file format."}


async def tool_infer_direction(columns: List[str]) -> Dict[str, Any]:
    """Enhanced direction inference with better keyword matching and confidence scoring"""
    if not columns:
        return {"direction": "unsure", "confidence": 0.0, "reason": "No columns provided for analysis"}

    # Expanded keyword lists for better detection
    higher_keywords = {
        "acc", "accuracy", "auc", "f1", "precision", "recall", "specificity", "sensitivity",
        "r2", "r_squared", "score", "performance", "quality", "efficiency", "success_rate",
        "hit_rate", "tpr", "fpr", "mcc", "kappa", "balanced_accuracy"
    }
    lower_keywords = {
        "loss", "error", "rmse", "mae", "mse", "nll", "logloss", "perplexity", "wer", "cer",
        "cost", "penalty", "deviation", "distance", "residual", "bias", "variance",
        "fpr", "fnr", "type_i_error", "type_ii_error"
    }

    higher_score = 0
    lower_score = 0
    matched_higher = []
    matched_lower = []

    for col in columns:
        col_lower = (col or "").lower()
        # Check for exact matches first
        for keyword in higher_keywords:
            if keyword in col_lower:
                higher_score += 2
                matched_higher.append(keyword)
        for keyword in lower_keywords:
            if keyword in col_lower:
                lower_score += 2
                matched_lower.append(keyword)

    # Normalize scores to confidence (0-1 scale)
    total_matches = len(matched_higher) + len(matched_lower)
    if total_matches == 0:
        return {
            "direction": "unsure",
            "confidence": 0.0,
            "reason": "No recognizable performance indicators found in column names",
            "suggestions": "Consider columns that contain accuracy, loss, error, or other performance metrics"
        }

    higher_confidence = min(0.9, higher_score / max(1, total_matches))
    lower_confidence = min(0.9, lower_score / max(1, total_matches))

    if higher_score > lower_score:
        return {
            "direction": "higher",
            "confidence": higher_confidence,
            "reason": f"Found higher-is-better indicators: {', '.join(set(matched_higher))}",
            "matched_keywords": matched_higher
        }
    elif lower_score > higher_score:
        return {
            "direction": "lower",
            "confidence": lower_confidence,
            "reason": f"Found lower-is-better indicators: {', '.join(set(matched_lower))}",
            "matched_keywords": matched_lower
        }
    else:
        return {
            "direction": "unsure",
            "confidence": 0.3,
            "reason": "Conflicting indicators found",
            "matched_keywords": {"higher": matched_higher, "lower": matched_lower},
            "suggestions": "Please manually specify the ranking direction based on your domain knowledge"
        }


async def tool_estimate_runtime(n_samples: int, k_methods: int, B: int) -> Dict[str, Any]:
    """Enhanced runtime estimation with better accuracy and user-friendly formatting"""
    try:
        if n_samples <= 0 or k_methods <= 0 or B <= 0:
            return {
                "error": "Invalid parameters",
                "eta_seconds": 0,
                "note": "Please provide positive values for samples, methods, and B parameter"
            }

        # More sophisticated estimation model
        # Base computation includes data loading and preprocessing
        base_time = 2.0

        # Core computation scales with samples, methods, and B iterations
        # Using logarithmic scaling for B as it's typically used in bootstrap iterations
        compute_factor = float(n_samples) * float(k_methods) * math.log2(max(2, B))

        # Additional overhead for larger datasets
        overhead_factor = 1.0 + (n_samples / 100000) * 0.1

        est_seconds = (base_time + 0.0008 * compute_factor) * overhead_factor

        # Convert to appropriate time units
        if est_seconds < 60:
            time_str = f"{int(est_seconds)} seconds"
        elif est_seconds < 3600:
            minutes = int(est_seconds // 60)
            seconds = int(est_seconds % 60)
            time_str = f"{minutes}m {seconds}s"
        else:
            hours = int(est_seconds // 3600)
            minutes = int((est_seconds % 3600) // 60)
            time_str = f"{hours}h {minutes}m"

        return {
            "eta_seconds": int(est_seconds),
            "eta_formatted": time_str,
            "note": "Estimated time based on data size and parameters",
            "factors": {
                "dataset_size": n_samples,
                "num_methods": k_methods,
                "bootstrap_iterations": B
            }
        }
    except Exception as e:
        return {
            "error": f"Estimation failed: {str(e)}",
            "eta_seconds": 30,
            "note": "Using conservative fallback estimate due to calculation error"
        }


async def tool_create_job(file_id: str, bigbetter: bool, B: int, seed: int) -> Dict[str, Any]:
    """Enhanced job creation with better validation and error handling"""
    path = _get_agent_file_path(file_id)
    if not os.path.exists(path):
        return {"error": "File not found. Please upload a CSV file first."}

    # Validate parameters
    if B <= 0:
        return {"error": "Bootstrap iterations (B) must be a positive integer"}
    if not isinstance(seed, int) or seed < 0:
        return {"error": "Seed must be a non-negative integer"}

    # Check file size (prevent extremely large uploads)
    file_size = os.path.getsize(path)
    if file_size > 100 * 1024 * 1024:  # 100MB limit
        return {"error": "File is too large (>100MB). Please use a smaller dataset."}

    url = "http://127.0.0.1:8001/api/ranking/jobs"
    form = aiohttp.FormData()

    try:
        with open(path, "rb") as f:
            form.add_field('file', f, filename='data.csv', content_type='text/csv')
            form.add_field('bigbetter', 'true' if bigbetter else 'false')
            form.add_field('B', str(B))
            form.add_field('seed', str(seed))

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=form, timeout=60) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        job_id = data.get("job_id")
                        if job_id:
                            return {
                                "job_id": job_id,
                                "status": "created",
                                "message": "Analysis job created successfully",
                                "parameters": {
                                    "direction": "higher" if bigbetter else "lower",
                                    "bootstrap_iterations": B,
                                    "random_seed": seed
                                }
                            }
                        else:
                            return {"error": "Job creation failed - no job ID returned"}
                    else:
                        error_text = await resp.text()
                        return {"error": f"Job creation failed: HTTP {resp.status} - {error_text}"}
    except asyncio.TimeoutError:
        return {"error": "Job creation timed out. The server may be busy. Please try again."}
    except Exception as e:
        return {"error": f"Job creation failed: {str(e)}. Please check your connection and try again."}


async def tool_poll_status(job_id: str) -> Dict[str, Any]:
    """Enhanced status polling with better error handling and user feedback"""
    if not job_id or not isinstance(job_id, str):
        return {"error": "Invalid job ID provided"}

    url = f"http://127.0.0.1:8001/api/ranking/jobs/{job_id}/status"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    status_data = await resp.json()
                    status = status_data.get('status', 'unknown')

                    # Add user-friendly status messages
                    status_messages = {
                        'running': 'Analysis is currently running...',
                        'succeeded': 'Analysis completed successfully!',
                        'failed': f'Analysis failed: {status_data.get("message", "Unknown error")}'
                    }

                    user_message = status_messages.get(status, f'Unknown status: {status}')

                    return {
                        "job_id": job_id,
                        "status": status,
                        "status_message": user_message,
                        "raw_status": status_data
                    }
                elif resp.status == 404:
                    return {"error": "Job not found. The job may have expired or been deleted."}
                else:
                    return {"error": f"Status check failed: HTTP {resp.status}"}
    except asyncio.TimeoutError:
        return {"error": "Status check timed out. The server may be busy."}
    except Exception as e:
        return {"error": f"Status check failed: {str(e)}. Please try again."}


async def tool_get_results(job_id: str) -> Dict[str, Any]:
    """Enhanced results retrieval with better error handling and user feedback"""
    if not job_id or not isinstance(job_id, str):
        return {"error": "Invalid job ID provided"}

    url = f"http://127.0.0.1:8001/api/ranking/jobs/{job_id}/results"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    return {
                        "job_id": job_id,
                        "status": "completed",
                        "results": results,
                        "message": "Analysis results retrieved successfully"
                    }
                elif resp.status == 202:
                    return {
                        "job_id": job_id,
                        "status": "running",
                        "message": "Analysis is still in progress. Please check back later."
                    }
                elif resp.status == 404:
                    return {
                        "error": "Results not found. The job may not exist or results may have been deleted."
                    }
                else:
                    error_text = await resp.text()
                    return {
                        "error": f"Results retrieval failed: HTTP {resp.status}",
                        "details": error_text
                    }
    except asyncio.TimeoutError:
        return {
            "error": "Results retrieval timed out. The server may be busy processing your request."
        }
    except Exception as e:
        return {
            "error": f"Results retrieval failed: {str(e)}. Please check your connection and try again."
        }


TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "inspect_dataset",
            "description": "Inspect uploaded CSV file by file_id and return statistics and candidate columns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "max_rows": {"type": "integer", "minimum": 10, "default": 200}
                },
                "required": ["file_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "infer_direction",
            "description": "Infer whether higher or lower values are better from column names heuristics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["columns"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_runtime",
            "description": "Estimate runtime in seconds given n_samples, k_methods and B.",
            "parameters": {
                "type": "object",
                "properties": {
                    "n_samples": {"type": "integer"},
                    "k_methods": {"type": "integer"},
                    "B": {"type": "integer"}
                },
                "required": ["n_samples", "k_methods", "B"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_job",
            "description": "Create a ranking job from an uploaded file_id and parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "bigbetter": {"type": "boolean"},
                    "B": {"type": "integer"},
                    "seed": {"type": "integer"}
                },
                "required": ["file_id", "bigbetter", "B", "seed"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "poll_status",
            "description": "Poll job status by job_id.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_results",
            "description": "Get job results by job_id.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"]
            }
        }
    }
]


async def _call_openai(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("REPLACE_"):
        return {"error": "OPENAI_API_KEY is not set in backend."}
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=json.dumps(payload), timeout=120) as resp:
            data = await resp.json()
            return data


async def _dispatch_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced tool dispatcher with better error handling and logging"""
    try:
        logger.info(f"Executing tool: {name} with args: {arguments}")

        if name == "inspect_dataset":
            file_id = arguments.get("file_id")
            max_rows = arguments.get("max_rows", 200)
            if not file_id:
                return {"error": "file_id is required for dataset inspection"}
            return await tool_inspect_dataset(file_id, max_rows)

        elif name == "infer_direction":
            columns = arguments.get("columns", [])
            if not columns:
                return {"error": "columns parameter is required for direction inference"}
            return await tool_infer_direction(columns)

        elif name == "estimate_runtime":
            n_samples = arguments.get("n_samples")
            k_methods = arguments.get("k_methods")
            B = arguments.get("B")
            if not all([n_samples, k_methods, B]):
                return {"error": "n_samples, k_methods, and B are all required for runtime estimation"}
            return await tool_estimate_runtime(int(n_samples), int(k_methods), int(B))

        elif name == "create_job":
            file_id = arguments.get("file_id")
            bigbetter = arguments.get("bigbetter")
            B = arguments.get("B")
            seed = arguments.get("seed")
            if not all([file_id, bigbetter is not None, B, seed]):
                return {"error": "file_id, bigbetter, B, and seed are all required for job creation"}
            return await tool_create_job(file_id, bool(bigbetter), int(B), int(seed))

        elif name == "poll_status":
            job_id = arguments.get("job_id")
            if not job_id:
                return {"error": "job_id is required for status polling"}
            return await tool_poll_status(job_id)

        elif name == "get_results":
            job_id = arguments.get("job_id")
            if not job_id:
                return {"error": "job_id is required for results retrieval"}
            return await tool_get_results(job_id)

        else:
            logger.warning(f"Unknown tool called: {name}")
            return {"error": f"Unknown tool: {name}. Available tools: inspect_dataset, infer_direction, estimate_runtime, create_job, poll_status, get_results"}

    except Exception as e:
        logger.error(f"Tool execution error for {name}: {str(e)}")
        return {"error": f"Tool execution failed: {str(e)}. Please check your input parameters and try again."}


SYSTEM_PROMPT = (
    "You are an intelligent ranking analysis assistant for Robust Spectral Ranking. Your goal is to guide users through the complete analysis workflow in a structured, professional manner while maintaining low autonomy and strict adherence to ranking-related topics."

    "\n=== CORE MISSION ==="
    "Help users complete spectral ranking analysis by:"
    "1. Data Upload & Validation (CONCISE feedback)"
    "2. Data Inspection & Understanding (BRIEF summary)"
    "3. Parameter Configuration (ESSENTIAL questions only)"
    "4. Analysis Execution (PROGRESS updates)"
    "5. Results Presentation (CLEAR findings)"

    "\n=== GUIDING PRINCIPLES ==="
    "- Stay focused on ranking analysis - politely redirect off-topic conversations"
    "- Provide CONCISE, clear guidance - avoid overwhelming details"
    "- Ask only ESSENTIAL clarifying questions"
    "- Offer intelligent defaults based on data characteristics"
    "- Explain technical concepts in SIMPLE terms"
    "- Always confirm important decisions before proceeding"

    "\n=== CONVERSATION STRATEGY ==="
    "- Use the current conversation context to maintain continuity"
    "- Remember user's previous choices (direction, parameters)"
    "- Track progress through workflow stages"
    "- Provide encouraging, professional feedback"
    "- Handle errors gracefully with clear explanations"
    "- Suggest next steps proactively but wait for user confirmation"

    "\n=== INTELLIGENT WORKFLOW AUTOMATION ==="
    "When a user uploads a file:"
    "- Use 'inspect_dataset' to analyze data structure"
    "- Use 'infer_direction' to determine ranking direction"
    "- Use 'estimate_runtime' to provide time estimates"
    "- Provide ULTRA-CONCISE summary"
    "- Ask ONLY for Ranking Direction choice:"
    "  • Reply 'higher' for higher-is-better"
    "  • Reply 'lower' for lower-is-better"
    "- After user selects Direction, show config preview:"
    "  • Ranking Direction: [selected choice]"
    "  • Bootstrap Samples (B): 100"
    "  • Reproducibility Seed: 42"
    "- After user confirms, use 'create_job' to start analysis"

    "\n=== WORKFLOW STAGES ==="
    "Stage 1: Awaiting file upload or analyzing uploaded data"
    "Stage 2: Data inspection and direction selection"
    "Stage 3: Configuration preview and confirmation"
    "Stage 4: Executing analysis and monitoring progress"
    "Stage 5: Presenting results and offering insights"

    "\n=== SAFETY & QUALITY ==="
    "- Only use provided tools - never fabricate information"
    "- Validate all tool inputs and handle errors appropriately"
    "- Respect user preferences while ensuring analysis quality"
    "- ULTRA-CONCISE responses with structured format"
    "- Ask ONLY essential questions (Direction choice, then confirmation)"
    "- Show configuration preview before execution"
)


@app.post("/api/agent/chat", response_model=ChatResponse)
async def agent_chat(payload: ChatRequest):
    try:
        logger.info(f"Received agent chat request with {len(payload.messages)} messages")
        for i, msg in enumerate(payload.messages):
            logger.info(f"Message {i}: {msg.get('role')} - {msg.get('content')[:100]}...")
        # Build conversation
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}] + payload.messages

        # Tool-calling loop
        loop_guard = 0
        last_assistant: Optional[Dict[str, Any]] = None
        while loop_guard < 5:
            loop_guard += 1
            logger.info(f"Tool-calling loop iteration {loop_guard}")
            completion = await _call_openai(messages, TOOLS_SPEC)
            if completion.get("error"):
                return ChatResponse(messages=messages, error=str(completion.get("error")))
            if "error" in completion:
                return ChatResponse(messages=messages, error=str(completion["error"]))
            choice = (completion.get("choices") or [{}])[0]
            assistant_msg = choice.get("message") or {}
            last_assistant = assistant_msg
            messages.append({"role": "assistant", **assistant_msg})

            tool_calls = assistant_msg.get("tool_calls") or []
            if not tool_calls:
                break

            # Execute tool calls sequentially and append tool results
            for tc in tool_calls:
                func = (tc.get("function") or {})
                name = func.get("name")
                raw_args = func.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {}
                result = await _dispatch_tool_call(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "name": name,
                    "content": json.dumps(result)
                })

        return ChatResponse(messages=messages, assistant_message=last_assistant)
    except Exception as e:
        logger.error(f"Chat exception: {str(e)}")
        return ChatResponse(messages=[], error=f"chat exception: {str(e)}")


# For testing purposes - simple test endpoint
@app.post("/api/test-chat")
async def test_chat():
    """Simple test endpoint to verify Agent chat functionality"""
    try:
        test_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Hello, please test the agent functionality"}
        ]

        logger.info("Testing agent chat with simple message")
        completion = await _call_openai(test_messages, TOOLS_SPEC)

        if completion.get("error"):
            return {"error": completion.get("error"), "status": "failed"}

        return {"status": "success", "response": completion.get("choices", [{}])[0].get("message", {})}
    except Exception as e:
        return {"error": str(e), "status": "exception"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)