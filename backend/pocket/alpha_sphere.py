import numpy as np
from scipy.spatial import Delaunay
from sklearn.cluster import DBSCAN
from dataclasses import dataclass
from typing import List
from scipy.spatial import cKDTree

@dataclass
class AlphaSphere:
    center: np.ndarray  # (3,)
    radius: float
    nearby_residue_ids: List[int]  # indices into the residue list

@dataclass
class Pocket:
    pocket_id: int
    centroid: np.ndarray    # (3,)
    volume: float           # Angstroms^3
    alpha_spheres: List[AlphaSphere]
    lining_residues: List[int]  # residue indices that line this pocket
    max_radius: float

def circumsphere(points: np.ndarray):
    """Calculate the circumsphere of a tetrahedron (4 points in 3D)."""
    # points: (4, 3)
    a = points[0]
    b = points[1] - a
    c = points[2] - a
    d = points[3] - a
    
    mat = np.array([
        [b[0], b[1], b[2]],
        [c[0], c[1], c[2]],
        [d[0], d[1], d[2]]
    ])
    
    try:
        inv = np.linalg.inv(mat)
    except np.linalg.LinAlgError:
        return None, 0.0
        
    v2 = np.array([
        np.dot(b, b),
        np.dot(c, c),
        np.dot(d, d)
    ])
    
    center = 0.5 * np.dot(v2, inv)
    radius = np.linalg.norm(center)
    return center + a, radius

def detect_alpha_spheres(
    coords: np.ndarray,          # (N_atoms, 3)
    residue_assignments: np.ndarray,  # (N_atoms,) — which residue each atom belongs to
    probe_radius: float = 3.5,
    r_max: float = 10.0
) -> List[AlphaSphere]:
    
    if len(coords) < 4:
        return []

    tri = Delaunay(coords)
    tree = cKDTree(coords)
    alpha_spheres = []
    
    for simplex in tri.simplices:
        pts = coords[simplex]
        center, radius = circumsphere(pts)
        
        if center is None:
            continue
            
        if radius > probe_radius and radius < r_max:
            # Check for overlap: distance to nearest atom must be >= radius - small tolerance
            dist, idx = tree.query(center)
            # The simplex atoms themselves are at distance 'radius'. 
            # If the closest atom is significantly closer than radius, it means the sphere intersects an atom.
            # Usually dist will be equal to radius (minus floating point errors).
            if dist > radius - 0.1:
                # Find nearby residues (within radius + 2.0 A)
                nearby_idxs = tree.query_ball_point(center, radius + 2.0)
                nearby_residues = list(set([int(residue_assignments[i]) for i in nearby_idxs]))
                
                alpha_spheres.append(AlphaSphere(
                    center=center,
                    radius=radius,
                    nearby_residue_ids=nearby_residues
                ))
                
    return alpha_spheres

def cluster_pockets(alpha_spheres: List[AlphaSphere], eps: float = 1.5) -> List[Pocket]:
    if not alpha_spheres:
        return []
        
    centers = np.array([s.center for s in alpha_spheres])
    clustering = DBSCAN(eps=eps, min_samples=3).fit(centers)
    
    pockets = []
    pocket_id = 0
    for label in set(clustering.labels_):
        if label == -1:
            continue # noise
            
        indices = np.where(clustering.labels_ == label)[0]
        cluster_spheres = [alpha_spheres[i] for i in indices]
        
        centroid = np.mean([s.center for s in cluster_spheres], axis=0)
        
        # Approximate volume: union of spheres is hard, sum of volumes is overestimate.
        # But we can just use sum of volumes and cap it, or just use it as relative measure.
        # Let's do sum of volumes for simplicity, scaled down to account for overlap.
        volumes = [(4/3) * np.pi * (s.radius ** 3) for s in cluster_spheres]
        volume = sum(volumes) * 0.3 # roughly 30% of sum to account for high overlap
        
        lining_res = set()
        max_r = 0.0
        for s in cluster_spheres:
            lining_res.update(s.nearby_residue_ids)
            if s.radius > max_r:
                max_r = s.radius
                
        pockets.append(Pocket(
            pocket_id=pocket_id,
            centroid=centroid,
            volume=volume,
            alpha_spheres=cluster_spheres,
            lining_residues=list(lining_res),
            max_radius=max_r
        ))
        pocket_id += 1
        
    return pockets
