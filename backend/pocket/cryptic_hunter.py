from dataclasses import dataclass, field
from typing import List, Dict
import numpy as np
import scipy.ndimage
from collections import defaultdict
from backend.pocket.alpha_sphere import detect_alpha_spheres, cluster_pockets
from backend.pocket.pocket_scorer import score_all_pockets, ScoredPocket

@dataclass
class CrypticPocket:
    cluster_id: int
    centroid: np.ndarray           # mean centroid across frames where present
    classification: str            # "constitutive" | "cryptic" | "rare"
    opening_probability: float     # fraction of frames present
    peak_druggability: float
    first_appearance_frame: int
    representative_frame: int      # best frame to show this pocket
    lining_residues: List[int]     # consensus lining residues
    presence_vector: np.ndarray    # (N_frames,) — druggability score per frame

def cluster_pockets_across_frames(
    all_frame_pockets: List[List[ScoredPocket]]
) -> Dict[int, List]:  # cluster_id → list of (frame_idx, ScoredPocket)
    """Use centroid-based greedy clustering with 5Å merge radius."""
    clusters = defaultdict(list)
    cluster_centroids = {}
    next_cluster_id = 0
    
    for frame_idx, frame_pockets in enumerate(all_frame_pockets):
        for sp in frame_pockets:
            centroid = sp.pocket.centroid
            
            # Find closest cluster
            best_cluster_id = -1
            min_dist = 5.0 # merge radius
            
            for cid, c_cent in cluster_centroids.items():
                dist = np.linalg.norm(centroid - c_cent)
                if dist < min_dist:
                    min_dist = dist
                    best_cluster_id = cid
                    
            if best_cluster_id != -1:
                # Add to existing cluster and update centroid (moving average)
                clusters[best_cluster_id].append((frame_idx, sp))
                n_members = len(clusters[best_cluster_id])
                # incremental update of centroid
                cluster_centroids[best_cluster_id] = (cluster_centroids[best_cluster_id] * (n_members - 1) + centroid) / n_members
            else:
                # New cluster
                clusters[next_cluster_id].append((frame_idx, sp))
                cluster_centroids[next_cluster_id] = centroid
                next_cluster_id += 1
                
    return clusters

def hunt_cryptic_pockets(
    ensemble_frames: List[dict],          # list of conformation dicts from inference
    residue_names: List[str],
    min_opening_prob: float = 0.10,
    max_constitutive_prob: float = 0.80,
) -> List[CrypticPocket]:
    """
    Main entry point. Takes all 100 frames, runs pocket detection on each,
    clusters across frames, classifies, and returns list of CrypticPocket.
    """
    
    n_frames = len(ensemble_frames)
    all_frame_pockets = []
    
    # We map residue_names to a dummy residue_assignments array where each atom in CA belongs to residue i
    # Wait, detect_alpha_spheres expects coords (N_atoms, 3) and residue_assignments (N_atoms,)
    # If we pass just CA and CB, we can do that. Or just CA.
    
    for frame in ensemble_frames:
        ca_coords = np.array(frame["ca_coords"]) # (N, 3)
        # Using just CA for speed and simplicity. 
        # residue_assignments is just 0 to N-1
        n_res = ca_coords.shape[0]
        residue_assignments = np.arange(n_res)
        
        # Detect alpha spheres
        alpha_spheres = detect_alpha_spheres(ca_coords, residue_assignments, probe_radius=3.5, r_max=10.0)
        
        # Cluster into pockets
        pockets = cluster_pockets(alpha_spheres, eps=1.5)
        
        # Score pockets
        scored = score_all_pockets(pockets, residue_names)
        all_frame_pockets.append(scored)
        
    # Cluster across frames
    clusters = cluster_pockets_across_frames(all_frame_pockets)
    
    results = []
    for cid, members in clusters.items():
        # Build presence vector
        presence = np.zeros(n_frames)
        for frame_idx, sp in members:
            # If a frame has multiple pockets assigned to same cluster, take max druggability
            presence[frame_idx] = max(presence[frame_idx], sp.druggability_score)
            
        # Gaussian smoothing
        smoothed_presence = scipy.ndimage.gaussian_filter1d(presence, sigma=2.0)
        
        # Calculate stats on smoothed presence
        # Threshold for "open" is > DRUGGABILITY_THRESHOLD (e.g. 0.55), but let's use a lower one or 0
        # Wait, presence is druggability_score. Let's say it's open if smoothed > 0.3
        is_open = smoothed_presence > 0.3
        opening_probability = np.mean(is_open)
        
        # Classify
        if opening_probability > max_constitutive_prob:
            classification = "constitutive"
        elif opening_probability > min_opening_prob:
            classification = "cryptic"
        else:
            classification = "rare"
            
        peak_druggability = float(np.max(presence))
        first_appearance = int(np.argmax(is_open)) if opening_probability > 0 else 0
        representative_frame = int(np.argmax(presence))
        
        # Consensus lining residues
        lining_counts = defaultdict(int)
        for _, sp in members:
            for res_id in sp.pocket.lining_residues:
                lining_counts[res_id] += 1
                
        # Keep residues present in at least 30% of instances
        consensus_lining = [res_id for res_id, count in lining_counts.items() if count / len(members) >= 0.3]
        
        # Mean centroid
        centroid = np.mean([sp.pocket.centroid for _, sp in members], axis=0)
        
        cp = CrypticPocket(
            cluster_id=cid,
            centroid=centroid,
            classification=classification,
            opening_probability=float(opening_probability),
            peak_druggability=peak_druggability,
            first_appearance_frame=first_appearance,
            representative_frame=representative_frame,
            lining_residues=consensus_lining,
            presence_vector=smoothed_presence
        )
        results.append(cp)
        
    # Sort by druggability descending
    results.sort(key=lambda x: x.peak_druggability, reverse=True)
    return results
