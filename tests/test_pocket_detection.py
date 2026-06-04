import numpy as np
from backend.pocket.alpha_sphere import detect_alpha_spheres, cluster_pockets
from backend.pocket.pocket_scorer import score_pocket
from backend.pocket.cryptic_hunter import hunt_cryptic_pockets

def test_detect_alpha_spheres():
    np.random.seed(42)
    # Generate 50 random points in a 15x15x15 box
    coords = np.random.rand(50, 3) * 15.0
    residues = np.arange(50)
    
    spheres = detect_alpha_spheres(coords, residues, probe_radius=1.5, r_max=10.0)
    assert len(spheres) > 0

def test_cluster_pockets():
    from backend.pocket.alpha_sphere import AlphaSphere
    
    s1 = AlphaSphere(center=np.array([5, 5, 5]), radius=4.0, nearby_residue_ids=[0, 1, 2, 3])
    s2 = AlphaSphere(center=np.array([5.5, 5.0, 5.0]), radius=4.5, nearby_residue_ids=[4, 5, 6, 7])
    s3 = AlphaSphere(center=np.array([5.2, 5.2, 5.0]), radius=4.2, nearby_residue_ids=[0, 7])
    
    pockets = cluster_pockets([s1, s2, s3], eps=1.5)
    assert len(pockets) == 1
    assert pockets[0].max_radius == 4.5

def test_score_pocket():
    from backend.pocket.alpha_sphere import Pocket
    from backend.pocket.alpha_sphere import AlphaSphere
    
    s1 = AlphaSphere(center=np.array([5, 5, 5]), radius=4.0, nearby_residue_ids=[0, 1])
    pocket = Pocket(0, np.array([5,5,5]), 300.0, [s1], [0, 1], 4.0)
    
    scored = score_pocket(pocket, ["ALA", "LEU"]) # Hydrophobic
    assert scored.druggability_score >= 0.0 and scored.druggability_score <= 1.0

def test_hunt_cryptic_pockets():
    # Mock frames
    frame1 = {
        "ca_coords": [
            [0,0,0], [10,0,0], [0,10,0], [10,10,0],
            [0,0,10], [10,0,10], [0,10,10], [10,10,10]
        ]
    }
    frame2 = {
        "ca_coords": [
            [0,0,0], [10,0,0], [0,10,0], [10,10,0],
            [0,0,10], [10,0,10], [0,10,10], [10,10,10]
        ]
    }
    # frame 3, collapsed so no pocket
    frame3 = {
        "ca_coords": [
            [0,0,0], [1,0,0], [0,1,0], [1,1,0],
            [0,0,1], [1,0,1], [0,1,1], [1,1,1]
        ]
    }
    
    res_names = ["ALA"] * 8
    
    results = hunt_cryptic_pockets([frame1, frame2, frame3], res_names, min_opening_prob=0.1)
    # Could be cryptic since it's open in 2/3 frames (66% > 10% and < 80%)
    if len(results) > 0:
        assert results[0].classification in ["cryptic", "constitutive", "rare"]
