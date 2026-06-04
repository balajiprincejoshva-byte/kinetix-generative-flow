import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { ConvexGeometry } from 'three/addons/geometries/ConvexGeometry.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { SSAOPass } from 'three/addons/postprocessing/SSAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

export class ProteinViewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.toneMapping = THREE.ReinhardToneMapping;
    
    // Scene setup
    this.scene = new THREE.Scene();
    
    // Camera setup
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    this.camera.position.z = 100;
    
    // Controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    this.scene.add(ambientLight);
    
    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight1.position.set(1, 1, 1);
    this.scene.add(dirLight1);
    
    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
    dirLight2.position.set(-1, -1, -1);
    this.scene.add(dirLight2);
    
    // State
    this.caCoords = [];
    this.targetCoords = [];
    this.isInterpolating = false;
    this.interpolationTime = 0;
    this.interpolationDuration = 150; // ms
    this.lastTime = performance.now();
    
    // Post-processing Composer
    this.composer = new EffectComposer(this.renderer);
    
    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);
    
    const parent = this.canvas.parentElement;
    
    // SSAO for deep shadows
    this.ssaoPass = new SSAOPass(this.scene, this.camera, parent.clientWidth, parent.clientHeight);
    this.ssaoPass.kernelRadius = 0.5;
    this.ssaoPass.minDistance = 0.001;
    this.ssaoPass.maxDistance = 0.1;
    this.composer.addPass(this.ssaoPass);
    
    // Bloom for pockets and allostery
    this.bloomPass = new UnrealBloomPass(new THREE.Vector2(parent.clientWidth, parent.clientHeight), 1.5, 0.4, 0.85);
    this.bloomPass.threshold = 1.0;
    this.bloomPass.strength = 1.5;
    this.bloomPass.radius = 0.5;
    this.composer.addPass(this.bloomPass);
    
    // Render objects
    this.backboneGroup = new THREE.Group();
    this.sidechainGroup = new THREE.Group();
    this.surfaceGroup = new THREE.Group();
    this.pocketsGroup = new THREE.Group();
    this.allosteryGroup = new THREE.Group();
    this.ligandGroup = new THREE.Group();
    
    this.scene.add(this.backboneGroup);
    this.scene.add(this.sidechainGroup);
    this.scene.add(this.surfaceGroup);
    this.scene.add(this.pocketsGroup);
    this.scene.add(this.allosteryGroup);
    this.scene.add(this.ligandGroup);
    
    this.showBackbone = true;
    this.showSidechains = false;
    this.showSurface = false;
    
    this.pocketSpheres = [];
    
    // Handle resize
    window.addEventListener('resize', () => this.resize());
    this.resize();
    
    // Animation loop
    this.renderer.setAnimationLoop((t) => this.animate(t));
  }
  
  resize() {
    const parent = this.canvas.parentElement;
    const width = parent.clientWidth;
    const height = parent.clientHeight;
    this.renderer.setSize(width, height);
    this.composer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }
  
  loadFrame(frameData) {
    if (!frameData || !frameData.ca_coords) return;
    
    // Convert coordinates: scale by 0.1 (A -> nm)
    const newCoords = frameData.ca_coords.map(c => new THREE.Vector3(c[0]*0.1, c[1]*0.1, c[2]*0.1));
    const newBbCoords = frameData.bb_coords ? frameData.bb_coords.map(res => res.map(a => new THREE.Vector3(a[0]*0.1, a[1]*0.1, a[2]*0.1))) : [];
    
    if (this.caCoords.length === 0) {
      this.caCoords = newCoords;
      this.targetCoords = newCoords;
      this.bbCoords = newBbCoords;
      this.targetBbCoords = newBbCoords;
      this._updateGeometry();
      this.computeBindingAffinity();
      this.fitCameraToProtein();
    } else {
      // Start interpolation
      this.targetCoords = newCoords;
      this.targetBbCoords = newBbCoords;
      this.isInterpolating = true;
      this.interpolationTime = 0;
    }
  }
  
  _updateGeometry() {
    // Rebuild all active geometries
    this.backboneGroup.clear();
    this.sidechainGroup.clear();
    this.surfaceGroup.clear();
    
    if (this.caCoords.length < 2) return;
    
    if (this.showBackbone) this._buildBackboneRibbon(this.caCoords);
    if (this.showSidechains) this._buildSideChainSpheres(this.caCoords);
    if (this.showSurface) this._buildSurface(this.caCoords);
  }
  
  _buildBackboneRibbon(coords) {
    const curve = new THREE.CatmullRomCurve3(coords);
    const tubularSegments = coords.length * 4;
    const radialSegments = 8;
    const radius = 0.15;
    
    const geometry = new THREE.TubeGeometry(curve, tubularSegments, radius, radialSegments, false);
    
    // Color by index (blue -> white -> red)
    const colors = [];
    for (let i = 0; i < geometry.attributes.position.count; i++) {
      const u = geometry.parameters.path.getUtoTmapping(i / geometry.attributes.position.count); // rough approximation
      const color = this._colorByIndex(u, 1.0);
      colors.push(color.r, color.g, color.b);
    }
    
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    
    const material = new THREE.MeshPhongMaterial({
      vertexColors: true,
      shininess: 50
    });
    
    const mesh = new THREE.Mesh(geometry, material);
    this.backboneGroup.add(mesh);
  }
  
  _buildSideChainSpheres(coords) {
    const geometry = new THREE.SphereGeometry(0.1, 16, 16);
    
    coords.forEach((coord, i) => {
      // Just using generic color for now since we don't have AA types strictly passed in frame
      const material = new THREE.MeshPhongMaterial({ color: 0x88ccff });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(coord);
      this.sidechainGroup.add(mesh);
    });
  }
  
  _buildSurface(coords) {
    // Simplified SES using ConvexHull
    if (coords.length < 4) return;
    try {
      const geometry = new ConvexGeometry(coords);
      const material = new THREE.MeshPhongMaterial({
        color: 0xdddddd,
        transparent: true,
        opacity: 0.4,
        side: THREE.DoubleSide
      });
      const mesh = new THREE.Mesh(geometry, material);
      this.surfaceGroup.add(mesh);
    } catch(e) {
      console.warn("Convex geometry failed", e);
    }
  }
  
  _colorByIndex(i, total) {
    const t = i / total;
    const color = new THREE.Color();
    // Blue to white to red
    if (t < 0.5) {
      color.lerpColors(new THREE.Color(0x0000ff), new THREE.Color(0xffffff), t * 2);
    } else {
      color.lerpColors(new THREE.Color(0xffffff), new THREE.Color(0xff0000), (t - 0.5) * 2);
    }
    return color;
  }
  
  computeBindingAffinity() {
    if (this.ligandGroup.children.length === 0 || this.caCoords.length === 0) return;
    
    let totalClashes = 0;
    let dgHydrophobic = 0;
    let dgHbond = 0;
    
    const acceptors = new Set(['D', 'E', 'N', 'Q', 'S', 'T', 'Y']);
    const donors = new Set(['K', 'R', 'H', 'N', 'Q', 'S', 'T', 'Y']);
    const hydrophobics = new Set(['V', 'I', 'L', 'F', 'M', 'W', 'C', 'A']);

    let targetResidues = [];
    if (this.activePocket && this.activePocket.lining_residues) {
      targetResidues = this.activePocket.lining_residues;
    } else {
      for(let i=0; i<this.caCoords.length; i++) targetResidues.push(i);
    }

    this.ligandGroup.children.forEach(mesh => {
      let atomHasClash = false;
      const elem = mesh.userData.element;
      const ligX = mesh.position.x;
      const ligY = mesh.position.y;
      const ligZ = mesh.position.z;
      
      for (let i = 0; i < targetResidues.length; i++) {
        const resIdx = targetResidues[i];
        if (resIdx >= this.caCoords.length) continue;
        
        // Use all available backbone atoms (N, CA, C, O) to better approximate sidechain/heavy atom density
        const heavyAtoms = (this.bbCoords && this.bbCoords[resIdx]) ? this.bbCoords[resIdx] : [this.caCoords[resIdx]];
        
        for (let j = 0; j < heavyAtoms.length; j++) {
          const protX = heavyAtoms[j].x;
          const protY = heavyAtoms[j].y;
          const protZ = heavyAtoms[j].z;
          
          const dx = ligX - protX;
          const dy = ligY - protY;
          const dz = ligZ - protZ;
          
          // distance is in nm (scale 0.1). 4.0A = 0.4nm. 0.4^2 = 0.16. 2.5A = 0.25nm. 0.25^2 = 0.0625.
          const distSquared = (dx*dx) + (dy*dy) + (dz*dz);
          
          if (distSquared < 0.0625) { // < 2.5 A
            atomHasClash = true;
            totalClashes += 1;
          }
          
          if (distSquared < 0.16 && elem) { // < 4.0 A
            const aa = this.proteinSequence ? this.proteinSequence[resIdx] : 'G';
            
            if (elem === 'C' || elem === 'F' || elem === 'Cl' || elem === 'Br') {
              if (hydrophobics.has(aa)) dgHydrophobic -= 0.5;
            } else if (elem === 'N' || elem === 'O') {
              if (acceptors.has(aa) || donors.has(aa)) dgHbond -= 1.0;
            }
          }
        }
      }
      
      if (atomHasClash) {
        mesh.material.color.setHex(0xff0000);
        mesh.material.emissive.setHex(0xff0000);
      } else {
        mesh.material.color.setHex(0x00ff00);
        mesh.material.emissive.setHex(0x00ff00);
      }
    });
    
    let dgEntropy = 0;
    if (this.dockedLigandMeta && this.dockedLigandMeta.rotatableBonds) {
      dgEntropy = this.dockedLigandMeta.rotatableBonds * 0.3;
    }
    
    const dgClash = totalClashes * 5.0;
    const dgTotal = dgHydrophobic + dgHbond + dgClash + dgEntropy;
    
    window.dispatchEvent(new CustomEvent('binding-affinity-update', {
      detail: { dgTotal, clashes: totalClashes }
    }));
  }
  
  showPockets(pockets, sequence) {
    this.pocketsGroup.clear();
    this.pocketSpheres = [];
    this.allPockets = pockets;
    this.proteinSequence = sequence;
    
    // Chemical mappings
    const acceptors = new Set(['D', 'E', 'N', 'Q', 'S', 'T', 'Y']);
    const donors = new Set(['K', 'R', 'H', 'N', 'Q', 'S', 'T', 'Y']);
    const hydrophobics = new Set(['V', 'I', 'L', 'F', 'M', 'W', 'C', 'A']);

    pockets.forEach(p => {
      const centroid = new THREE.Vector3(p.centroid[0]*0.1, p.centroid[1]*0.1, p.centroid[2]*0.1);
      
      const particlePositions = [];
      const particleColors = [];
      const color = new THREE.Color();
      
      for (let i=0; i<300; i++) {
        const resIdx = p.lining_residues[Math.floor(Math.random() * p.lining_residues.length)];
        const aa = sequence ? sequence[resIdx] : 'G';
        
        let cHex = 0xffffff;
        if (acceptors.has(aa)) cHex = 0xff0000;
        else if (donors.has(aa)) cHex = 0x0000ff;
        else if (hydrophobics.has(aa)) cHex = 0xffff00;
        else cHex = 0x888888;
        
        // Use CA coord as base, or fallback to centroid
        let basePos = centroid;
        if (this.caCoords && resIdx < this.caCoords.length) {
            basePos = this.caCoords[resIdx];
        }
        
        // Gaussian-ish scatter around the residue CA atom
        const radius = 0.3;
        const u = Math.random();
        const v = Math.random();
        const theta = 2 * Math.PI * u;
        const phi = Math.acos(2 * v - 1);
        const r = radius * Math.cbrt(Math.random());
        
        const x = basePos.x + r * Math.sin(phi) * Math.cos(theta);
        const y = basePos.y + r * Math.sin(phi) * Math.sin(theta);
        const z = basePos.z + r * Math.cos(phi);
        
        particlePositions.push(x, y, z);
        color.setHex(cHex);
        particleColors.push(color.r, color.g, color.b);
      }
      
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(particlePositions, 3));
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(particleColors, 3));
      
      const material = new THREE.PointsMaterial({
        size: 0.15,
        vertexColors: true,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
      });
      
      const particleSystem = new THREE.Points(geometry, material);
      particleSystem.position.set(0, 0, 0); // Points are already in global coords
      particleSystem.userData = { id: p.pocket_id, classification: p.classification, centroid: centroid };
      
      this.pocketsGroup.add(particleSystem);
      this.pocketSpheres.push(particleSystem);
      
      // Wireframe bounds
      const boundsGeo = new THREE.SphereGeometry(0.6, 16, 16);
      const boundsMat = new THREE.MeshBasicMaterial({ color: 0x222222, transparent: true, opacity: 0.1, wireframe: true });
      const boundsMesh = new THREE.Mesh(boundsGeo, boundsMat);
      boundsMesh.position.copy(centroid);
      particleSystem.add(boundsMesh);
      
      if (p.classification === 'cryptic') {
        const ringGeo = new THREE.TorusGeometry(0.8, 0.02, 16, 64);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0x1dc8a0 });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.position.copy(centroid);
        particleSystem.add(ring);
        particleSystem.userData.ring = ring;
      }
    });
  }
  
  hidePockets() {
    this.pocketsGroup.clear();
    this.pocketSpheres = [];
  }
  
  highlightPocket(pocketId) {
    if (this.allPockets) {
      this.activePocket = this.allPockets.find(p => p.pocket_id === pocketId);
    }
    this.pocketSpheres.forEach(mesh => {
      if (mesh.userData.id === pocketId) {
        mesh.material.opacity = 1.0;
        
        // Focus camera on pocket
        const centroid = mesh.userData.centroid || mesh.position;
        this.controls.target.copy(centroid);
        const offset = this.camera.position.clone().sub(centroid).normalize().multiplyScalar(15);
        this.camera.position.copy(centroid).add(offset);
        this.controls.update();
      } else {
        mesh.material.opacity = 0.2;
      }
    });
  }
  
  drawAllostericWebs(webs, pocketCentroid) {
    this.allosteryGroup.clear();
    if (!webs || webs.length === 0 || this.caCoords.length === 0) return;
    
    const start = new THREE.Vector3(pocketCentroid[0]*0.1, pocketCentroid[1]*0.1, pocketCentroid[2]*0.1);
    
    webs.forEach(web => {
      if (web.target >= this.caCoords.length) return;
      const end = this.caCoords[web.target];
      
      // Control point for curved spline
      const mid = start.clone().add(end).multiplyScalar(0.5);
      // Offset perpendicular to create a web-like arc
      const offset = new THREE.Vector3(Math.random()-0.5, Math.random()-0.5, Math.random()-0.5).multiplyScalar(5.0);
      mid.add(offset);
      
      const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
      const points = curve.getPoints(20);
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      
      const isPositive = web.correlation > 0;
      const material = new THREE.LineBasicMaterial({
        color: isPositive ? 0x00ffff : 0xff00ff,
        transparent: true,
        opacity: Math.abs(web.correlation) * 0.8,
        linewidth: 2
      });
      material.color.multiplyScalar(2.0); // > 1.0 for bloom
      
      const line = new THREE.Line(geometry, material);
      // Tag for glow/bloom later
      line.userData = { isAllostery: true };
      
      this.allosteryGroup.add(line);
    });
  }
  
  clearAllostery() {
    this.allosteryGroup.clear();
  }
  
  drawLigand(ligandData, meta) {
    this.ligandGroup.clear();
    if (!ligandData || !ligandData.atoms) return;
    this.dockedLigandMeta = meta;
    
    // Scale coords by 0.1
    const geometry = new THREE.SphereGeometry(0.15, 16, 16);
    
    ligandData.atoms.forEach(atom => {
      let color = 0x00ff00; // default green for safe
      
      const material = new THREE.MeshPhongMaterial({ 
        color, 
        emissive: color,
        emissiveIntensity: 1.5,
        shininess: 100 
      });
      const mesh = new THREE.Mesh(geometry, material);
      
      mesh.position.set(atom.coords[0]*0.1, atom.coords[1]*0.1, atom.coords[2]*0.1);
      mesh.userData = { rawCoords: atom.coords, element: atom.element };
      this.ligandGroup.add(mesh);
    });
    
    this.computeBindingAffinity();
  }
  
  clearLigand() {
    this.ligandGroup.clear();
  }
  
  toggleBackbone(visible) {
    this.showBackbone = visible;
    this.backboneGroup.visible = visible;
    if (visible && this.backboneGroup.children.length === 0) this._updateGeometry();
  }
  
  toggleSidechains(visible) {
    this.showSidechains = visible;
    this.sidechainGroup.visible = visible;
    if (visible && this.sidechainGroup.children.length === 0) this._updateGeometry();
  }
  
  toggleSurface(visible) {
    this.showSurface = visible;
    this.surfaceGroup.visible = visible;
    if (visible && this.surfaceGroup.children.length === 0) this._updateGeometry();
  }
  
  resetCamera() {
    this.fitCameraToProtein();
  }
  
  fitCameraToProtein() {
    if (this.caCoords.length === 0) return;
    
    const box = new THREE.Box3();
    this.caCoords.forEach(c => box.expandByPoint(c));
    
    const center = new THREE.Vector3();
    box.getCenter(center);
    
    const size = new THREE.Vector3();
    box.getSize(size);
    
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = this.camera.fov * (Math.PI / 180);
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
    cameraZ *= 1.5; // padding
    
    this.camera.position.set(center.x, center.y, center.z + cameraZ);
    this.controls.target.copy(center);
    this.controls.update();
  }
  
  animate(time) {
    const dt = time - this.lastTime;
    this.lastTime = time;
    
    // Handle interpolation
    if (this.isInterpolating && this.caCoords.length === this.targetCoords.length) {
      this.interpolationTime += dt;
      let t = this.interpolationTime / this.interpolationDuration;
      if (t >= 1.0) {
        t = 1.0;
        this.isInterpolating = false;
      }
      
      // Interpolate coords
      for (let i = 0; i < this.caCoords.length; i++) {
        this.caCoords[i].lerpVectors(this.caCoords[i], this.targetCoords[i], t);
        
        // Also interpolate backbone atoms if available
        if (this.bbCoords && this.targetBbCoords && this.bbCoords[i] && this.targetBbCoords[i]) {
          for (let j=0; j<this.bbCoords[i].length; j++) {
            this.bbCoords[i][j].lerpVectors(this.bbCoords[i][j], this.targetBbCoords[i][j], t);
          }
        }
      }
      
      this._updateGeometry();
      this.computeBindingAffinity();
    }
    
    // Animate rings
    this.pocketSpheres.forEach(mesh => {
      if (mesh.userData.ring) {
        mesh.userData.ring.rotation.x += 0.01;
        mesh.userData.ring.rotation.y += 0.02;
        // pulse scale
        const scale = 1.0 + 0.1 * Math.sin(time * 0.005);
        mesh.scale.set(scale, scale, scale);
      }
    });
    
    this.controls.update();
    this.composer.render();
  }
  
  dispose() {
    this.renderer.dispose();
    
    // Deep dispose traversal to prevent memory leaks
    this.scene.traverse((object) => {
      if (object.geometry) {
        object.geometry.dispose();
      }
      if (object.material) {
        if (Array.isArray(object.material)) {
          object.material.forEach(mat => mat.dispose());
        } else {
          object.material.dispose();
        }
      }
    });
  }
}
