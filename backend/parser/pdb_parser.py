from dataclasses import dataclass
import numpy as np
from Bio.PDB import PDBParser as BioPDBParser
from typing import List, Tuple, Union
import io
import warnings
from Bio import BiopythonWarning
from scipy.spatial import cKDTree
from backend.config import MAX_RESIDUES

# Suppress Biopython warnings for discontinuous chains, etc.
warnings.simplefilter('ignore', BiopythonWarning)

@dataclass
class ProteinGraph:
    residue_ids: List[Tuple]
    ca_coords: np.ndarray      # (N, 3)
    cb_coords: np.ndarray      # (N, 3)
    bb_coords: np.ndarray      # (N, 4, 3) — N, CA, C, O per residue
    sequence: str
    n_residues: int
    distance_matrix: np.ndarray  # (N, N)
    edge_index: np.ndarray       # (2, E) — k-NN graph edges
    edge_attr: np.ndarray        # (E,) — edge distances

# AA 3-to-1 letter code mapping
AA_MAP = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLN': 'Q', 'GLU': 'E', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'
}

def parse_pdb(pdb_source: Union[str, bytes]) -> ProteinGraph:
    parser = BioPDBParser(QUIET=True)
    
    if isinstance(pdb_source, bytes):
        structure = parser.get_structure("protein", io.StringIO(pdb_source.decode('utf-8')))
    else:
        structure = parser.get_structure("protein", pdb_source)
        
    model = structure[0] # Take only MODEL 1
    
    residue_ids = []
    ca_coords_list = []
    cb_coords_list = []
    bb_coords_list = []
    sequence_list = []
    
    for chain in model:
        for residue in chain:
            # Skip hetero atoms and water
            if residue.id[0] != ' ':
                continue
            
            res_name = residue.resname.strip()
            
            # Simple check for amino acid
            if res_name not in AA_MAP and res_name != 'UNK':
                continue
                
            # Need at least CA to proceed
            if 'CA' not in residue:
                continue
                
            ca = residue['CA'].get_coord()
            
            # For GLY, CB is at CA position, otherwise get CB or fallback to CA
            if res_name == 'GLY':
                cb = ca.copy()
            else:
                if 'CB' in residue:
                    cb = residue['CB'].get_coord()
                else:
                    cb = ca.copy()
            
            # Get backbone (N, CA, C, O)
            n_coord = residue['N'].get_coord() if 'N' in residue else ca.copy()
            c_coord = residue['C'].get_coord() if 'C' in residue else ca.copy()
            o_coord = residue['O'].get_coord() if 'O' in residue else ca.copy()
            
            residue_ids.append((chain.id, residue.id[1], res_name))
            ca_coords_list.append(ca)
            cb_coords_list.append(cb)
            bb_coords_list.append([n_coord, ca, c_coord, o_coord])
            sequence_list.append(AA_MAP.get(res_name, 'X'))
            
    n_residues = len(residue_ids)
    
    if n_residues < 10:
        raise ValueError(f"PDB has too few residues ({n_residues}). Minimum is 10.")
    if n_residues > MAX_RESIDUES:
        raise ValueError(f"PDB has too many residues ({n_residues}). Maximum is {MAX_RESIDUES}.")
        
    ca_coords = np.array(ca_coords_list)
    cb_coords = np.array(cb_coords_list)
    bb_coords = np.array(bb_coords_list)
    sequence = "".join(sequence_list)
    
    # Compute distance matrix
    # Compute pairwise Euclidean distance between all CA atoms
    diff = ca_coords[:, np.newaxis, :] - ca_coords[np.newaxis, :, :]
    distance_matrix = np.sqrt(np.sum(diff ** 2, axis=-1))
    
    # Compute KNN graph
    edge_index, edge_attr = compute_knn_graph(ca_coords, k=min(10, n_residues))
    
    return ProteinGraph(
        residue_ids=residue_ids,
        ca_coords=ca_coords,
        cb_coords=cb_coords,
        bb_coords=bb_coords,
        sequence=sequence,
        n_residues=n_residues,
        distance_matrix=distance_matrix,
        edge_index=edge_index,
        edge_attr=edge_attr
    )

def compute_knn_graph(ca_coords: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
    tree = cKDTree(ca_coords)
    # query includes the point itself, so we query k+1 points if we wanted to exclude self, 
    # but GNNs often include self-loops or handle them, let's just query k points and self loops might be included,
    # or actually we can include self-loops since distance is 0. 
    # We query k closest neighbors for each node.
    distances, indices = tree.query(ca_coords, k=k)
    
    # Flatten the results
    n_nodes = ca_coords.shape[0]
    
    # Create edge_index (2, E)
    # Source nodes
    src = np.repeat(np.arange(n_nodes), k)
    # Target nodes
    dst = indices.flatten()
    
    edge_index = np.stack([src, dst], axis=0)
    edge_attr = distances.flatten()
    
    return edge_index, edge_attr
