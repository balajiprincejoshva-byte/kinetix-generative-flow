import torch
import numpy as np
from typing import Generator, List
import os
from backend.model.flow_matching import KinetiXFlowModel
from backend.parser.pdb_parser import ProteinGraph
import backend.config as config
import scipy.linalg

def load_or_init_model():
    """
    Checks for weights. If not found, initializes random weights and sets a flag
    to indicate it's untrained (so we can use NMA perturbation for visually interesting results).
    """
    model = KinetiXFlowModel(config)
    weights_path = os.path.join(os.path.dirname(__file__), "..", "..", "weights", "kinetics_model.pt")
    if os.path.exists(weights_path):
        model.load_state_dict(torch.load(weights_path, map_location="cpu"))
        model.is_trained = True
    else:
        model.is_trained = False
    model.eval()
    return model

def compute_rmsd(coords_a: np.ndarray, coords_b: np.ndarray) -> float:
    """Kabsch-aligned RMSD between two (N,3) coordinate sets."""
    # Center coords
    c_a = coords_a - coords_a.mean(axis=0)
    c_b = coords_b - coords_b.mean(axis=0)
    
    # Covariance matrix
    H = np.dot(c_a.T, c_b)
    
    # SVD
    U, S, Vt = np.linalg.svd(H)
    
    # Rotation matrix
    d = np.sign(np.linalg.det(np.dot(Vt.T, U.T)))
    R = np.dot(Vt.T, np.dot(np.diag([1, 1, d]), U.T))
    
    # Rotate and compute RMSD
    c_b_rotated = np.dot(c_b, R)
    rmsd = np.sqrt(np.mean(np.sum((c_a - c_b_rotated)**2, axis=1)))
    return float(rmsd)

def reconstruct_backbone_from_ca(ca_coords: np.ndarray) -> np.ndarray:
    """
    Given CA coordinates (N, 3), reconstruct idealized N, C, O positions.
    Very simplified idealized geometry for demo purposes.
    """
    N = ca_coords.shape[0]
    bb_coords = np.zeros((N, 4, 3))
    
    # Set CA
    bb_coords[:, 1, :] = ca_coords
    
    # Approximate N, C, O using adjacent CA atoms to determine direction
    for i in range(N):
        prev_ca = ca_coords[i-1] if i > 0 else ca_coords[i]
        next_ca = ca_coords[i+1] if i < N - 1 else ca_coords[i]
        
        if i == 0:
            direction = (next_ca - ca_coords[i])
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            prev_ca = ca_coords[i] - direction * 3.8
            
        if i == N - 1:
            direction = (ca_coords[i] - prev_ca)
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            next_ca = ca_coords[i] + direction * 3.8
            
        v1 = prev_ca - ca_coords[i]
        v2 = next_ca - ca_coords[i]
        
        # Cross product to get a perpendicular vector
        norm_v = np.cross(v1, v2)
        norm_n = np.linalg.norm(norm_v)
        if norm_n > 1e-8:
            norm_v = norm_v / norm_n
        else:
            norm_v = np.array([0.0, 1.0, 0.0])
            
        # N is generally towards prev_ca
        n_dir = (v1 / (np.linalg.norm(v1) + 1e-8)) * 1.46
        bb_coords[i, 0, :] = ca_coords[i] + n_dir + norm_v * 0.2
        
        # C is generally towards next_ca
        c_dir = (v2 / (np.linalg.norm(v2) + 1e-8)) * 1.52
        bb_coords[i, 2, :] = ca_coords[i] + c_dir - norm_v * 0.2
        
        # O is perpendicular
        o_dir = np.cross(c_dir, norm_v)
        o_dir = (o_dir / (np.linalg.norm(o_dir) + 1e-8)) * 1.23
        bb_coords[i, 3, :] = bb_coords[i, 2, :] + o_dir
        
    return bb_coords

