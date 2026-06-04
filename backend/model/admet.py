from rdkit import Chem
from rdkit.Chem import Descriptors

class ADMETPredictor:
    @staticmethod
    def is_safe(mol: Chem.Mol) -> bool:
        """
        Mock XGBoost microservice for Toxicity/ADMET.
        Uses heuristics representing standard ADMET cutoffs.
        """
        if not mol:
            return False
            
        try:
            mw = Descriptors.MolWt(mol)
            logp = Descriptors.MolLogP(mol)
            tpsa = Descriptors.TPSA(mol)
            
            # Lipinski / Veber rules + some strict toxicity filters
            if mw > 550: return False
            if logp > 5.0 or logp < -1.0: return False
            if tpsa > 140: return False
            
            # Check for highly reactive / toxic substructures
            
            # Epoxide: C1OC1
            epoxide = Chem.MolFromSmarts('C1OC1')
            if mol.HasSubstructMatch(epoxide): return False
            
            # Aldehyde
            aldehyde = Chem.MolFromSmarts('[CX3H1](=O)[#6]')
            if mol.HasSubstructMatch(aldehyde): return False
            
            # Quinone
            quinone = Chem.MolFromSmarts('O=C1C=CC(=O)C=C1')
            if mol.HasSubstructMatch(quinone): return False
            
            return True
        except Exception:
            return False
