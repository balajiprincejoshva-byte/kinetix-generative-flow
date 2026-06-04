const BASE = 'http://localhost:8000';

export async function uploadPDB(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${BASE}/api/upload_pdb`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }
  
  return response.json();
}

export function connectEnsembleStream(jobId, onChunk, onComplete, onError) {
  const wsUrl = `ws://${window.location.host}/api/ws/${jobId}/stream_ensemble`;
  const ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    try {
      const chunk = JSON.parse(event.data);
      onChunk(chunk);
      if (chunk.is_final) {
        onComplete();
        ws.close();
      }
    } catch (e) {
      console.error("Failed to parse chunk", e);
    }
  };
  
  ws.onerror = (error) => {
    onError(error);
  };
  
  ws.onclose = (event) => {
    if (event.code !== 1000 && event.code !== 1005) {
      // Not a normal closure
      onError(new Error(`WebSocket closed unexpectedly: ${event.code}`));
    }
  };
  
  return ws;
}

export async function analyzePockets(jobId) {
  const response = await fetch(`${BASE}/api/jobs/${jobId}/analyze_pockets`, {
    method: 'POST'
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Analysis failed');
  }
  
  return response.json();
}

export async function getAllostery(jobId, pocketId) {
  const response = await fetch(`${BASE}/api/jobs/${jobId}/allostery/${pocketId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch allostery data');
  }
  return response.json();
}

export async function getHealth() {
  const response = await fetch(`${BASE}/api/health`);
  if (!response.ok) throw new Error('Backend offline');
  return response.json();
}

export async function dockLigand(jobId, pocketId, frameId, smiles) {
  const res = await fetch(`/api/jobs/${jobId}/dock`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ smiles, pocket_id: pocketId, frame_id: frameId })
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Docking failed');
  }
  return await res.json();
}

export async function optimizePose(jobId, pocketId, frameId, smiles) {
  const res = await fetch(`/api/jobs/${jobId}/optimize_pose`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ smiles, pocket_id: pocketId, frame_id: frameId })
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Pose optimization failed');
  }
  return await res.json();
}

export async function autoDesign(jobId, pocketId, frameId) {
  const res = await fetch(`/api/jobs/${jobId}/dream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pocket_id: pocketId,
      frame_idx: frameId
    })
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Auto design failed');
  }
  return await res.json();
}