def compute_nma_modes(distance_matrix: np.ndarray, ca_coords: np.ndarray, n_modes: int = 10):
    """Compute low-frequency normal modes using an Elastic Network Model (ANM)."""
    N = distance_matrix.shape[0]
    cutoff = 15.0 # Angstroms
    
    H = np.zeros((3*N, 3*N))
    for i in range(N):
        for j in range(i+1, N):
            dist = distance_matrix[i, j]
            if dist < cutoff and dist > 0.1:
                # Spring constant (gamma) decreases with distance in some models, or just constant
                gamma = 1.0
                
                # Direction vector
                v = ca_coords[j] - ca_coords[i]
                v = v / dist
                
                # Outer product
                h_ij = -gamma * np.outer(v, v)
                
                H[3*i:3*i+3, 3*j:3*j+3] = h_ij
                H[3*j:3*j+3, 3*i:3*i+3] = h_ij
                
                H[3*i:3*i+3, 3*i:3*i+3] -= h_ij
                H[3*j:3*j+3, 3*j:3*j+3] -= h_ij
                
    # Diagonalize
    eigenvalues, eigenvectors = scipy.linalg.eigh(H)
    
    # Find first n_modes eigenvalues strictly greater than a small threshold to avoid rigid-body/disconnected modes
    valid_idx = np.where(eigenvalues > 1e-3)[0]
    if len(valid_idx) < n_modes:
        valid_idx = np.arange(len(eigenvalues) - n_modes, len(eigenvalues))
    idx = valid_idx[:n_modes]
    
    modes = eigenvectors[:, idx]
    evals = eigenvalues[idx]
    
    # Shape: (n_modes, N, 3)
    modes = modes.T.reshape(n_modes, N, 3)
    
    return modes, evals

def sample_ensemble(
    model: KinetiXFlowModel,
    protein_graph: ProteinGraph,
    n_samples: int = 100,
    chunk_size: int = 10,
    device: str = "cpu"
) -> Generator[List[dict], None, None]:
    
    N = protein_graph.n_residues
    ca_base = protein_graph.ca_coords
    
    # If the model is untrained, we use NMA for visually pleasing dynamics
    use_nma = not getattr(model, "is_trained", False)
    
    if use_nma:
        modes, evals = compute_nma_modes(protein_graph.distance_matrix, ca_base, n_modes=5)
        # Amplitudes for the modes (bounded to prevent explosions)
        amplitudes = 1.0 / (np.sqrt(np.abs(evals)) + 1e-2)

    for chunk_start in range(0, n_samples, chunk_size):
        chunk = []
        for i in range(chunk_start, min(chunk_start + chunk_size, n_samples)):
            frame_id = i
            
            if use_nma:
                # Random coefficients for the modes
                coeffs = np.random.randn(5) * amplitudes
                
                # Perturb coords
                perturbation = np.zeros_like(ca_base)
                for m in range(5):
                    perturbation += coeffs[m] * modes[m]
                
                # Limit the maximum displacement of any single atom to prevent "spikes"
                max_disp = np.linalg.norm(perturbation, axis=1).max()
                if max_disp > 5.0:
                    perturbation = perturbation * (5.0 / max_disp)
                
                # Generate new ca coords and remove any center of mass drift
                ca_new = ca_base + perturbation
                ca_new = ca_new - ca_new.mean(axis=0) + ca_base.mean(axis=0)
                
            else:
                # Use Flow-Matching (Simplified Euler for demo)
                with torch.no_grad():
                    # Prepare node input
                    # Need to mock this slightly since we didn't add mapping to aa_types in parser explicitly yet, 
                    # but we can just use 0s for now
                    aa_types = torch.zeros(N, dtype=torch.long, device=device)
                    ca_tensor = torch.tensor(ca_base, dtype=torch.float32, device=device)
                    edge_idx_t = torch.tensor(protein_graph.edge_index, dtype=torch.long, device=device)
                    edge_attr_t = torch.tensor(protein_graph.edge_attr, dtype=torch.float32, device=device)
                    
                    # initial noise near structure
                    x_t = ca_tensor + 0.5 * torch.randn_like(ca_tensor)
                    
                    dt = 1.0 / config.FLOW_STEPS
                    
                    node_emb, _ = model.encoder(aa_types, ca_tensor, edge_idx_t, edge_attr_t)
                    
                    for step in range(config.FLOW_STEPS):
                        t = torch.tensor([1.0 - step * dt], device=device)
                        v_pred = model.decoder(x_t, node_emb, t)
                        x_t = x_t - v_pred * dt  # Reverse ODE is going backwards in time
                        
                    ca_new = x_t.cpu().numpy()
            
            # Reconstruct backbone
            bb_new = reconstruct_backbone_from_ca(ca_new)
            
            # Calculate RMSD
            rmsd = compute_rmsd(ca_base, ca_new)
            
            # Create dict (coords to list for JSON serialization)
            chunk.append({
                "frame_id": frame_id,
                "ca_coords": ca_new.tolist(),
                "bb_coords": bb_new.tolist(),
                "rmsd_from_input": float(rmsd)
            })
            
        yield chunk
