# Every config value needed across the entire project.
# If a value is used in more than one file, it lives here.

MAX_RESIDUES = 1000            # reject PDBs larger than this
N_CONFORMATIONS = 100          # number of ensemble frames to generate
FLOW_STEPS = 50                # ODE integration steps for flow matching
LATENT_DIM = 128               # protein graph embedding dimension
HIDDEN_DIM = 256               # transformer hidden dim
N_LAYERS = 6                   # number of equivariant layers
N_HEADS = 8                    # attention heads
ALPHA_SPHERE_RADIUS = 3.5      # Angstroms — probe radius for cavity detection
MIN_POCKET_VOLUME = 200.0      # Angstroms^3 — discard trivially small cavities
DRUGGABILITY_THRESHOLD = 0.55  # score [0,1] above which pocket is flagged
STREAM_CHUNK_SIZE = 10         # send conformations to frontend in chunks of 10
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000"
]
