export class EnsemblePlayer {
  constructor(viewer, onFrameChange) {
    this.viewer = viewer;
    this.onFrameChange = onFrameChange;
    
    this.frames = [];
    this.currentFrameIdx = 0;
    this.playing = false;
    this.fps = 5;
    this.timer = null;
  }
  
  addFrames(newFrames) {
    this.frames.push(...newFrames);
    // If this is the first chunk and we aren't playing, start playing
    if (this.frames.length === newFrames.length && !this.playing) {
      this.play();
    }
  }
  
  play() {
    if (this.frames.length === 0) return;
    this.playing = true;
    this.tick();
  }
  
  pause() {
    this.playing = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
  
  goToFrame(index) {
    if (index < 0 || index >= this.frames.length) return;
    this.currentFrameIdx = index;
    const frame = this.frames[this.currentFrameIdx];
    this.viewer.loadFrame(frame);
    if (this.onFrameChange) {
      this.onFrameChange(frame);
    }
  }
  
  setSpeed(fps) {
    this.fps = fps;
    // If playing, we don't need to restart immediately, next tick will use new speed
  }
  
  tick() {
    if (!this.playing) return;
    
    this.goToFrame(this.currentFrameIdx);
    
    this.currentFrameIdx++;
    if (this.currentFrameIdx >= this.frames.length) {
      this.currentFrameIdx = 0; // loop
    }
    
    const delay = 1000 / this.fps;
    this.timer = setTimeout(() => this.tick(), delay);
  }
  
  get currentFrame() {
    return this.currentFrameIdx;
  }
  
  get totalFrames() {
    return this.frames.length;
  }
  
  get isPlaying() {
    return this.playing;
  }
}
