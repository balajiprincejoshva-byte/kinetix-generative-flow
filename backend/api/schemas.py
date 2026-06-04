from pydantic import BaseModel, Field
from typing import List, Optional

class UploadPDBResponse(BaseModel):
    job_id: str
    n_residues: int
    sequence: str
    message: str

class ConformationFrame(BaseModel):
    frame_id: int
    ca_coords: List[List[float]]    # (N, 3)
    bb_coords: List[List[List[float]]]  # (N, 4, 3)
    rmsd_from_input: float

class ConformationChunk(BaseModel):
    frames: List[ConformationFrame]
    total_generated: int
    is_final: bool

class PocketInfo(BaseModel):
    pocket_id: int
    classification: str
    opening_probability: float
    peak_druggability: float
    centroid: List[float]           # [x, y, z]
    representative_frame: int
    lining_residues: List[int]
    presence_vector: List[float]    # druggability across all frames

class AnalysisResult(BaseModel):
    job_id: str
    n_frames_analyzed: int
    cryptic_pockets: List[PocketInfo]
    constitutive_pockets: List[PocketInfo]
    rare_pockets: List[PocketInfo]
    analysis_time_seconds: float
    latent_landscape: Optional[List[dict]] = None
