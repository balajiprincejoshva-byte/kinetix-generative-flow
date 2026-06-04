import uuid
import time
import asyncio
from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Request, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
import numpy as np
from sklearn.decomposition import PCA
import backend.config as config
from backend.parser.pdb_parser import parse_pdb
from backend.model.inference import sample_ensemble
from backend.model.inference import load_or_init_model, sample_ensemble
from backend.pocket.cryptic_hunter import hunt_cryptic_pockets
from backend.model.allostery import compute_dccm, get_allosteric_webs
from backend.api.schemas import (
    UploadPDBResponse, ConformationFrame, ConformationChunk, 
    PocketInfo, AnalysisResult
)
from pydantic import BaseModel
from backend.model.docking import generate_docked_conformer, score_clashes, optimize_docked_conformer
from backend.model.genesis import run_genesis_loop

class DockRequest(BaseModel):
    smiles: str
    pocket_id: int
    frame_id: int

class DreamRequest(BaseModel):
    pocket_id: int
    frame_idx: int

router = APIRouter()

# In-memory storage for jobs
# job_id -> {"status": str, "protein_graph": ProteinGraph, "frames": List[dict], "pocket_results": AnalysisResult}
JOBS = {}

@router.get("/health")
async def health(request: Request):
    model = getattr(request.app.state, "model", None)
    return {
        "status": "ok", 
        "model_loaded": model is not None, 
        "torch_device": "cpu"
    }

