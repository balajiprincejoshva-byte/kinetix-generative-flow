import { ProteinViewer } from './viewer3d.js';
import { EnsemblePlayer } from './ensemble_player.js';
import { PocketOverlay } from './pocket_overlay.js';
import { bindUIControls } from './ui_controls.js';
import { LatentMap } from './latent_map.js';
import * as api from './api.js';

// Global state
window.state = {
  jobId: null,
  proteinGraph: null,
  frames: [],
  pocketResults: null,
  ws: null,
};

async function init() {
  // Check backend health
  try {
    const health = await api.getHealth();
    if (!health) throw new Error("Offline");
  } catch (e) {
    document.getElementById('status-indicator').textContent = '⚠ Backend offline';
    document.getElementById('status-indicator').classList.add('error');
  }

  const canvas = document.getElementById('mol-canvas');
  const viewer = new ProteinViewer(canvas);

  const player = new EnsemblePlayer(viewer, (frame) => {
    // Update all UI elements on frame change
    document.getElementById('frame-slider').value = frame.frame_id;
    document.getElementById('frame-display').textContent = frame.frame_id;
    document.getElementById('rmsd-display').textContent = frame.rmsd_from_input.toFixed(2);
    document.getElementById('badge-frame').textContent = frame.frame_id;
    document.getElementById('badge-rmsd').textContent = frame.rmsd_from_input.toFixed(2);
  });

  const overlay = new PocketOverlay(viewer, document.getElementById('pocket-list'));
  const latentMap = new LatentMap('latent-canvas');

  bindUIControls({ player, overlay, viewer, api, latentMap });

  // Global upload handler — called by ui_controls when file is ready
  window.handlePDBUpload = async (file) => {
    window.showLoading('Parsing PDB...');
    
    try {
      const uploadResult = await api.uploadPDB(file);
      window.state.jobId = uploadResult.job_id;
      window.state.frames = [];
      window.state.pocketResults = null;
      if (window.state.ws) window.state.ws.close();
      
      overlay.clearAll();
      player.pause();
      player.frames = [];
      player.currentFrameIdx = 0;

      // Show protein info
      document.getElementById('protein-info-grid').innerHTML = `
        <div class="info-item"><span>Residues</span><span>${uploadResult.n_residues}</span></div>
        <div class="info-item"><span>Sequence</span><span class="mono">${uploadResult.sequence.substring(0, 20)}…</span></div>
      `;
      window.showPanel('protein-info-panel');

      // Start ensemble streaming
      window.updateLoading('Running Flow-Matching inference...');
      window.showPanel('ensemble-panel');
      document.getElementById('frame-badge').classList.remove('hidden');

      window.state.ws = api.connectEnsembleStream(
        window.state.jobId,
        (chunk) => {
          player.addFrames(chunk.frames);
          window.state.frames.push(...chunk.frames);
          window.updateProgress(chunk.total_generated, 100);
          document.getElementById('frame-counter').textContent = `${chunk.total_generated} / 100 frames`;
          document.getElementById('frame-slider').max = Math.max(0, chunk.total_generated - 1);
        },
        () => {
          window.hideLoading();
          window.showPanel('pocket-panel');
          document.getElementById('status-indicator').textContent = `✓ ${window.state.frames.length} conformations ready`;
          document.getElementById('status-indicator').classList.remove('error');
          
          const params = new URLSearchParams(window.location.search);
          if (params.has('pocket')) {
            setTimeout(() => {
              document.getElementById('hunt-pockets-btn').click();
              
              const checkInterval = setInterval(() => {
                if (window.state.pocketResults) {
                  clearInterval(checkInterval);
                  const pocketId = parseInt(params.get('pocket'));
                  
                  // highlight
                  const viewBtn = document.querySelector(`.show-pocket-btn[data-id="${pocketId}"]`);
                  if (viewBtn) viewBtn.click();
                  
                  if (params.has('frame')) {
                    player.goToFrame(parseInt(params.get('frame')));
                  }
                  
                  if (params.has('ligand')) {
                    const smilesInput = document.getElementById(`smiles-${pocketId}`);
                    const dockBtn = document.querySelector(`.dock-btn[data-id="${pocketId}"]`);
                    if (smilesInput && dockBtn) {
                      smilesInput.value = params.get('ligand');
                      dockBtn.click();
                    }
                  }
                }
              }, 500);
            }, 500);
          }
        },
        (err) => {
          window.hideLoading();
          window.showError(`Stream error: ${err.message}`);
          console.error('Stream error:', err);
        }
      );
    } catch (e) {
      window.hideLoading();
      window.showError(e.message);
    }
  };
}

// Global UI helpers
window.showLoading = (text) => {
  document.getElementById('loading-overlay').classList.remove('hidden');
  document.getElementById('loading-text').textContent = text;
};

window.updateLoading = (text) => {
  document.getElementById('loading-text').textContent = text;
};

window.hideLoading = () => {
  document.getElementById('loading-overlay').classList.add('hidden');
};

window.updateProgress = (current, total) => {
  const pct = (current / total) * 100;
  document.getElementById('gen-progress').style.width = `${pct}%`;
};

window.showPanel = (id) => {
  document.getElementById(id).classList.remove('hidden');
};

window.showError = (message) => {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => {
      if(toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 4000);
};

init();

// Auto-trigger flow from URL params
setTimeout(() => {
  const params = new URLSearchParams(window.location.search);
  if (params.has('sample')) {
    const btn = document.getElementById('load-sample-btn');
    if (btn) btn.click();
  }
}, 500);
