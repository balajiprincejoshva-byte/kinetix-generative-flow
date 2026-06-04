export class LatentMap {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    
    // State
    this.data = []; // {frame, pc1, pc2, rmsd}
    this.bounds = { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    this.hoveredFrame = -1;
    this.activeFrame = 0;
    
    // Bind events
    this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
    this.canvas.addEventListener('mouseleave', this.onMouseLeave.bind(this));
    this.canvas.addEventListener('click', this.onClick.bind(this));
    
    // Listen to global frame jumps
    window.addEventListener('jump-to-frame', (e) => {
      this.activeFrame = e.detail.frame;
      this.draw();
    });
  }
  
  setData(landscapeData) {
    if (!landscapeData || !landscapeData.length) return;
    this.data = landscapeData;
    
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    
    this.data.forEach(d => {
      if (d.pc1 < minX) minX = d.pc1;
      if (d.pc1 > maxX) maxX = d.pc1;
      if (d.pc2 < minY) minY = d.pc2;
      if (d.pc2 > maxY) maxY = d.pc2;
    });
    
    // Add padding
    const dx = maxX - minX;
    const dy = maxY - minY;
    this.bounds = {
      minX: minX - dx * 0.1,
      maxX: maxX + dx * 0.1,
      minY: minY - dy * 0.1,
      maxY: maxY + dy * 0.1
    };
    
    this.draw();
  }
  
  toScreen(pc1, pc2) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    
    const x = ((pc1 - this.bounds.minX) / (this.bounds.maxX - this.bounds.minX)) * w;
    const y = h - ((pc2 - this.bounds.minY) / (this.bounds.maxY - this.bounds.minY)) * h;
    
    return { x, y };
  }
  
  getHoveredNode(mouseX, mouseY) {
    if (!this.data.length) return -1;
    
    let closestFrame = -1;
    let minDist = 10; // 10px radius
    
    this.data.forEach(d => {
      const { x, y } = this.toScreen(d.pc1, d.pc2);
      const dist = Math.sqrt((mouseX - x)**2 + (mouseY - y)**2);
      if (dist < minDist) {
        minDist = dist;
        closestFrame = d.frame;
      }
    });
    
    return closestFrame;
  }
  
  onMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const scaleX = this.canvas.width / rect.width;
    const scaleY = this.canvas.height / rect.height;
    
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    const hFrame = this.getHoveredNode(x, y);
    if (hFrame !== this.hoveredFrame) {
      this.hoveredFrame = hFrame;
      this.draw();
    }
  }
  
  onMouseLeave() {
    if (this.hoveredFrame !== -1) {
      this.hoveredFrame = -1;
      this.draw();
    }
  }
  
  onClick(e) {
    if (this.hoveredFrame !== -1) {
      this.activeFrame = this.hoveredFrame;
      window.dispatchEvent(new CustomEvent('jump-to-frame', { detail: { frame: this.hoveredFrame } }));
      this.draw();
    }
  }
  
  draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ctx = this.ctx;
    
    ctx.clearRect(0, 0, w, h);
    
    if (!this.data.length) return;
    
    // Draw edges connecting consecutive frames? (Optional, creates a path)
    ctx.beginPath();
    this.data.forEach((d, i) => {
      const { x, y } = this.toScreen(d.pc1, d.pc2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = 'rgba(122, 154, 184, 0.2)'; // text-muted
    ctx.lineWidth = 1;
    ctx.stroke();
    
    // Draw points
    this.data.forEach(d => {
      const { x, y } = this.toScreen(d.pc1, d.pc2);
      
      const isHovered = d.frame === this.hoveredFrame;
      const isActive = d.frame === this.activeFrame;
      
      ctx.beginPath();
      ctx.arc(x, y, isActive ? 5 : (isHovered ? 4 : 2.5), 0, Math.PI * 2);
      
      // Color by RMSD (e.g. low=teal, high=red)
      // We can use HSL: H=166 (teal) -> H=0 (red) based on RMSD / 5.0
      const maxRmsd = 5.0; 
      const normRmsd = Math.min(1.0, d.rmsd / maxRmsd);
      const hue = 166 - (166 * normRmsd);
      
      ctx.fillStyle = isActive ? '#ffffff' : `hsl(${hue}, 80%, 50%)`;
      ctx.fill();
      
      if (isActive) {
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });
    
    // Draw tooltip if hovered
    if (this.hoveredFrame !== -1) {
      const d = this.data[this.hoveredFrame];
      const { x, y } = this.toScreen(d.pc1, d.pc2);
      
      ctx.fillStyle = 'var(--bg-panel)';
      ctx.fillRect(x + 10, y - 25, 90, 20);
      ctx.strokeStyle = 'var(--border)';
      ctx.strokeRect(x + 10, y - 25, 90, 20);
      
      ctx.fillStyle = 'var(--text-primary)';
      ctx.font = '10px var(--font-mono)';
      ctx.fillText(`F:${d.frame} R:${d.rmsd.toFixed(1)}`, x + 15, y - 11);
    }
  }
}
