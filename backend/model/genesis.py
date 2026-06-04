import random
import numpy as np
from rdkit import Chem
from rdkit.Chem import QED
from rdkit.Chem import rdChemReactions
from rdkit.Chem import Descriptors
from typing import List, Dict, Any

from backend.model.admet import ADMETPredictor
from backend.model.docking import optimize_docked_conformer
from backend.model.llm_agent import BioLLMAgent

MUTATION_SMARTS = [
    '[c:1][H]>>[c:1]O',          # Add hydroxyl to aromatic
    '[c:1][H]>>[c:1]F',          # Add fluorine to aromatic
    '[c:1][H]>>[c:1]C',          # Add methyl to aromatic
    '[c:1][H]>>[c:1]N',          # Add amine to aromatic
    '[c:1][H]>>[c:1]Cl',         # Add Chlorine
    '[C:1]([H])([H])[H]>>[C:1]([H])([H])F', # Add fluorine to aliphatic
    '[C:1]([H])([H])[H]>>[C:1]([H])([H])O', # Add hydroxyl to aliphatic
]

REACTIONS = [rdChemReactions.ReactionFromSmarts(sm) for sm in MUTATION_SMARTS]

def mutate_mol(mol: Chem.Mol) -> Chem.Mol:
    """Apply a random reaction to mutate the molecule."""
    # Try up to 5 times to find a valid mutation
    for _ in range(5):
        rxn = random.choice(REACTIONS)
        prods = rxn.RunReactants((mol,))
        if prods:
            # Pick a random product if multiple sites match
            new_mol = random.choice(prods)[0]
            try:
                Chem.SanitizeMol(new_mol)
                return new_mol
            except:
                pass
    return None

def run_genesis_loop(pocket_centroid: List[float], ca_coords: np.ndarray, seed_smiles: str = 'c1ccccc1NC(=O)C') -> Dict[str, Any]:
    """
    The Genesis Loop: Autonomous Agent for Drug Design.
    Runs a fast genetic algorithm with ADMET filtering and 3D scoring.
    """
    generations = 5
    population_size = 10
    
    # Initialize population with the seed
    seed_mol = Chem.MolFromSmiles(seed_smiles)
    if not seed_mol:
        seed_mol = Chem.MolFromSmiles('c1ccccc1')
        
    population = [seed_mol]
    
    # Expand initial population
    for _ in range(population_size - 1):
        mut = mutate_mol(seed_mol)
        if mut and ADMETPredictor.is_safe(mut):
            population.append(mut)
            
    best_overall_mol = seed_mol
    best_overall_score = float('inf')
    best_docking_res = None
    best_herg_penalty = 0.0
    
    for gen in range(generations):
        # 1. Score current population in 3D
        scored_pop = []
        for mol in population:
            smiles = Chem.MolToSmiles(mol)
            try:
                # generate 3D conformers, optimize, and score clashes
                # We limit to 5 confs in the GA to keep it blazing fast
                res = optimize_docked_conformer(smiles, pocket_centroid, ca_coords, num_confs=5)
                
                # Fitness = clash_score (lower is better) - QED (higher is better)
                # We want 0 clashes, high QED.
                qed_score = QED.qed(mol)
                
                # hERG Toxicity Model (Anti-Target)
                logp = Descriptors.MolLogP(mol)
                basic_amine = Chem.MolFromSmarts('[NX3;H2,H1;!$(NC=O)]')
                has_amine = mol.HasSubstructMatch(basic_amine)
                herg_penalty = logp * 1.5
                if has_amine:
                    herg_penalty += 3.0
                    
                fitness = res['clash_score'] * 5.0 - (qed_score * 10.0) + herg_penalty
                
                scored_pop.append((fitness, mol, res, herg_penalty))
            except:
                pass
                
        # Rank by fitness
        scored_pop.sort(key=lambda x: x[0])
        
        if not scored_pop:
            break
            
        # Track elites
        if scored_pop[0][0] < best_overall_score:
            best_overall_score = scored_pop[0][0]
            best_overall_mol = scored_pop[0][1]
            best_docking_res = scored_pop[0][2]
            best_herg_penalty = scored_pop[0][3]
            
            # If we found a perfect drug (0 clashes and good QED), we can early exit!
            if best_docking_res['clash_score'] == 0 and QED.qed(best_overall_mol) > 0.6:
                break
                
        # 2. Select Elites
        elites = [x[1] for x in scored_pop[:3]]
        
        # 3. Mutate for next generation
        next_gen = elites.copy()
        attempts = 0
        while len(next_gen) < population_size and attempts < 50:
            attempts += 1
            parent = random.choice(elites)
            child = mutate_mol(parent)
            
            if child:
                # The Silent Killer: ADMET Toxicity Filter
                if ADMETPredictor.is_safe(child):
                    next_gen.append(child)
                    
        # Fallback: Scaffold Reset
        if len(next_gen) < population_size:
            while len(next_gen) < population_size:
                next_gen.append(seed_mol)
                
        population = next_gen
        
    if not best_docking_res:
        # Fallback if something failed
        best_docking_res = optimize_docked_conformer(Chem.MolToSmiles(best_overall_mol), pocket_centroid, ca_coords)
        best_herg_penalty = Descriptors.MolLogP(best_overall_mol) * 1.5
        
    llm_analysis = BioLLMAgent.evaluate_synthesis(Chem.MolToSmiles(best_overall_mol))
    sel_index = 10.0 - best_docking_res['clash_score'] - best_herg_penalty
        
    return {
        "smiles": Chem.MolToSmiles(best_overall_mol),
        "ligand": {
            "atoms": best_docking_res['atoms']
        },
        "clash_score": best_docking_res['clash_score'],
        "rotatable_bonds": best_docking_res.get('rotatable_bonds', 0),
        "qed": QED.qed(best_overall_mol),
        "generations_run": gen + 1,
        "selectivity_index": round(sel_index, 2),
        "synthesis": llm_analysis
    }
