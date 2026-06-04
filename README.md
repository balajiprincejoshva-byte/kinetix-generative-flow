# KinetiX
**"AlphaFold for Movies, not Pictures"**

KinetiX is a generative flow-matching model that predicts millisecond-scale protein dynamics and identifies cryptic pockets that are invisible in static AlphaFold snapshots.

## Architecture Overview

```text
       ┌───────────┐       ┌──────────────┐       ┌──────────────┐
PDB ──►│ PDB Parser├──────►│ Flow-Matching├───┬──►│ Cryptic      │
File   │ (BioPython)│       │ Generative   │   │   │ Pocket Hunter│
       └───────────┘       │ Model (OT-CFM│   │   └────────┬─────┘
                           └──────────────┘   │            │
                                              │            ▼
                                              │   ┌────────────────┐
                                              └──►│ Frontend UI    │
                                                  │ (Three.js Web) │
                                                  └────────────────┘
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the backend server:**
   ```bash
   cd kinetics
   uvicorn backend.app:app --reload
   ```

3. **Open the application:**
   Navigate to `http://localhost:8000` in your browser.

## Usage Walkthrough

1. **Upload Structure**: Drag and drop a PDB file into the upload zone, or click **"Load 1UBQ (Demo)"** to run the sample ubiquitin structure.
2. **Conformational Ensemble**: Watch as the flow-matching model generates 100 valid 3D conformations and streams them to the browser.
3. **Cryptic Pocket Hunter**: Once generation is complete, click **"Run Analysis"**. The backend cross-analyzes all 100 frames to find transient binding pockets. Click on a pocket to highlight it in the 3D viewer.

## Technical Notes

- **Optimal Transport Conditional Flow Matching (OT-CFM):** We use continuous-time flow matching to generate valid physical states rather than just noise diffusion.
- **Alpha-Sphere Cavity Detection:** Pockets are identified purely by geometric analysis using Delaunay triangulation and clustering (alpha-spheres).
- **Cryptic Pockets:** These are binding sites that only open up during natural protein motion. By evaluating an ensemble of generated states, we find pockets AlphaFold (which predicts a single static snapshot) misses.
