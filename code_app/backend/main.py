import uuid
import os
import json
import subprocess
import asyncio
import math
import csv
import re
import shutil
import io
from typing import Any, Dict, List, Optional, Tuple
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
    from code_app.backend.data_ranking.custom_model_ranking import run_custom_ranking, run_custom_ranking_background
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
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")

def _get_agent_file_path(file_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", file_id)
    return os.path.join(AGENT_UPLOADS_DIR, f"{safe_id}.csv")

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    api_key: Optional[str] = None

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
async def create_custom_model_ranking_job(
    background_tasks: BackgroundTasks,
    model_name: str = Form(...),
    scores: str = Form(...)  # JSON string of scores dict
):
    """Create a custom model ranking job and return job_id"""
    try:
        if not CUSTOM_RANKING_AVAILABLE:
            raise HTTPException(status_code=500, detail="Custom ranking function not available")

        # Parse scores from JSON string
        scores_dict = json.loads(scores)

        # Create job directory and save parameters
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(DATA_DIR, 'temp_ranking_jobs', job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Save parameters
        params = {'model_name': model_name, 'scores': scores_dict}
        params_path = os.path.join(job_dir, 'params.json')
        with open(params_path, 'w') as f:
            json.dump(params, f)

        # Set initial status
        status_path = os.path.join(job_dir, 'status.json')
        with open(status_path, 'w') as f:
            json.dump({'status': 'running', 'message': 'Initializing custom model ranking...'}, f)

        # Run the custom ranking function in the background
        background_tasks.add_task(run_custom_ranking_background, job_id, model_name, scores_dict)

        return {"job_id": job_id}

    except Exception as e:
        logger.error(f"Failed to create custom ranking job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create custom ranking job: {str(e)}")


@app.get("/api/ranking/custom/{job_id}/status")
async def get_custom_ranking_job_status(job_id: str):
    """Get the status of a custom model ranking job"""
    job_dir = os.path.join(DATA_DIR, 'temp_ranking_jobs', job_id)
    status_path = os.path.join(job_dir, 'status.json')

    if not os.path.exists(status_path):
        raise HTTPException(status_code=404, detail="Custom ranking job not found")

    with open(status_path, 'r') as f:
        status = json.load(f)

    return status


@app.get("/api/ranking/custom/{job_id}/results")
async def get_custom_ranking_job_results(job_id: str):
    """Get the results of a custom model ranking job"""
    job_dir = os.path.join(DATA_DIR, 'temp_ranking_jobs', job_id)
    status_path = os.path.join(job_dir, 'status.json')
    results_path = os.path.join(job_dir, 'results.json')

    if not os.path.exists(status_path):
        raise HTTPException(status_code=404, detail="Custom ranking job not found")

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

@app.delete("/api/agent/files/{file_id}")
async def delete_agent_file(file_id: str):
    """Delete uploaded agent file"""
    try:
        dest_path = _get_agent_file_path(file_id)
        if not os.path.exists(dest_path):
            raise HTTPException(status_code=404, detail="File not found")

        os.remove(dest_path)
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.post("/api/agent/load-example")
async def load_example_data(request: Dict[str, str]):
    """Load example dataset from predefined file paths"""
    try:
        file_path = request.get("file_path")
        dataset_name = request.get("dataset_name", "Example Dataset")

        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")

        # Validate file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Example file not found: {file_path}")

        # Validate it's a CSV file
        if not file_path.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")

        # Generate unique file ID
        file_id = str(uuid.uuid4())
        dest_path = _get_agent_file_path(file_id)

        # Copy the example file to agent uploads directory
        shutil.copy2(file_path, dest_path)

        # Read file content for validation and preview generation
        with open(dest_path, 'r', encoding='utf-8') as f:
            content_str = f.read()

        # Parse CSV to validate and generate preview
        csv_reader = csv.reader(io.StringIO(content_str))
        rows = list(csv_reader)

        if not rows:
            raise HTTPException(status_code=400, detail="The example file appears to be empty")

        # Get filename from path
        filename = os.path.basename(file_path)

        # Generate preview HTML (similar to existing data preview logic)
        headers = rows[0] if rows else []
        data_rows = rows[1:]  # Show all data rows for scrolling functionality

        # Build compact preview table with file info at top
        table_html = f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; font-size: 0.85rem;">'
        table_html += f'<div style="font-weight: 600; color: #011f5b;"><span class="material-symbols-outlined" style="font-size: 1rem; margin-right: 0.25rem; vertical-align: middle; color: #011f5b;">analytics</span> {filename}</div>'
        table_html += f'<div style="color: #6b7280;">{dataset_name}</div>'
        table_html += f'</div>'

        # Table container with scrolling
        table_html += f'<div style="max-height: 300px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 6px;">'
        table_html += f'<table style="width: 100%; border-collapse: collapse; font-size: 0.8rem;">'

        # Header row
        table_html += f'<thead style="background: #f9fafb; position: sticky; top: 0; z-index: 1;">'
        table_html += f'<tr>'
        for header in headers:
            table_html += f'<th style="padding: 0.5rem; text-align: left; border-bottom: 1px solid #e5e7eb; font-weight: 600; color: #374151;">{header}</th>'
        table_html += f'</tr>'
        table_html += f'</thead>'

        # Data rows
        table_html += f'<tbody>'
        for i, row in enumerate(data_rows[:100]):  # Limit to first 100 rows for preview
            bg_color = '#ffffff' if i % 2 == 0 else '#f9fafb'
            table_html += f'<tr style="background: {bg_color};">'
            for cell in row:
                # Truncate long cell content
                display_cell = str(cell)[:50] + '...' if len(str(cell)) > 50 else str(cell)
                table_html += f'<td style="padding: 0.5rem; border-bottom: 1px solid #f3f4f6; color: #6b7280;">{display_cell}</td>'
            table_html += f'</tr>'
        table_html += f'</tbody>'
        table_html += f'</table>'
        table_html += f'</div>'

        # Add row count info
        total_rows = len(data_rows)
        table_html += f'<div style="margin-top: 0.5rem; font-size: 0.8rem; color: #6b7280;">Showing {min(100, total_rows)} of {total_rows} rows</div>'

        return {
            "file_id": file_id,
            "filename": filename,
            "dataset_name": dataset_name,
            "preview_html": table_html
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load example data: {str(e)}")


# -----------------------------
# Agent: Tool implementations
# -----------------------------
async def tool_inspect_dataset(file_id: str, max_rows: int = 10, api_key: str = None) -> Dict[str, Any]:
    """Enhanced dataset inspection using LLM to identify ranking items from data content"""
    path = _get_agent_file_path(file_id)
    if not os.path.exists(path):
        return {"error": "File not found. Please ensure you've uploaded a CSV file first."}

    try:
        # Read header and first 10 rows for LLM analysis
        header: List[str] = []
        sample_data: List[List[str]] = []

        with open(path, "r", newline="", encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    header = row
                elif i <= max_rows:  # Read first 10 data rows
                    sample_data.append(row)
                else:
                    break

        if not header:
            return {"error": "CSV file appears to be empty or has no header row."}

        # Count total rows (excluding header)
        total_rows = sum(1 for _ in open(path, "r", newline="", encoding='utf-8')) - 1

        # Use OpenAI API to analyze columns and identify ranking items
        analysis_result = await _analyze_columns_with_llm(header, sample_data[:5], api_key)  # Use first 5 rows for analysis

        # Extract ranking columns from LLM analysis
        ranking_columns = analysis_result.get('ranking_columns', [])
        excluded_columns = analysis_result.get('excluded_columns', [])

        # Calculate missing ratios for analysis
        missing_per_col = [0] * len(header)
        numeric_counts = [0] * len(header)

        for row in sample_data:
            for c, val in enumerate(row):
                if c >= len(header):
                    continue
                if val is None or val == "" or val.lower() in ("na", "nan", "null"):
                    missing_per_col[c] += 1
                else:
                    try:
                        float(val)
                        numeric_counts[c] += 1
                    except (ValueError, TypeError):
                        pass

        missing_ratio = {header[i]: (missing_per_col[i] / max(1, len(sample_data))) for i in range(len(header))}

        # Enhanced analysis summary
        column_missing_ratios = [missing_per_col[i] / max(1, len(sample_data)) for i in range(len(header))]
        max_col_missing = max(column_missing_ratios) if column_missing_ratios else 0.0
        avg_col_missing = sum(column_missing_ratios) / len(column_missing_ratios) if column_missing_ratios else 0.0

        if max_col_missing > 0.30:
            dq_level = "poor"
        elif max_col_missing > 0.10 or avg_col_missing > 0.05:
            dq_level = "moderate"
        else:
            dq_level = "great"

        analysis_summary = {
            "data_quality": dq_level,
            "recommended_columns": ranking_columns,
            "excluded_columns": excluded_columns,
            "llm_analysis": analysis_result.get('reasoning', ''),
            "potential_issues": []
        }

        if total_rows > 10000:
            analysis_summary["potential_issues"].append("Large dataset - analysis may take longer")
        if analysis_summary["data_quality"] == "moderate":
            analysis_summary["potential_issues"].append("Some missing values detected - consider data cleaning")
        if analysis_summary["data_quality"] == "poor":
            analysis_summary["potential_issues"].append("High missingness - results may be unreliable")

        return {
            "n_rows": total_rows,
            "n_cols": len(header),
            "columns": header,
            "ranking_columns": ranking_columns,
            "excluded_columns": excluded_columns,
            "missing_ratio_sample": missing_ratio,
            "analysis_summary": analysis_summary,
            "inspection_status": "success"
        }

    except UnicodeDecodeError:
        return {"error": "File encoding issue. Please ensure your CSV file is saved in UTF-8 format."}
    except Exception as e:
        return {"error": f"Inspection failed: {str(e)}. Please check your CSV file format."}


async def _analyze_columns_with_llm(header: List[str], sample_data: List[List[str]], api_key: str = None) -> Dict[str, Any]:
    """Use OpenAI API to analyze CSV columns and identify ranking items"""

    # Build the data sample for LLM
    data_sample = []
    for i, row in enumerate(sample_data):
        if i >= 5:  # Limit to 5 rows for token efficiency
            break
        row_data = {}
        for j, val in enumerate(row):
            if j < len(header):
                row_data[header[j]] = val
        data_sample.append(row_data)

    prompt = f"""You are analyzing a CSV file to identify which columns contain ranking items (metrics that should be compared to rank/score different methods/models).

COLUMNS: {', '.join(header)}

SAMPLE DATA (first {len(data_sample)} rows):
{json.dumps(data_sample, indent=2)}

TASK: Analyze each column and determine if it contains ranking items. Ranking items are ANY numeric values that could be used for comparison and ranking, including:
- Performance metrics (accuracy, F1, AUC, loss, precision, recall, etc.)
- Resource usage metrics (time, memory, CPU usage)
- Count-based metrics (true positives, false negatives, confusion matrix counts, etc.) - THESE ARE ALWAYS RANKING ITEMS
- Statistical measures (means, variances, p-values, etc.)
- ANY numeric column that represents a quantitative measurement or score

ONLY EXCLUDE columns that are clearly NOT quantitative measurements:
- Model/Method names or text identifiers (like 'model', 'method', 'algorithm', 'classifier')
- Metadata or descriptions (like 'description', 'sample_id', 'experiment_id')
- Timestamps and dates (like 'timestamp', 'date')
- Sequential IDs that are just row numbers

IMPORTANT GUIDELINES:
- Be VERY INCLUSIVE: ANY column with numeric data should be considered a ranking item unless it's clearly just an identifier or metadata
- If it's a number that could be compared/ordered, it's a ranking item
- Resource metrics (time, memory), performance metrics, counts, statistics - ALL are ranking items
- Only exclude columns that are clearly text identifiers, timestamps, or descriptions
- When in doubt, INCLUDE as ranking item - users can always manually exclude if needed

Return your analysis in this exact JSON format:
{{
    "ranking_columns": ["list", "of", "ranking", "column", "names"],
    "excluded_columns": ["list", "of", "excluded", "column", "names"],
    "reasoning": "brief explanation of your decisions"
}}"""

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key or OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']

                    # Try to parse JSON response
                    try:
                        parsed = json.loads(content)
                        return parsed
                    except json.JSONDecodeError:
                        # Fallback: extract column names from text
                        ranking_cols = []
                        for col in header:
                            if col.lower() not in ['model', 'method', 'description', 'sample_id', 'case_num', 'id', 'index']:
                                ranking_cols.append(col)
                        return {
                            "ranking_columns": ranking_cols,
                            "excluded_columns": ["model", "description", "sample_id", "case_num"],
                            "reasoning": f"LLM parsing failed, used fallback logic. Content: {content[:200]}..."
                        }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")

    except Exception as e:
        # Fallback to simple logic if OpenAI fails
        ranking_cols = []
        excluded_cols = []
        for col in header:
            if col.lower() in ['model', 'method', 'description', 'sample_id', 'case_num', 'id', 'index', 'case_number']:
                excluded_cols.append(col)
            else:
                ranking_cols.append(col)

        return {
            "ranking_columns": ranking_cols,
            "excluded_columns": excluded_cols,
            "reasoning": f"OpenAI API failed ({str(e)}), used fallback logic"
        }


async def tool_infer_direction(columns: List[str], file_id: str = None, api_key: str = None) -> Dict[str, Any]:
    """Enhanced direction inference using LLM to analyze ranking columns and actual data values"""
    logger.info(f"DEBUG BACKEND: tool_infer_direction called with columns={columns}, file_id={file_id}")
    if not columns:
        return {"direction": "unsure", "confidence": 0.0, "reason": "No columns provided for analysis"}

    # If file_id is provided, use LLM to analyze actual data values
    if file_id:
        try:
            path = _get_agent_file_path(file_id)
            if os.path.exists(path):
                logger.info(f"DEBUG BACKEND: Using LLM for direction inference with file: {path}")
                result = await _infer_direction_with_llm(path, columns, api_key)
                if result:
                    logger.info(f"DEBUG BACKEND: LLM direction inference result: {result}")
                    return result
            else:
                logger.warning(f"DEBUG BACKEND: File not found: {path}")
        except Exception as e:
            logger.warning(f"Failed to use LLM for direction inference: {str(e)}, falling back to keyword matching")

    # Fallback to keyword-based inference with data value analysis
    logger.info("DEBUG BACKEND: Using keyword-based direction inference")
    if file_id:
        try:
            path = _get_agent_file_path(file_id)
            if os.path.exists(path):
                result = await _infer_direction_with_keywords(columns, file_path=path)
            else:
                result = await _infer_direction_with_keywords(columns)
        except Exception as e:
            logger.warning(f"Error in keyword-based inference with data: {str(e)}")
            result = await _infer_direction_with_keywords(columns)
    else:
        result = await _infer_direction_with_keywords(columns)
    
    logger.info(f"DEBUG BACKEND: Keyword-based direction inference result: {result}")
    return result


async def _infer_direction_with_llm(file_path: str, ranking_columns: List[str], api_key: str = None) -> Optional[Dict[str, Any]]:
    """Use LLM to infer optimization direction based on column names and actual data values"""
    try:
        # Read header and sample data
        header: List[str] = []
        sample_data: List[List[str]] = []
        
        with open(file_path, "r", newline="", encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    header = row
                elif i <= 20:  # Read first 20 rows for better analysis
                    sample_data.append(row)
                else:
                    break

        if not header or not sample_data:
            return None

        # Extract data for ranking columns only
        ranking_col_indices = [i for i, col in enumerate(header) if col in ranking_columns]
        if not ranking_col_indices:
            return None

        # Build data sample with only ranking columns
        data_sample = []
        for row in sample_data[:15]:  # Use first 15 rows
            row_data = {}
            for idx in ranking_col_indices:
                if idx < len(row):
                    col_name = header[idx]
                    val = row[idx]
                    # Try to convert to numeric for analysis
                    try:
                        numeric_val = float(val) if val and val.strip() not in ("", "na", "nan", "null") else None
                        row_data[col_name] = numeric_val
                    except (ValueError, TypeError):
                        row_data[col_name] = val
            if row_data:
                data_sample.append(row_data)

        if not data_sample:
            return None

        # Calculate basic statistics for each ranking column
        column_stats = {}
        for col in ranking_columns:
            values = []
            for row in data_sample:
                if col in row and row[col] is not None:
                    try:
                        val = float(row[col])
                        values.append(val)
                    except (ValueError, TypeError):
                        pass
            
            if values:
                column_stats[col] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "count": len(values),
                    "sample_values": sorted(set(values))[:10]  # First 10 unique values
                }

        # Build prompt using string concatenation to avoid f-string formatting issues
        column_stats_json = json.dumps(column_stats, indent=2)
        sample_data_json = json.dumps(data_sample[:15], indent=2)
        
        prompt = """You are analyzing a ranking dataset to determine the optimization direction (whether higher values are better or lower values are better).

DATASET OVERVIEW:
- Ranking columns: """ + ', '.join(ranking_columns) + """
- Total columns: """ + str(len(ranking_columns)) + """

COLUMN STATISTICS SUMMARY:
""" + column_stats_json + """

SAMPLE DATA ROWS (first 15 rows, showing all ranking columns together):
""" + sample_data_json + """

TASK: Analyze the ENTIRE dataset to determine the optimization direction:

1. HIGHER values are better (e.g., accuracy, F1, AUC, R², precision, recall, success rate, score)
2. LOWER values are better (e.g., loss, error, RMSE, MAE, cost, distance, perplexity)

IMPORTANT: Look at the dataset as a WHOLE, not individual columns in isolation. Consider:
- What type of metrics these appear to be (are they all losses, all scores, or mixed?)
- The range and scale of values across all ranking columns
- Whether this looks like a typical machine learning evaluation dataset
- Common patterns: datasets usually have consistent direction (all higher-better OR all lower-better)

For example:
- If all values are small positive numbers (typically 0-1 or 0-10), this suggests loss/error metrics where lower is better
- If all values are percentages or scores, this suggests higher is better
- Mixed directions within a single dataset are very rare and usually indicate data quality issues

Return your analysis in this exact JSON format:
```json
{
    "direction": "higher",
    "confidence": 0.8,
    "reason": "explanation of your decision based on overall dataset analysis",
    "recommendation": "overall recommendation based on dataset characteristics"
}
```

Only set direction to "mixed" if you're absolutely certain the dataset contains fundamentally different types of metrics that should be optimized in opposite directions."""

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key or OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1500
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']

                    # Try to parse JSON response with multiple strategies
                    import re
                    parsed = None

                    # Strategy 1: Extract JSON from markdown code blocks
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group(1))
                        except json.JSONDecodeError as e:
                            logger.warning(f"Strategy 1 JSON parse error: {e}")

                    # Strategy 2: Try to find JSON object directly
                    if not parsed:
                        json_match = re.search(r'\{[^{}]*"direction"[^{}]*\}', content, re.DOTALL)
                        if json_match:
                            try:
                                parsed = json.loads(json_match.group(0))
                            except json.JSONDecodeError as e:
                                logger.warning(f"Strategy 2 JSON parse error: {e}")

                    # Strategy 3: Try to parse the entire content
                    if not parsed:
                        try:
                            parsed = json.loads(content)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Strategy 3 JSON parse error: {e}")

                    # Strategy 4: Try to extract direction from text if JSON parsing fails
                    if not parsed:
                        logger.warning(f"Failed to parse LLM JSON response, attempting text extraction. Content preview: {content[:500]}")
                        # Try to extract direction from text
                        direction_match = re.search(r'"direction"\s*:\s*"?(higher|lower|mixed)"?', content, re.IGNORECASE)
                        confidence_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', content)
                        reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', content)
                        
                        if direction_match:
                            direction = direction_match.group(1).lower()
                            if direction not in ["higher", "lower", "mixed"]:
                                direction = "unsure"
                            
                            confidence = 0.5
                            if confidence_match:
                                try:
                                    confidence = float(confidence_match.group(1))
                                except ValueError:
                                    pass
                            
                            reason = reason_match.group(1) if reason_match else "Extracted from LLM text response"
                            
                            logger.info(f"Extracted direction from text: {direction}, confidence: {confidence}")
                            return {
                                "direction": direction,
                                "confidence": confidence,
                                "reason": reason,
                                "recommendation": "",
                                "method": "llm_analysis_text_extraction"
                            }
                        else:
                            logger.warning("Could not extract direction from LLM text response")
                            return None
                    
                    # If we successfully parsed JSON
                    if parsed:
                        # Validate and format response
                        direction = parsed.get("direction", "unsure")
                        if direction not in ["higher", "lower", "mixed"]:
                            direction = "unsure"
                        
                        # Check if direction is "mixed" - ranking_cli.R cannot handle this
                        if direction == "mixed":
                            # Return error for mixed directions since ranking script cannot handle this
                            return {
                                "error": "Data quality issue: Mixed optimization directions detected",
                                "direction": "mixed",
                                "confidence": float(parsed.get("confidence", 0.5)),
                                "reason": parsed.get("reason", "LLM detected mixed directions") + " The ranking script requires all columns to have the same optimization direction (either all higher-is-better or all lower-is-better). Please preprocess your data to ensure consistent direction.",
                                "recommendation": parsed.get("recommendation", ""),
                                "method": "llm_analysis",
                                "data_quality_warning": True
                            }
                        
                        return {
                            "direction": direction,
                            "confidence": float(parsed.get("confidence", 0.5)),
                            "reason": parsed.get("reason", "LLM analysis completed"),
                            "recommendation": parsed.get("recommendation", ""),
                            "method": "llm_analysis"
                        }
                    
                    return None
                else:
                    logger.warning(f"LLM API returned status {response.status}")
                    return None
    except Exception as e:
        logger.warning(f"Error in LLM direction inference: {str(e)}")
        return None


async def _infer_direction_from_data_values(file_path: str, columns: List[str]) -> Optional[Dict[str, Any]]:
    """Infer direction based on actual data values when column names don't provide clues"""
    try:
        # Read sample data
        header: List[str] = []
        sample_data: List[List[str]] = []
        
        with open(file_path, "r", newline="", encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    header = row
                elif i <= 50:  # Read first 50 rows for analysis
                    sample_data.append(row)
                else:
                    break

        if not header or not sample_data:
            return None

        # Extract data for ranking columns only
        ranking_col_indices = [i for i, col in enumerate(header) if col in columns]
        if not ranking_col_indices:
            return None

        # Collect all numeric values
        all_values = []
        for row in sample_data:
            for idx in ranking_col_indices:
                if idx < len(row):
                    val = row[idx]
                    try:
                        numeric_val = float(val) if val and val.strip() not in ("", "na", "nan", "null") else None
                        if numeric_val is not None:
                            all_values.append(numeric_val)
                    except (ValueError, TypeError):
                        pass

        if len(all_values) < 10:  # Need at least 10 values for meaningful analysis
            return None

        # Calculate statistics
        mean_val = sum(all_values) / len(all_values)
        min_val = min(all_values)
        max_val = max(all_values)
        median_val = sorted(all_values)[len(all_values) // 2]

        # Heuristics for direction inference:
        # 1. If values are typically between 0-1 and mean < 0.5, likely loss/error (lower is better)
        # 2. If values are typically between 0-1 and mean > 0.5, likely score/accuracy (higher is better)
        # 3. If values are typically small (< 1) and mean < 0.5, likely loss (lower is better)
        # 4. If values are typically large (> 1), need more context, but if they're errors/costs, lower is better

        if 0 <= min_val <= 1 and 0 <= max_val <= 1:
            # Values in 0-1 range
            if mean_val < 0.4 and median_val < 0.4:
                # Typical loss/error range (0.15-0.35)
                return {
                    "direction": "lower",
                    "confidence": 0.7,
                    "reason": f"Values are in loss/error range (mean={mean_val:.3f}, range=[{min_val:.3f}, {max_val:.3f}]). Lower values typically indicate better performance for loss metrics.",
                    "method": "data_value_analysis"
                }
            elif mean_val > 0.6 and median_val > 0.6:
                # Typical score/accuracy range (0.6-1.0)
                return {
                    "direction": "higher",
                    "confidence": 0.7,
                    "reason": f"Values are in score/accuracy range (mean={mean_val:.3f}, range=[{min_val:.3f}, {max_val:.3f}]). Higher values typically indicate better performance for score metrics.",
                    "method": "data_value_analysis"
                }
        
        # If values are small positive numbers (< 1) but not clearly in 0-1 range
        if max_val < 1.0 and mean_val < 0.5:
            return {
                "direction": "lower",
                "confidence": 0.6,
                "reason": f"Values are small positive numbers (mean={mean_val:.3f}), suggesting loss/error metrics where lower is better.",
                "method": "data_value_analysis"
            }

        return None
    except Exception as e:
        logger.warning(f"Error in data value analysis: {str(e)}")
        return None


async def _infer_direction_with_keywords(columns: List[str], file_path: str = None) -> Dict[str, Any]:
    """Fallback keyword-based direction inference with optional data value analysis"""
    # Expanded keyword lists for better detection
    higher_keywords = {
        "acc", "accuracy", "auc", "f1", "precision", "recall", "specificity", "sensitivity",
        "r2", "r_squared", "score", "performance", "quality", "efficiency", "success_rate",
        "hit_rate", "tpr", "mcc", "kappa", "balanced_accuracy"
    }
    lower_keywords = {
        "loss", "error", "rmse", "mae", "mse", "nll", "logloss", "perplexity", "wer", "cer",
        "cost", "penalty", "deviation", "distance", "residual", "bias", "variance",
        "fnr", "type_i_error", "type_ii_error"
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
        # If no keyword matches and file_path is provided, analyze data values
        if file_path and os.path.exists(file_path):
            try:
                data_based_result = await _infer_direction_from_data_values(file_path, columns)
                if data_based_result:
                    return data_based_result
            except Exception as e:
                logger.warning(f"Failed to analyze data values for direction inference: {str(e)}")
        
        return {
            "direction": "unsure",
            "confidence": 0.0,
            "reason": "No recognizable performance indicators found in column names",
            "suggestions": "Consider columns that contain accuracy, loss, error, or other performance metrics",
            "method": "keyword_matching"
        }

    higher_confidence = min(0.9, higher_score / max(1, total_matches))
    lower_confidence = min(0.9, lower_score / max(1, total_matches))

    if higher_score > lower_score:
        return {
            "direction": "higher",
            "confidence": higher_confidence,
            "reason": f"Found higher-is-better indicators: {', '.join(set(matched_higher))}",
            "matched_keywords": matched_higher,
            "method": "keyword_matching"
        }
    elif lower_score > higher_score:
        return {
            "direction": "lower",
            "confidence": lower_confidence,
            "reason": f"Found lower-is-better indicators: {', '.join(set(matched_lower))}",
            "matched_keywords": matched_lower,
            "method": "keyword_matching"
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
    """Optimized runtime estimation based on R script analysis and actual benchmarks"""
    try:
        if n_samples <= 0 or k_methods <= 0 or B <= 0:
            return {
                "error": "Invalid parameters",
                "eta_seconds": 0,
                "note": "Please provide positive values for samples, methods, and B parameter"
            }

        # Benchmark: 163 samples, 6 methods, B=2000 takes ~1 second
        # Scale factor based on this reference point
        reference_time = 1.0  # seconds
        reference_samples = 163
        reference_methods = 6
        reference_bootstrap = 2000

        # Calculate scaling factors
        sample_ratio = n_samples / reference_samples
        method_ratio = k_methods / reference_methods
        bootstrap_ratio = B / reference_bootstrap

        # Complexity analysis based on R script:
        # 1. Data preprocessing: O(n_samples * k_methods^2)
        # 2. Matrix operations: O(n_samples * k_methods^3)
        # 3. Bootstrap: O(B * n_samples * k_methods^2)

        # Estimate time using power-law scaling
        preprocessing_factor = sample_ratio * (method_ratio ** 2)
        matrix_factor = sample_ratio * (method_ratio ** 3)
        bootstrap_factor = bootstrap_ratio * sample_ratio * (method_ratio ** 2)

        # Weighted combination based on actual bottlenecks
        est_seconds = reference_time * (
            0.1 * preprocessing_factor +     # 10% preprocessing
            0.2 * matrix_factor +           # 20% matrix operations
            0.7 * bootstrap_factor          # 70% bootstrap (bottleneck)
        )

        # Minimum time bounds
        est_seconds = max(0.5, min(est_seconds, 300))  # 0.5s to 5min

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
            "description": "Infer whether higher or lower values are better from column names and actual data values using LLM analysis. Uses ranking_columns from inspect_dataset result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ranking column names to analyze (should be ranking_columns from inspect_dataset)"
                    },
                    "file_id": {
                        "type": "string",
                        "description": "Optional file ID to read actual data values for more accurate direction inference"
                    }
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

# Phase 1 tool dependencies (for file upload analysis workflow)
TOOL_DEPENDENCIES_PHASE1 = {
    "infer_direction": ["inspect_dataset"],
    "estimate_runtime": ["inspect_dataset"],
    # create_job is not in Phase 1 - user confirms parameters in UI
}


def _check_tool_dependencies_phase1(tool_name: str, message_history: List[Dict]) -> Tuple[bool, str]:
    """Check tool dependencies for Phase 1 workflow"""
    if tool_name not in TOOL_DEPENDENCIES_PHASE1:
        return True, ""
    
    required_tools = TOOL_DEPENDENCIES_PHASE1[tool_name]
    called_tools = set()
    
    for msg in message_history:
        if msg.get("role") == "tool":
            called_tools.add(msg.get("name"))
    
    missing = [tool for tool in required_tools if tool not in called_tools]
    if missing:
        return False, f"Tool {tool_name} requires these tools to be called first: {', '.join(missing)}. Please call inspect_dataset first."
    
    return True, ""


def _classify_error_phase1(error_msg: str) -> str:
    """Classify error type for Phase 1 to determine if retry is appropriate"""
    error_lower = error_msg.lower()
    if "timeout" in error_lower or "timed out" in error_lower:
        return "timeout"  # Retryable
    elif "network" in error_lower or "connection" in error_lower:
        return "network"  # Retryable
    elif "file not found" in error_lower or "404" in error_lower:
        return "not_found"  # Not retryable
    elif "invalid" in error_lower or "validation" in error_lower:
        return "invalid"  # Not retryable
    else:
        return "temporary"  # Retryable


def _validate_tool_result_phase1(tool_name: str, result: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate tool result structure for Phase 1"""
    if tool_name == "inspect_dataset":
        if "error" in result:
            return False, result["error"]
        if "n_rows" not in result or "columns" not in result:
            return False, "inspect_dataset result missing required fields: n_rows, columns"
        if result.get("n_rows", 0) == 0:
            return False, "Dataset appears to be empty"
        return True, ""
    
    elif tool_name == "infer_direction":
        if "error" in result:
            return False, result["error"]
        if "direction" not in result:
            return False, "infer_direction result missing required field: direction"
        return True, ""
    
    elif tool_name == "estimate_runtime":
        if "error" in result:
            return False, result["error"]
        if "eta_seconds" not in result:
            return False, "estimate_runtime result missing required field: eta_seconds"
        return True, ""
    
    return True, ""


def _get_inspect_result_from_history(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract inspect_dataset result from message history"""
    for msg in reversed(messages):  # Search from most recent
        if msg.get("role") == "tool" and msg.get("name") == "inspect_dataset":
            content = msg.get("content", "{}")
            try:
                result = json.loads(content) if isinstance(content, str) else content
                if "error" not in result:
                    return result
            except:
                pass
    return None


def _get_file_id_from_history(messages: List[Dict[str, Any]]) -> Optional[str]:
    """Extract file_id from inspect_dataset tool call arguments or system/user messages"""
    # First, try to get from inspect_dataset tool call arguments
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            tool_calls = msg.get("tool_calls", [])
            for tc in tool_calls:
                func = tc.get("function", {})
                if func.get("name") == "inspect_dataset":
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                        if "file_id" in args:
                            return args["file_id"]
                    except:
                        pass
    
    # Fallback: try to extract from system/user messages
    for msg in reversed(messages):
        if msg.get("role") in ["system", "user"]:
            content = msg.get("content", "")
            import re
            file_id_match = re.search(r'file.*?ID[:\s]+([a-f0-9\-]{36})', content, re.IGNORECASE)
            if file_id_match:
                return file_id_match.group(1)
            # Also try UUID pattern
            uuid_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', content, re.IGNORECASE)
            if uuid_match:
                return uuid_match.group(1)
    
    return None


def _check_phase1_complete(messages: List[Dict[str, Any]]) -> bool:
    """Check if Phase 1 is complete (all three required tools successfully called)"""
    required_tools = {"inspect_dataset", "infer_direction", "estimate_runtime"}
    called_tools = set()
    
    for msg in messages:
        if msg.get("role") == "tool":
            tool_name = msg.get("name")
            if tool_name in required_tools:
                # Check if tool call was successful
                content = msg.get("content", "{}")
                try:
                    result = json.loads(content) if isinstance(content, str) else content
                    if "error" not in result:
                        called_tools.add(tool_name)
                except:
                    pass
    
    return len(called_tools) == len(required_tools)


async def _dispatch_tool_call_with_retry_phase1(
    name: str,
    arguments: Dict[str, Any],
    message_history: List[Dict],
    max_retries: int = 2,
    api_key: str = None
) -> Dict[str, Any]:
    """Phase 1 tool call with dependency check, retry, and result validation"""
    # Check dependencies
    dep_ok, dep_msg = _check_tool_dependencies_phase1(name, message_history)
    if not dep_ok:
        return {"error": dep_msg}
    
    last_error = None
    for attempt in range(max_retries + 1):  # max_retries=2 means 3 total attempts (initial + 2 retries)
        try:
            result = await _dispatch_tool_call(name, arguments, api_key)
            
            # Validate result structure
            if name in ["inspect_dataset", "infer_direction", "estimate_runtime"]:
                valid, error_msg = _validate_tool_result_phase1(name, result)
                if not valid:
                    result = {"error": error_msg}
            
            if result.get("error"):
                error_type = _classify_error_phase1(result["error"])
                # Only retry retryable errors
                if error_type in ["network", "timeout", "temporary"] and attempt < max_retries:
                    wait_time = 1 * (attempt + 1)  # Linear backoff: 1s, 2s
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return result
            
            return result
            
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                await asyncio.sleep(1 * (attempt + 1))
                continue
    
    return {"error": f"Tool execution failed after {max_retries + 1} attempts: {last_error}"}


async def _call_openai(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], api_key: Optional[str] = None) -> Dict[str, Any]:
    # Use provided API key or fall back to environment variable
    effective_api_key = api_key or OPENAI_API_KEY

    if not effective_api_key or effective_api_key.startswith("REPLACE_"):
        return {"error": "OpenAI API key is required. Please provide your API key."}
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }
    headers = {
        "Authorization": f"Bearer {effective_api_key}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=json.dumps(payload), timeout=120) as resp:
            data = await resp.json()
            return data


async def _dispatch_tool_call(name: str, arguments: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
    """Enhanced tool dispatcher with better error handling and logging"""
    try:
        logger.info(f"Executing tool: {name} with args: {arguments}")

        if name == "inspect_dataset":
            file_id = arguments.get("file_id")
            max_rows = arguments.get("max_rows", 200)
            if not file_id:
                return {"error": "file_id is required for dataset inspection"}
            return await tool_inspect_dataset(file_id, max_rows, api_key)

        elif name == "infer_direction":
            columns = arguments.get("columns", [])
            if not columns:
                return {"error": "columns parameter is required for direction inference"}
            # Try to get file_id from arguments or from inspect_dataset result
            file_id = arguments.get("file_id")
            result = await tool_infer_direction(columns, file_id=file_id, api_key=api_key)
            logger.info(f"DEBUG BACKEND: infer_direction tool result: {result}")
            return result

        elif name == "estimate_runtime":
            n_samples = arguments.get("n_samples")
            k_methods = arguments.get("k_methods")
            B = arguments.get("B")
            # Align runtime preview with UI ParameterSetup (B=2000) unless explicitly higher
            try:
                if B is None or int(B) < 2000:
                    B = 2000
            except Exception:
                B = 2000
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

    "\n=== IMPORTANT: API KEY REQUIRED ==="
    "Enter OpenAI api key below 👇"

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
    "- When estimating runtime for preview, ALWAYS use B=2000 (unless user specified otherwise) and set k_methods to the number of recommended_columns (fallback to numeric_candidates length)."
    "- CRITICAL: When processing 'inspect_dataset' results, identify ranking-related columns by excluding metadata columns such as 'sample_id', 'case_num', 'case_number', 'description', 'id', 'index'."
    "- CRITICAL: Ranking-related columns are numeric performance metrics columns (e.g., model_1, model_2, model_3, model_4, model_5, model_6) that represent different methods/models to be ranked."
    "- CRITICAL: After calling inspect_dataset, infer_direction, and estimate_runtime, DO NOT generate ANY text response. The UI will automatically display a Ranking Preview modal where users can configure parameters. Your work is done - remain silent."
    "- CRITICAL: NEVER ask users to specify ranking direction, choose higher/lower, or provide any configuration via text. The UI handles all parameter collection."
    "- CRITICAL: NEVER output phrases like 'please specify', 'please choose', 'next step', 'reply with', 'higher-is-better', 'lower-is-better', or any direction-related prompts."
    "- CRITICAL: The UI renders previews and collects direction/parameters. Your role is ONLY to call the three tools - no text output needed."
    "- CRITICAL: After successfully calling all three tools (inspect_dataset, infer_direction, estimate_runtime), set the 'content' field to an empty string (\"\") or null. Do NOT use the word 'EMPTY' as text - use an actual empty string. Do not generate any summary, explanation, or prompt."
    "- CRITICAL: After each tool call during the initial analysis, if you have more tools to call, make the next tool call with empty content (empty string \"\", not the word 'EMPTY')."
    "- CRITICAL: Once all three tools (inspect_dataset, infer_direction, estimate_runtime) are successfully called, STOP. Set content to empty string (\"\") or null. Do not generate any final response or text content. The UI will handle the rest."

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
    "- Keep textual responses minimal; prefer tool calls."
    "- Do NOT ask for Ranking Direction in text; UI will handle."
    "- Do NOT print configuration previews in text; UI will handle."
)


@app.post("/api/agent/chat", response_model=ChatResponse)
async def agent_chat(payload: ChatRequest):
    try:
        logger.info(f"Received agent chat request with {len(payload.messages)} messages")
        for i, msg in enumerate(payload.messages):
            logger.info(f"Message {i}: {msg.get('role')} - {msg.get('content')[:100]}...")
        # Build conversation
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}] + payload.messages

        # Debug: Log the final messages and tools
        logger.info(f"Final messages count: {len(messages)}")
        logger.info(f"Tools spec count: {len(TOOLS_SPEC)}")
        for i, tool in enumerate(TOOLS_SPEC):
            logger.info(f"Tool {i}: {tool['function']['name']}")

        # Tool-calling loop with Phase 1 optimizations
        loop_guard = 0
        max_iterations = 10  # Increased from 5 to allow more flexibility
        consecutive_no_tool_calls = 0
        max_consecutive_no_tool_calls = 2
        last_assistant: Optional[Dict[str, Any]] = None
        
        while loop_guard < max_iterations:
            # Check if Phase 1 is complete (early termination)
            if _check_phase1_complete(messages):
                logger.info("Phase 1 complete - terminating loop early")
                break
            
            loop_guard += 1
            logger.info(f"Tool-calling loop iteration {loop_guard}")
            
            completion = await _call_openai(messages, TOOLS_SPEC, payload.api_key)
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
                consecutive_no_tool_calls += 1
                # Terminate if no tool calls for consecutive iterations
                if consecutive_no_tool_calls >= max_consecutive_no_tool_calls:
                    logger.info(f"No tool calls for {consecutive_no_tool_calls} consecutive iterations - terminating")
                break
                continue

            # Reset counter when tool calls are present
            consecutive_no_tool_calls = 0

            # Execute tool calls in Phase 1 priority order: inspect_dataset -> infer_direction -> estimate_runtime
            # This ensures correct sequential execution even if LLM calls tools simultaneously
            phase1_tool_priority = {"inspect_dataset": 1, "infer_direction": 2, "estimate_runtime": 3}

            # Sort tool calls by Phase 1 priority
            sorted_tool_calls = sorted(
                [tc for tc in tool_calls if (tc.get("function") or {}).get("name") in phase1_tool_priority],
                key=lambda tc: phase1_tool_priority.get((tc.get("function") or {}).get("name"), 999)
            )

            # Execute tools in priority order, executing all valid ones in sequence within this iteration
            executed_tools = set()
            for tc in sorted_tool_calls:
                func = (tc.get("function") or {})
                name = func.get("name")

                if name in executed_tools:
                    continue

                raw_args = func.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {}

                # Check dependencies before executing
                dep_ok, dep_msg = _check_tool_dependencies_phase1(name, messages)
                if not dep_ok:
                    continue  # Skip this tool - dependencies not satisfied

                # For infer_direction and estimate_runtime, enrich arguments with data from inspect_dataset
                if name == "infer_direction":
                    logger.info(f"DEBUG BACKEND: infer_direction original args: {args}")
                    # Get columns and file_id from previous inspect_dataset result
                    inspect_result = _get_inspect_result_from_history(messages)
                    if inspect_result:
                        logger.info(f"DEBUG BACKEND: infer_direction found inspect_result with keys: {list(inspect_result.keys())}")
                        # ALWAYS override with ranking_columns from LLM analysis if available
                        ranking_cols = inspect_result.get("ranking_columns", [])
                        if ranking_cols:
                            logger.info(f"DEBUG BACKEND: infer_direction OVERRIDING with ranking_columns: {ranking_cols}")
                            args["columns"] = ranking_cols
                        elif "columns" in inspect_result:
                            logger.info(f"DEBUG BACKEND: infer_direction using fallback columns: {inspect_result.get('columns')}")
                            args["columns"] = inspect_result["columns"]
                    else:
                        logger.warning("DEBUG BACKEND: infer_direction could not find inspect_result in messages")
                    # Get file_id from tool call history or messages
                    if not args.get("file_id"):
                        file_id = _get_file_id_from_history(messages)
                        if file_id:
                            logger.info(f"DEBUG BACKEND: infer_direction found file_id: {file_id}")
                            args["file_id"] = file_id
                        else:
                            logger.warning("DEBUG BACKEND: infer_direction could not find file_id in history")
                    logger.info(f"DEBUG BACKEND: infer_direction final args: {args}")

                elif name == "estimate_runtime":
                    # Get data from previous inspect_dataset result
                    inspect_result = _get_inspect_result_from_history(messages)
                    if inspect_result:
                        logger.debug(f"DEBUG BACKEND: estimate_runtime found inspect_result keys: {list(inspect_result.keys())}")
                        if not args.get("n_samples"):
                            args["n_samples"] = inspect_result.get("n_rows", 1000)
                        if not args.get("k_methods"):
                            # Use ranking_columns from LLM analysis, fallback to numeric_candidates
                            ranking_cols = inspect_result.get("ranking_columns", [])
                            logger.debug(f"DEBUG BACKEND: estimate_runtime ranking_cols from inspect_result: {ranking_cols}")
                            if not ranking_cols:
                                ranking_cols = inspect_result.get("numeric_candidates", [])
                                logger.debug(f"DEBUG BACKEND: estimate_runtime using numeric_candidates fallback: {ranking_cols}")
                            args["k_methods"] = len(ranking_cols)
                            logger.debug(f"DEBUG BACKEND: estimate_runtime setting k_methods to: {args['k_methods']}")
                        if not args.get("B"):
                            args["B"] = 2000  # Default for preview
                    else:
                        logger.warning("DEBUG BACKEND: estimate_runtime could not find inspect_result in messages")

                # Use Phase 1 optimized tool call with retry and dependency checking
                result = await _dispatch_tool_call_with_retry_phase1(name, args, messages, api_key=payload.api_key)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "name": name,
                    "content": json.dumps(result)
                })

                executed_tools.add(name)
                # Don't break - execute all valid tools in this iteration

        return ChatResponse(messages=messages, assistant_message=last_assistant)
    except Exception as e:
        logger.error(f"Chat exception: {str(e)}")
        return ChatResponse(messages=[], error=f"chat exception: {str(e)}")


# For testing purposes - simple test endpoint
@app.post("/api/test-chat")
async def test_chat(api_key: str = Form(...)):
    """Simple test endpoint to verify Agent chat functionality"""
    try:
        test_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Hello, please test the agent functionality"}
        ]

        logger.info("Testing agent chat with simple message")
        completion = await _call_openai(test_messages, TOOLS_SPEC, api_key)

        if completion.get("error"):
            return {"error": completion.get("error"), "status": "failed"}

        return {"status": "success", "response": completion.get("choices", [{}])[0].get("message", {})}
    except Exception as e:
        return {"error": str(e), "status": "exception"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)