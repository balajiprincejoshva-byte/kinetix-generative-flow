from rdkit import Chem
from rdkit.Chem import AllChem, rdMolDescriptors
import numpy as np
from typing import List, Dict, Any

def generate_docked_conformer(smiles: str, pocket_centroid: List[float]) -> Dict[str, Any]:
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        raise ValueError("Invalid SMILES string")
        
    mol = Chem.AddHs(mol)
    res = AllChem.EmbedMolecule(mol, randomSeed=42)
    if res != 0:
        # Fallback
        res = AllChem.EmbedMolecule(mol, useRandomCoords=True, randomSeed=42)
        if res != 0:
            raise ValueError("Failed to generate 3D conformer")
            
    AllChem.MMFFOptimizeMolecule(mol)
    
    conf = mol.GetConformer()
    atoms = []
    
    coords = np.array([conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())])
    centroid = coords.mean(axis=0)
    
    target = np.array(pocket_centroid)
    translation = target - centroid
    
    for i, atom in enumerate(mol.GetAtoms()):
        pos = conf.GetAtomPosition(i)
        new_pos = [float(pos.x + translation[0]), float(pos.y + translation[1]), float(pos.z + translation[2])]
        atoms.append({
            "element": atom.GetSymbol(),
            "coords": new_pos
        })
        
    rot_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol)
        
    return {"atoms": atoms, "rotatable_bonds": rot_bonds}

def optimize_docked_conformer(smiles: str, pocket_centroid: List[float], ca_coords: np.ndarray, num_confs: int = 20) -> Dict[str, Any]:
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        raise ValueError("Invalid SMILES string")
        
    mol = Chem.AddHs(mol)
    
    res = AllChem.EmbedMultipleConfs(mol, numConfs=num_confs, randomSeed=42)
    if not res:
        res = AllChem.EmbedMultipleConfs(mol, numConfs=num_confs, useRandomCoords=True, randomSeed=42)
        if not res:
            from rdkit.Chem import rdDepictor
            rdDepictor.Compute2DCoords(mol)
            res = AllChem.EmbedMultipleConfs(mol, numConfs=1, useBasicKnowledge=True, enforceChirality=False, randomSeed=42)
            if not res:
                raise ValueError("Failed to generate 3D conformers even with relaxed fallbacks.")
            
    AllChem.MMFFOptimizeMoleculeConfs(mol, numThreads=0)
    
    best_clash_score = float('inf')
    best_atoms = None
    target = np.array(pocket_centroid)
    
    for conf_id in res:
        conf = mol.GetConformer(conf_id)
        coords = np.array([conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())])
        centroid = coords.mean(axis=0)
        translation = target - centroid
        
        atoms = []
        for i, atom in enumerate(mol.GetAtoms()):
            pos = conf.GetAtomPosition(i)
            new_pos = [float(pos.x + translation[0]), float(pos.y + translation[1]), float(pos.z + translation[2])]
            atoms.append({
                "element": atom.GetSymbol(),
                "coords": new_pos
            })
            
        score = score_clashes(atoms, ca_coords)
        if score < best_clash_score:
            best_clash_score = score
            best_atoms = atoms
            if score == 0:
                break
                
    rot_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol)
                
    return {"atoms": best_atoms, "clash_score": best_clash_score, "rotatable_bonds": rot_bonds}

def score_clashes(ligand_atoms: List[Dict], protein_coords: np.ndarray) -> float:
    from scipy.spatial.distance import cdist
    
    if len(ligand_atoms) == 0 or len(protein_coords) == 0:
        return 0.0
        
    ligand_coords = np.array([a["coords"] for a in ligand_atoms])
    dists = cdist(ligand_coords, protein_coords)
    
    # Threshold for steric clash
    n_clashes = np.sum(dists < 2.5)
    return float(n_clashes)
