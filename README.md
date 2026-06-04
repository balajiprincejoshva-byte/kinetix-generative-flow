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

![KinetiX Demo Placeholder](https://via.placeholder.com/1000x500.png?text=Drop+Your+Loom+or+GIF+Demo+Here)

---

## 🚀 God-Tier Architecture & Features

* **Generative Conformational Flow-Matching:** Accelerates state-space exploration by mapping 3D structural trajectories natively without heavy desktop clusters or gigabyte-sized trajectory downloads.
* **Autonomous De Novo "Genesis" Loop:** An active RDKit-driven genetic algorithm that targets discovered cryptic pocket centroids, mutating drug scaffolds using parameterized SMARTS transformations.
* **Real-Time Empirical Physics & $\Delta G$ Scoring:** Computes pairwise atomic interactions at 60 FPS to dynamically output a binding free energy estimation ($\Delta G = \Delta G_{hydrophobic} + \Delta G_{hbond} + \Delta G_{clash} + \Delta G_{entropy}$) while scrubbing the structural timeline.
* **Biophysical & ADMET Safety Filters:** Enforces structural integrity via localized all-atom MMFF94 force-field relaxation, simultaneously filtering out toxicophores and Lipinski Rule-of-5 violations before compound delivery.
* **Latent Energy Landscape Mapping:** Projects high-dimensional protein coordinates into a 2D interactive PCA manifold, featuring bidirectional frame-snapping for real-time conformational analysis.
* **Cinematic WebGL GPU Overdrive:** Custom shader architecture utilizing Screen-Space Ambient Occlusion (SSAO) for deep structural folds, UnrealBloom post-processing for neon pharmacophore clouds, and glowing quadratic Bezier curves for allosteric communication webs.

---

## ⚙️ Systems Topology

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
