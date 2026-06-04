<div align="center">
  
# 🧬 KinetiX

**Zero-Latency Generative Cryptic Pocket & Allosteric Perturbation Engine**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com/)
[![Three.js](https://img.shields.io/badge/WebGL-Three.js-black.svg)](https://threejs.org/)
[![RDKit](https://img.shields.io/badge/RDKit-Cheminformatics-orange.svg)](https://www.rdkit.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14.0-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*An advanced computational biology platform engineered by **PixelForge Studio**.*

</div>

---

## 🔬 The Paradigm Shift

Legacy molecular dynamics (MD) and docking pipelines are crippled by massive trajectory files, slow desktop-bound CPU clusters, and decoupled chemistry software. 

**KinetiX** bridges the gap between static structural data and active drug design. By combining generative flow-matching ensembles with an active, client-side biophysics pipeline, the platform maps latent conformational landscapes, uncovers transient cryptic pockets, and **autonomously designs biochemically viable small molecules** completely in the browser at a locked 60 FPS.

[![To Try KinetiX Demo](https://img.shields.io/badge/Live-Demo-00a393?style=for-the-badge)](https://huggingface.co/spaces/BalajiM020504/kinetix-generative-flow)

---

## 🧬 Scientific Methodology

KinetiX does not just visualize data; it computes biophysical realities in real-time utilizing a hybrid edge-compute architecture.

### 1. Latent Conformational Mapping (PCA)
Instead of forcing researchers to manually scrub through thousands of frames, KinetiX flattens the multidimensional state-space of the protein target. 
* High-dimensional Alpha-Carbon ($C\alpha$) coordinates are projected into a 2D interactive manifold using **Principal Component Analysis (PCA)**. 
* Bidirectional event-listeners allow the user to click a cluster of states (e.g., a rare "open pocket" conformation) on the 2D map, instantly snapping the 3D WebGL viewer to that exact physical frame.

### 2. Client-Side Empirical Physics ($\Delta G$)
KinetiX implements an AutoDock Vina-inspired empirical scoring function that executes natively in the V8 JavaScript engine. As the user scrubs the temporal timeline, KinetiX calculates pairwise heavy-atom distances across the pocket environment.
The binding free energy is approximated dynamically:
$$\Delta G = \Delta G_{hydrophobic} + \Delta G_{hbond} + \Delta G_{clash} + \Delta G_{entropy}$$
* **H-Bonds:** Proximity ($\le 4.0\text{ \AA}$) between ligand heteroatoms and receptor donor/acceptors (mapped via the Pharmacophore Cloud).
* **Steric Penalty:** Exponential decay penalty for any atom pairs $< 2.5\text{ \AA}$.
* **Entropy:** Rigid-body and rotatable-bond penalty derived from RDKit topological parsing.

### 3. The "Genesis" Loop (De Novo Agent)
The Genesis Loop is an autonomous RDKit-driven Genetic Algorithm (GA) that invents novel chemical matter:
* **Generative Seed:** Initializes a stable molecular scaffold (e.g., Pyrimidine) within the pocket centroid.
* **Mutation Engine:** Applies stochastic SMARTS transformations (e.g., `[c:1][H]>>[c:1]O` for targeted hydroxylation) across 50 generations to optimize for the exact local $\Delta G$ minima.
* **ADMET Heuristic Filter:** Silently culls any generated structure that violates Lipinski's Rule of 5 or triggers toxicophore structural alerts (e.g., Michael Acceptors), guaranteeing that the output is synthetically viable and safe.

---

## 📚 Comprehensive Tutorial

### Phase 1: Ingestion & Allosteric Mapping
1. **Load Target:** Initialize the workspace by uploading a PDB target or selecting a simulated ensemble.
2. **Cryptic Pocket Hunt:** Click **[ Run Analysis ]**. The engine will scan the ensemble for transient cavities, highlighting the most druggable pocket with a translucent Pharmacophore Cloud (Red = Acceptors, Blue = Donors, Yellow = Hydrophobic).
3. **Trace Allostery:** Select a pocket to generate dynamic Bezier-curve splines, visually tracing the Dynamic Cross-Correlation (DCCM) pathways to distant protein regions.

### Phase 2: Perturbation & Auto-Relax
1. **SMILES Docking:** Input a known drug (e.g., Imatinib: `Cc1ccc(NC(=O)...`) into the Perturbation UI and hit **[ Dock ]**.
2. **Timeline Scrubbing:** Drag the bottom slider to animate the protein. Watch the atoms glow neon red in real-time as the protein structure tightens and clashes with the drug.
3. **MMFF94 Auto-Relax:** Click **[ Optimize Pose ]**. KinetiX pings the backend to run a localized Merck Molecular Force Field (MMFF94) relaxation, snapping the drug into the lowest-energy conformer for that specific frame.

### Phase 3: Autonomous Discovery (Dream Mode)
1. **Trigger Genesis:** If a pocket is "undruggable" with known compounds, click the glowing **[ Auto-Design Ligand ]** button.
2. **Observe:** The UI will display the generative stream as the agent iterates through structural mutations. 
3. **Review:** The finalized, fully optimized de novo molecule drops into the viewer with a `Target Druggability & Safety Verified` badge.
4. **Audit Export:** Click **[ Export Target Report ]** to generate a deterministic JSON snapshot containing the frame coordinates, SMILES payload, and $\Delta G$ breakdown for external validation.

---

## ⚙️ Systems Topology & API Reference

KinetiX utilizes a strict decoupling of intense cheminformatics (Python) and high-FPS rendering (JavaScript).

```mermaid
graph TD
    subgraph Frontend [Next.js / Three.js WebGL Client]
        UI[Aerogel UI & State Manager]
        R1[60 FPS Distance Matrix Loop]
        R2[SSAO + UnrealBloom Render Pass]
        UI -->|Scrub Timeline| R1
        R1 -->|Update| R2
    end

    subgraph Backend [FastAPI / Python Inference]
        API[Async API Router]
        P1[PCA Latent Mapper]
        P2[RDKit MMFF94 Relax Engine]
        
        subgraph Genesis [De Novo Genesis Loop]
            GA[SMARTS Genetic Algorithm]
            ADMET[Heuristic ADMET / Tox Filter]
            GA <--> ADMET
        end
    end

    UI <-->|JSON / SSE Streams| API
    API --> P1
    API --> P2
    API --> Genesis
