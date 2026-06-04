import * as api from './api.js';

export class PocketOverlay {
  constructor(viewer, listContainer) {
    this.viewer = viewer;
    this.listContainer = listContainer;
    
    // Listen for real-time affinity updates from viewer3d.js
    window.addEventListener('binding-affinity-update', (e) => {
      if (!this.viewer.activePocket) return;
      const resultDiv = document.getElementById(`dock-result-${this.viewer.activePocket.pocket_id}`);
      if (resultDiv) {
        const { dgTotal, clashes } = e.detail;
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `<strong>Predicted Affinity:</strong> ${dgTotal.toFixed(1)} kcal/mol <br/> Clashes: ${clashes}`;
        
        if (dgTotal <= -6.0) {
          resultDiv.style.color = 'var(--accent-teal)';
          resultDiv.style.textShadow = '0 0 5px var(--accent-teal)';
        } else if (dgTotal > 0) {
          resultDiv.style.color = 'var(--accent-red)';
          resultDiv.style.textShadow = '0 0 5px var(--accent-red)';
        } else {
          resultDiv.style.color = 'var(--text-primary)';
          resultDiv.style.textShadow = 'none';
        }
      }
    });
  }

  displayResults(analysisResult) {
    this.listContainer.innerHTML = '';
    const allPockets = [
      ...analysisResult.cryptic_pockets,
      ...analysisResult.constitutive_pockets,
      ...analysisResult.rare_pockets
    ];
    
    if (allPockets.length === 0) {
      this.listContainer.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No pockets found.</div>';
      return;
    }
    
    // Sort by peak druggability descending
    allPockets.sort((a, b) => b.peak_druggability - a.peak_druggability);
    
    allPockets.forEach(pocket => {
      const card = document.createElement('div');
      card.className = 'pocket-card';
      card.id = `pocket-card-${pocket.pocket_id}`;
      
      const probPct = Math.round(pocket.opening_probability * 100);
      const isCryptic = pocket.classification === 'cryptic';
      
      // Build sparkline
      const sparklineHtml = pocket.presence_vector.map(val => {
        const height = Math.max(2, val * 100); // % height
        return `<div style="flex:1; background:var(--accent-teal); opacity:${val}; height:${height}%"></div>`;
      }).join('');
      
      card.innerHTML = `
        <div class="pocket-header">
          <span>Pocket #${pocket.pocket_id}</span>
          <span class="badge ${pocket.classification}">${pocket.classification}</span>
        </div>
        <div class="pocket-stat">
          <span>Max Druggability</span>
          <span>${pocket.peak_druggability.toFixed(2)}</span>
        </div>
        <div class="stat-bar-wrap">
          <div class="stat-bar ${pocket.classification}" style="width: ${Math.min(100, pocket.peak_druggability * 100)}%"></div>
        </div>
        <div class="pocket-stat">
          <span>Open frames</span>
          <span>${probPct}%</span>
        </div>
        <div style="height:20px; display:flex; align-items:flex-end; gap:1px; margin: 8px 0; background:rgba(0,0,0,0.2); padding:2px;">
          ${sparklineHtml}
        </div>
        <div class="pocket-stat">
          <span>Lining Residues</span>
          <span>${pocket.lining_residues.length}</span>
        </div>
        <div style="margin-top:8px; display:flex; gap:4px; flex-direction:column;">
          <input type="text" class="smiles-input" id="smiles-${pocket.pocket_id}" placeholder="Enter SMILES to dock" style="padding:4px; background:var(--bg-primary); border:1px solid var(--border); color:var(--text-primary); border-radius:var(--radius-sm); font-family:var(--font-mono); font-size:0.75rem;" />
          <div style="display: flex; gap: 8px; margin-top: 8px;">
            <button id="dock-btn-${pocket.pocket_id}" class="action-btn">Dock</button>
            <button id="optimize-btn-${pocket.pocket_id}" class="action-btn" style="background: var(--accent-amber); color: black;">Optimize</button>
          </div>
          <button id="dream-btn-${pocket.pocket_id}" class="action-btn" style="margin-top: 8px; background: var(--accent-teal); color: black; font-weight: bold; width: 100%;">✨ Auto-Design Ligand</button>
          <div id="dock-result-${pocket.pocket_id}" style="margin-top: 8px; font-size: 0.85rem; display: none;"></div>
          <div id="dream-badge-${pocket.pocket_id}" style="margin-top: 4px; font-size: 0.8rem; color: var(--accent-teal); font-weight: bold; display: none;">✅ Target Druggability & Safety Verified</div>
          
          <div id="flex-panels-${pocket.pocket_id}" style="display: none; flex-direction: column; gap: 8px; margin-top: 12px;">
            <div style="background: var(--bg-tertiary); padding: 8px; border-radius: var(--radius-sm); border: 1px solid var(--border);">
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;">Selectivity Index (Target vs. hERG)</div>
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="height: 6px; flex: 1; background: linear-gradient(90deg, var(--accent-red), var(--accent-teal)); border-radius: 3px; position: relative;">
                  <div id="sel-marker-${pocket.pocket_id}" style="position: absolute; top: -3px; left: 50%; width: 4px; height: 12px; background: white; border-radius: 2px;"></div>
                </div>
                <div id="sel-score-${pocket.pocket_id}" style="font-size: 0.9rem; font-weight: bold; margin-left: 8px; color: var(--accent-teal);">9.5</div>
              </div>
            </div>
            
            <div style="background: #1e1e1e; padding: 8px; border-radius: var(--radius-sm); border: 1px solid #333; font-family: monospace; position: relative;">
              <div style="font-size: 0.65rem; color: #888; margin-bottom: 4px;">Bio-LLM Agent | Synthetic Accessibility</div>
              <div id="llm-stream-${pocket.pocket_id}" style="font-size: 0.75rem; color: #0f0; line-height: 1.4; min-height: 40px;"></div>
            </div>
          </div>

          <button class="btn-small show-pocket-btn" data-id="${pocket.pocket_id}" data-frame="${pocket.representative_frame}" style="margin-top: 8px; width: 100%;">View</button>
        </div>
      `;
      
      this.listContainer.appendChild(card);
    });
    
    // Bind buttons
    allPockets.forEach(pocket => {
      const pocketId = pocket.pocket_id;
      const frameIdx = pocket.representative_frame;
      
      const showBtn = document.querySelector(`.show-pocket-btn[data-id="${pocketId}"]`);
      if (showBtn) {
        showBtn.addEventListener('click', () => {
          this.listContainer.querySelectorAll('.pocket-card').forEach(c => c.classList.remove('highlighted'));
          const card = document.getElementById(`pocket-card-${pocketId}`);
          if (card) {
            card.classList.add('highlighted');
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }
          this.highlightPocket(pocketId, frameIdx, allPockets);
        });
      }
      
      const input = document.getElementById(`smiles-${pocketId}`);
      const resultDiv = document.getElementById(`dock-result-${pocketId}`);
      
      const dockBtn = document.getElementById(`dock-btn-${pocketId}`);
      if (dockBtn) {
        dockBtn.addEventListener('click', async () => {
          if (!input.value.trim()) return;
          dockBtn.textContent = '...';
          dockBtn.disabled = true;
          try {
            const res = await api.dockLigand(window.state.jobId, pocketId, parseInt(window.state.currentFrameIdx), input.value.trim());
            this.viewer.drawLigand(res.ligand, { rotatableBonds: res.rotatable_bonds, pocketId: pocketId });
          } catch(err) {
            resultDiv.style.display = 'block';
            resultDiv.style.color = 'var(--accent-red)';
            resultDiv.textContent = err.message;
          } finally {
            dockBtn.textContent = 'Dock';
            dockBtn.disabled = false;
          }
        });
      }
      
      const optBtn = document.getElementById(`optimize-btn-${pocketId}`);
      if (optBtn) {
        optBtn.addEventListener('click', async () => {
          if (!input.value.trim()) return;
          optBtn.textContent = '...';
          optBtn.disabled = true;
          try {
            const res = await api.optimizePose(window.state.jobId, pocketId, parseInt(window.state.currentFrameIdx), input.value.trim());
            this.viewer.drawLigand(res.ligand, { rotatableBonds: res.rotatable_bonds, pocketId: pocketId });
          } catch(err) {
            resultDiv.style.display = 'block';
            resultDiv.style.color = 'var(--accent-red)';
            resultDiv.textContent = err.message;
          } finally {
            optBtn.textContent = 'Optimize';
            optBtn.disabled = false;
          }
        });
      }
      
      const dreamBtn = document.getElementById(`dream-btn-${pocketId}`);
      const dreamBadge = document.getElementById(`dream-badge-${pocketId}`);
      const flexPanels = document.getElementById(`flex-panels-${pocketId}`);
      const selMarker = document.getElementById(`sel-marker-${pocketId}`);
      const selScore = document.getElementById(`sel-score-${pocketId}`);
      const llmStream = document.getElementById(`llm-stream-${pocketId}`);
      
      if (dreamBtn) {
        dreamBtn.addEventListener('click', async () => {
          const frame = parseInt(window.state.currentFrameIdx);
          if (isNaN(frame) || !window.state.jobId) return;
          
          dreamBtn.disabled = true;
          dreamBtn.textContent = 'Agentic Genesis Loop Running...';
          resultDiv.style.display = 'none';
          dreamBadge.style.display = 'none';
          if(flexPanels) flexPanels.style.display = 'none';
          
          try {
            const res = await api.autoDesign(window.state.jobId, pocketId, frame);
            input.value = res.smiles;
            this.viewer.drawLigand(res.ligand, { rotatableBonds: res.rotatable_bonds, pocketId: pocketId });
            dreamBadge.style.display = 'block';
            
            if(flexPanels) {
              flexPanels.style.display = 'flex';
              
              // Selectivity Index Gauge
              const sel = res.selectivity_index || 0;
              selScore.textContent = sel.toFixed(1);
              // clamp sel between 0 and 10 to place marker (0=left, 10=right)
              const pct = Math.max(0, Math.min(100, (sel / 10.0) * 100));
              selMarker.style.left = `${pct}%`;
              if (sel > 5) {
                selScore.style.color = 'var(--accent-teal)';
              } else {
                selScore.style.color = 'var(--accent-red)';
              }
              
              // LLM Streaming Effect
              llmStream.textContent = '';
              const analysisText = res.synthesis ? res.synthesis.analysis : 'Analysis unavailable.';
              let i = 0;
              const typeWriter = setInterval(() => {
                llmStream.textContent += analysisText.charAt(i);
                i++;
                if (i >= analysisText.length) {
                  clearInterval(typeWriter);
                }
              }, 15);
            }
          } catch(err) {
            resultDiv.style.display = 'block';
            resultDiv.style.color = 'var(--accent-red)';
            resultDiv.textContent = err.message;
          } finally {
            dreamBtn.disabled = false;
            dreamBtn.textContent = '✨ Auto-Design Ligand';
          }
        });
      }
    });
    
    // Tell viewer to show all pockets initially
    this.viewer.showPockets(allPockets, window.state.proteinGraph ? window.state.proteinGraph.sequence : '');
  }
  
  async highlightPocket(pocketId, representativeFrame, allPockets) {
    window.state.selectedPocketId = pocketId;
    
    // Jump to frame
    window.dispatchEvent(new CustomEvent('jump-to-frame', { detail: { frame: representativeFrame } }));
    
    this.viewer.highlightPocket(pocketId);
    
    const pocket = allPockets.find(p => p.pocket_id === pocketId);
    if (!pocket) return;
    
    try {
      const allostery = await api.getAllostery(window.state.jobId, pocketId);
      this.viewer.drawAllostericWebs(allostery.webs, pocket.centroid);
    } catch(e) {
      console.error('Allostery fetch failed', e);
    }
  }
  
  clearAll() {
    this.listContainer.innerHTML = '';
    this.viewer.hidePockets();
    this.viewer.clearAllostery();
    this.viewer.clearLigand();
  }
}