@router.post("/upload_pdb", response_model=UploadPDBResponse)
async def upload_pdb(file: UploadFile = File(...)):
    try:
        content = await file.read()
        protein_graph = parse_pdb(content)
        
        job_id = str(uuid.uuid4())
        JOBS[job_id] = {
            "status": "pending",
            "protein_graph": protein_graph,
            "frames": [],
            "pocket_results": None,
            "dccm": None
        }
        
        return UploadPDBResponse(
            job_id=job_id,
            n_residues=protein_graph.n_residues,
            sequence=protein_graph.sequence,
            message="PDB uploaded and parsed successfully."
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid PDB: {str(e)}")

@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": JOBS[job_id]["status"]}

@router.websocket("/ws/{job_id}/stream_ensemble")
async def stream_ensemble(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    if job_id not in JOBS:
        await websocket.close(code=1008, reason="Job not found")
        return
        
    app = websocket.app
    model = app.state.model
    job = JOBS[job_id]
    
    if job["status"] == "running":
        await websocket.close(code=1008, reason="Job already running")
        return
        
    job["status"] = "running"
    
    generator = sample_ensemble(
        model=model,
        protein_graph=job["protein_graph"],
        n_samples=config.N_CONFORMATIONS,
        chunk_size=config.STREAM_CHUNK_SIZE
    )
    
    total_generated = 0
    try:
        # Generate chunks in threadpool to avoid blocking event loop
        # Wait, generator might not work well with run_in_threadpool if it yields
        # We can run next(generator) in threadpool
        while True:
            chunk_data = await run_in_threadpool(next, generator, None)
            if chunk_data is None:
                break
                
            job["frames"].extend(chunk_data)
            total_generated += len(chunk_data)
            is_final = total_generated >= config.N_CONFORMATIONS
            
            chunk_response = ConformationChunk(
                frames=[ConformationFrame(**f) for f in chunk_data],
                total_generated=total_generated,
                is_final=is_final
            )
            
            await websocket.send_text(chunk_response.model_dump_json())
            
            if is_final:
                break
            
        job["status"] = "complete"
    except WebSocketDisconnect:
        print(f"Client disconnected from {job_id}")
        job["status"] = "error"
    except Exception as e:
        print(f"Error generating ensemble: {e}")
        job["status"] = "error"
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

@router.post("/jobs/{job_id}/analyze_pockets", response_model=AnalysisResult)
async def analyze_pockets(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = JOBS[job_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Ensemble generation not complete")
        
    if job["pocket_results"]:
        return job["pocket_results"]
        
    start_time = time.time()
    
    # Run heavy computation in threadpool
    try:
        # Create sequence list for residue names
        seq_list = list(job["protein_graph"].sequence) # e.g. ['M', 'Q', 'I', 'F', ...]
        
        cryptic_pockets_raw = await run_in_threadpool(
            hunt_cryptic_pockets,
            job["frames"],
            seq_list
        )
        
        cryptic = []
        constitutive = []
        rare = []
        
        for cp in cryptic_pockets_raw:
            info = PocketInfo(
                pocket_id=cp.cluster_id,
                classification=cp.classification,
                opening_probability=cp.opening_probability,
                peak_druggability=cp.peak_druggability,
                centroid=cp.centroid.tolist(),
                representative_frame=cp.representative_frame,
                lining_residues=cp.lining_residues,
                presence_vector=cp.presence_vector.tolist()
            )
            
            if cp.classification == "cryptic":
                cryptic.append(info)
            elif cp.classification == "constitutive":
                constitutive.append(info)
            else:
                rare.append(info)
                
        analysis_time = time.time() - start_time
        
        # Calculate Latent Landscape using PCA
        latent_landscape = None
        try:
            n_frames = len(job["frames"])
            if n_frames > 2:
                # Shape: (n_frames, N, 3)
                ca_matrix = np.array([f["ca_coords"] for f in job["frames"]]) 
                # Shape: (n_frames, N*3)
                ca_matrix_flat = ca_matrix.reshape(n_frames, -1)
                
                pca = PCA(n_components=2)
                pc_coords = pca.fit_transform(ca_matrix_flat)
                
                latent_landscape = []
                for i in range(n_frames):
                    latent_landscape.append({
                        "frame": i,
                        "pc1": float(pc_coords[i, 0]),
                        "pc2": float(pc_coords[i, 1]),
                        "rmsd": float(job["frames"][i].get("rmsd_from_input", 0.0))
                    })
        except Exception as e:
            print(f"PCA landscape computation failed: {e}")
            
        result = AnalysisResult(
            job_id=job_id,
            n_frames_analyzed=len(job["frames"]),
            cryptic_pockets=cryptic,
            constitutive_pockets=constitutive,
            rare_pockets=rare,
            analysis_time_seconds=analysis_time,
            latent_landscape=latent_landscape
        )
        
        job["pocket_results"] = result
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/jobs/{job_id}/frame/{frame_id}", response_model=ConformationFrame)
async def get_frame(job_id: str, frame_id: int):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    frames = JOBS[job_id]["frames"]
    if frame_id < 0 or frame_id >= len(frames):
        raise HTTPException(status_code=404, detail="Frame not found")
        
    return ConformationFrame(**frames[frame_id])

@router.get("/jobs/{job_id}/allostery/{pocket_id}")
async def get_pocket_allostery(job_id: str, pocket_id: int):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = JOBS[job_id]
    if job["status"] != "complete" or not job["pocket_results"]:
        raise HTTPException(status_code=400, detail="Analysis not complete")
        
    # Find pocket
    pocket = None
    all_pockets = (job["pocket_results"].cryptic_pockets + 
                   job["pocket_results"].constitutive_pockets + 
                   job["pocket_results"].rare_pockets)
                   
    for p in all_pockets:
        if p.pocket_id == pocket_id:
            pocket = p
            break
            
    if not pocket:
        raise HTTPException(status_code=404, detail="Pocket not found")
        
    # Compute DCCM if needed
    if job["dccm"] is None:
        try:
            ca_matrix = np.array([f["ca_coords"] for f in job["frames"]])
            job["dccm"] = await run_in_threadpool(compute_dccm, ca_matrix)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to compute DCCM: {e}")
            
    # Get webs
    n_residues = job["protein_graph"].n_residues
    webs = get_allosteric_webs(job["dccm"], pocket.lining_residues, n_residues, threshold=0.45)
    
    return {"webs": webs}

@router.post("/jobs/{job_id}/dock")
async def dock_smiles(job_id: str, req: DockRequest):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = JOBS[job_id]
    if job["status"] != "complete" or not job["pocket_results"]:
        raise HTTPException(status_code=400, detail="Analysis not complete")
        
    if req.frame_id < 0 or req.frame_id >= len(job["frames"]):
        raise HTTPException(status_code=400, detail="Invalid frame_id")
        
    # Find pocket
    pocket = None
    all_pockets = (job["pocket_results"].cryptic_pockets + 
                   job["pocket_results"].constitutive_pockets + 
                   job["pocket_results"].rare_pockets)
    for p in all_pockets:
        if p.pocket_id == req.pocket_id:
            pocket = p
            break
            
    if not pocket:
        raise HTTPException(status_code=404, detail="Pocket not found")
        
    try:
        docked = await run_in_threadpool(generate_docked_conformer, req.smiles, pocket.centroid)
        
        frame = job["frames"][req.frame_id]
        ca_coords = np.array(frame["ca_coords"])
        
        clashes = score_clashes(docked["atoms"], ca_coords)
        
        return {
            "ligand": docked,
            "clash_score": clashes,
            "rotatable_bonds": docked.get("rotatable_bonds", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/jobs/{job_id}/optimize_pose")
async def optimize_pose(job_id: str, req: DockRequest):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = JOBS[job_id]
    if job["status"] != "complete" or not job["pocket_results"]:
        raise HTTPException(status_code=400, detail="Analysis not complete")
        
    if req.frame_id < 0 or req.frame_id >= len(job["frames"]):
        raise HTTPException(status_code=400, detail="Invalid frame_id")
        
    # Find pocket
    pocket = None
    all_pockets = (job["pocket_results"].cryptic_pockets + 
                   job["pocket_results"].constitutive_pockets + 
                   job["pocket_results"].rare_pockets)
    for p in all_pockets:
        if p.pocket_id == req.pocket_id:
            pocket = p
            break
            
    if not pocket:
        raise HTTPException(status_code=404, detail="Pocket not found")
        
    try:
        frame = job["frames"][req.frame_id]
        ca_coords = np.array(frame["ca_coords"])
        
        docked = await run_in_threadpool(
            optimize_docked_conformer, 
            req.smiles, 
            pocket.centroid,
            ca_coords
        )
        
        return {
            "ligand": docked,
            "clash_score": docked["clash_score"],
            "rotatable_bonds": docked.get("rotatable_bonds", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/jobs/{job_id}/dream")
async def dream_ligand(job_id: str, req: DreamRequest):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = JOBS[job_id]
    if job["status"] != "complete" or not job["pocket_results"]:
        raise HTTPException(status_code=400, detail="Analysis not complete")
        
    if req.frame_idx < 0 or req.frame_idx >= len(job["frames"]):
        raise HTTPException(status_code=400, detail="Invalid frame_idx")
        
    # Find pocket
    pocket = None
    all_pockets = (job["pocket_results"].cryptic_pockets + 
                   job["pocket_results"].constitutive_pockets + 
                   job["pocket_results"].rare_pockets)
    for p in all_pockets:
        if p.pocket_id == req.pocket_id:
            pocket = p
            break
            
    if not pocket:
        raise HTTPException(status_code=404, detail="Pocket not found")
        
    try:
        frame = job["frames"][req.frame_idx]
        ca_coords = np.array(frame["ca_coords"])
        
        res = await run_in_threadpool(
            run_genesis_loop, 
            pocket.centroid,
            ca_coords
        )
        
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

