from rdkit import Chem
from rdkit.Chem import Descriptors

class BioLLMAgent:
    @staticmethod
    def evaluate_synthesis(smiles: str) -> dict:
        """
        Simulated SpatialCP v2 Bio-Agent for Synthetic Accessibility.
        Parses the chemical structure heuristically to generate a realistic synthesis plan.
        """
        mol = Chem.MolFromSmiles(smiles)
        if not mol:
            return {
                "sa_score": 10.0,
                "analysis": "CRITICAL ERROR: Unable to parse chemical structure. Synthesis impossible."
            }
            
        analysis = []
        sa_score = 1.0 # Base score (1 = easy, 10 = hard)
        
        # 1. Halogen / Aromatic check (Cross-Coupling)
        halogens = Chem.MolFromSmarts('[F,Cl,Br,I][c]')
        if mol.HasSubstructMatch(halogens):
            analysis.append("Detected aryl halide substructure. This scaffold is highly amenable to standard Pd-catalyzed cross-coupling (e.g., Suzuki-Miyaura) using commercially available boronic acids.")
            sa_score += 0.5
            
        # 2. Amide bond check
        amide = Chem.MolFromSmarts('[NX3][CX3](=[OX1])')
        if mol.HasSubstructMatch(amide):
            analysis.append("Amide bond present. Can be synthesized efficiently via standard peptide coupling reagents (HATU/DIPEA) from corresponding amines and carboxylic acids.")
            sa_score += 0.5
            
        # 3. Hydroxyls
        hydroxyl = Chem.MolFromSmarts('[OX2H]')
        if mol.HasSubstructMatch(hydroxyl):
            analysis.append("Exposed hydroxyl group identified. May require temporary protection (e.g., TBS or Boc) depending on upstream synthetic sequence, mildly decreasing total yield.")
            sa_score += 1.0
            
        # 4. Complexity
        rings = mol.GetRingInfo().NumRings()
        if rings > 3:
            analysis.append(f"High ring complexity ({rings} rings). Proceed with convergent synthesis strategy to minimize late-stage loss of yield.")
            sa_score += (rings - 3) * 0.8
            
        if not analysis:
            analysis.append("Structure is relatively simple aliphatic/aromatic scaffold. Standard commercial building blocks can be assembled via single-step nucleophilic substitutions.")
            
        analysis.append(f"Synthetic Accessibility Score: {round(sa_score, 1)} (Highly realizable).")
        
        return {
            "sa_score": round(sa_score, 1),
            "analysis": " ".join(analysis)
        }
