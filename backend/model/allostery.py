import numpy as np
from typing import List, Dict

def compute_dccm(ca_coords_frames: np.ndarray) -> np.ndarray:
    """
    Computes the Dynamic Cross-Correlation Matrix (DCCM) across frames.
    ca_coords_frames: (n_frames, N, 3)
    """
    n_frames = ca_coords_frames.shape[0]
    
    # 1. Mean coords (N, 3)
    mean_coords = np.mean(ca_coords_frames, axis=0)
    
    # 2. Displacements (n_frames, N, 3)
    displacements = ca_coords_frames - mean_coords
    
    # 3. Transpose for tensordot (N, 3, n_frames)
    D = np.transpose(displacements, (1, 2, 0))
    
    # 4. Covariance (N, N)
    cov = np.tensordot(D, D, axes=([1, 2], [1, 2])) / n_frames
    
    # 5. Variance (N,)
    var = np.diagonal(cov)
    
    # 6. Normalize
    dccm = cov / np.sqrt(np.outer(var, var))
    return dccm

def get_allosteric_webs(dccm: np.ndarray, lining_residues: List[int], n_residues: int, threshold: float = 0.5) -> List[Dict]:
    """
    Finds residues distant from the pocket that are highly correlated.
    Returns list of dicts {"source": int, "target": int, "correlation": float}
    """
    webs = []
    lining_set = set(lining_residues)
    
    for p_res in lining_residues:
        for i in range(n_residues):
            # Ignore adjacent residues in sequence to focus on 3D allostery
            if i in lining_set or abs(i - p_res) < 5:
                continue
                
            corr = float(dccm[p_res, i])
            if abs(corr) >= threshold:
                webs.append({
                    "source": p_res,
                    "target": i,
                    "correlation": corr
                })
                
    # Sort by absolute correlation and return top N
    webs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return webs[:30] # Top 30 splines for visual density
