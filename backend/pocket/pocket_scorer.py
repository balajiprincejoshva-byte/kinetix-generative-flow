from dataclasses import dataclass
from typing import List
from backend.pocket.alpha_sphere import Pocket
import backend.config as config

AA_HYDROPHOBIC = {'A', 'V', 'I', 'L', 'M', 'F', 'W', 'P', 'ALA', 'VAL', 'ILE', 'LEU', 'MET', 'PHE', 'TRP', 'PRO'}
AA_POLAR = {'S', 'T', 'C', 'Y', 'N', 'Q', 'SER', 'THR', 'CYS', 'TYR', 'ASN', 'GLN'}
AA_CHARGED = {'D', 'E', 'K', 'R', 'H', 'ASP', 'GLU', 'LYS', 'ARG', 'HIS'}

@dataclass
class ScoredPocket:
    pocket: Pocket
    volume: float
    hydrophobicity_score: float
    buriedness: float
    polarity_score: float
    shape_score: float
    druggability_score: float  # [0, 1]
    is_druggable: bool

def score_pocket(pocket: Pocket, residue_names: List[str]) -> ScoredPocket:
    lining_names = [residue_names[i] for i in pocket.lining_residues if i < len(residue_names)]
    
    n_lining = len(lining_names)
    if n_lining == 0:
        return ScoredPocket(pocket, pocket.volume, 0, 0, 0, 0, 0, False)
        
    n_hydro = sum(1 for aa in lining_names if aa in AA_HYDROPHOBIC)
    n_polar = sum(1 for aa in lining_names if aa in AA_POLAR or aa in AA_CHARGED)
    
    hydrophobicity_score = n_hydro / n_lining
    polarity_score = n_polar / n_lining
    
    # Very crude approximation of buriedness based on number of residues
    # If a pocket has many lining residues, it's more buried
    buriedness = min(1.0, n_lining / 20.0)
    
    # Shape score based on max radius vs equivalent spherical radius for volume
    # V = 4/3 pi r^3 => r_eq = (3V / 4pi)^(1/3)
    # sphericity = r_eq / max_radius
    r_eq = ((3 * pocket.volume) / (4 * 3.14159)) ** (1/3)
    shape_score = min(1.0, r_eq / (pocket.max_radius + 1e-5))
    
    volume_score = min(pocket.volume / 500.0, 1.0)
    
    druggability_score = (
        0.4 * volume_score +
        0.3 * hydrophobicity_score +
        0.2 * buriedness +
        0.1 * shape_score
    )
    
    # Cap at 1.0
    druggability_score = min(1.0, max(0.0, druggability_score))
    
    is_druggable = druggability_score > config.DRUGGABILITY_THRESHOLD
    
    return ScoredPocket(
        pocket=pocket,
        volume=pocket.volume,
        hydrophobicity_score=hydrophobicity_score,
        buriedness=buriedness,
        polarity_score=polarity_score,
        shape_score=shape_score,
        druggability_score=druggability_score,
        is_druggable=is_druggable
    )

def score_all_pockets(pockets: List[Pocket], residue_names: List[str]) -> List[ScoredPocket]:
    return [score_pocket(p, residue_names) for p in pockets if p.volume > config.MIN_POCKET_VOLUME]
