export function bindUIControls({ player, overlay, viewer, api, latentMap }) {
  // Upload panel
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('pdb-input');
  
  dropZone.addEventListener('click', () => fileInput.click());
  
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  
  dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
  });
  
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      window.handlePDBUpload(e.dataTransfer.files[0]);
    }
  });
  
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      window.handlePDBUpload(e.target.files[0]);
    }
  });
  
  // Sample button
  document.getElementById('load-sample-btn').addEventListener('click', async () => {
    try {
      window.showLoading('Downloading sample...');
      const response = await fetch('/assets/sample.pdb');
      if (!response.ok) throw new Error('Sample not found');
      const blob = await response.blob();
      const file = new File([blob], "1UBQ.pdb", { type: "chemical/x-pdb" });
      window.handlePDBUpload(file);
    } catch(e) {
      window.hideLoading();
      window.showError(e.message);
    }
  });
  
  // Export button
  document.getElementById('export-btn').addEventListener('click', () => {
    if (!window.state || !window.state.jobId) {
      window.showError("No active job to export.");
      return;
    }
    
    const exportData = {
      timestamp: new Date().toISOString(),
      jobId: window.state.jobId,
      currentFrameIdx: player.currentFrameIdx,
      pocketResults: window.state.pocketResults
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kinetix_audit_trail_${window.state.jobId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });
  
  // Share button
  document.getElementById('share-btn').addEventListener('click', () => {
    if (!window.state || !window.state.jobId) {
      window.showError("No active job to share.");
      return;
    }
    const url = new URL(window.location.origin + window.location.pathname);
    url.searchParams.set('sample', '1UBQ');
    url.searchParams.set('frame', player.currentFrameIdx);
    
    if (window.state.selectedPocketId !== undefined) {
      url.searchParams.set('pocket', window.state.selectedPocketId);
      const input = document.getElementById(`smiles-${window.state.selectedPocketId}`);
      if (input && input.value.trim()) {
        url.searchParams.set('ligand', input.value.trim());
      }
    }
    
    navigator.clipboard.writeText(url.toString()).then(() => {
      window.showError("Share URL copied to clipboard!"); // using showError as a toast notification
    });
  });
  
  // Playback controls
  document.getElementById('play-btn').addEventListener('click', () => player.play());
  document.getElementById('pause-btn').addEventListener('click', () => player.pause());
  document.getElementById('rewind-btn').addEventListener('click', () => player.goToFrame(0));
  
  // Frame slider
  const slider = document.getElementById('frame-slider');
  slider.addEventListener('input', e => player.goToFrame(parseInt(e.target.value)));
  
  // Speed slider
  document.getElementById('speed-slider').addEventListener('input', e => player.setSpeed(parseInt(e.target.value)));
  
  // Pocket hunter button
  document.getElementById('hunt-pockets-btn').addEventListener('click', async () => {
    if (!window.state || !window.state.jobId) return;
    
    try {
      window.showLoading('Hunting cryptic pockets...');
      const result = await api.analyzePockets(window.state.jobId);
      window.state.pocketResults = result;
      overlay.displayResults(result);
      if (result.latent_landscape) {
        latentMap.setData(result.latent_landscape);
        window.showPanel('latent-panel');
      }
      window.hideLoading();
    } catch(e) {
      window.hideLoading();
      window.showError(e.message);
    }
  });
  
  // Viewer toolbar
  const toggleBtn = (id, action) => {
    const btn = document.getElementById(id);
    btn.addEventListener('click', () => {
      const isActive = btn.classList.toggle('active');
      action(isActive);
    });
  };
  
  // Default backbone is active
  document.getElementById('toggle-backbone').classList.add('active');
  
  toggleBtn('toggle-backbone', (val) => viewer.toggleBackbone(val));
  toggleBtn('toggle-sidechains', (val) => viewer.toggleSidechains(val));
  toggleBtn('toggle-surface', (val) => viewer.toggleSurface(val));
  
  document.getElementById('reset-camera').addEventListener('click', () => viewer.resetCamera());
  
  // Listen for jump-to-frame from pocket overlay
  window.addEventListener('jump-to-frame', (e) => {
    player.pause();
    player.goToFrame(e.detail.frame);
  });
}
