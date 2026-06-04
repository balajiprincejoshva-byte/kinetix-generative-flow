import pytest
import torch
import numpy as np
from backend.model.noise_schedule import OTFlowSchedule
from backend.model.flow_matching import KinetiXFlowModel
from backend.model.inference import sample_ensemble, compute_rmsd
from backend.parser.pdb_parser import ProteinGraph
import backend.config as config

def test_ot_schedule():
    schedule = OTFlowSchedule(sigma_min=0.0) # easy to test
    x_0 = torch.zeros(10, 3)
    x_1 = torch.ones(10, 3)
    
    # t = 0 -> x_0
    t_0 = torch.tensor([0.0])
    assert torch.allclose(schedule.sample_path(x_0, x_1, t_0), x_0)
    
    # t = 1 -> x_1
    t_1 = torch.tensor([1.0])
    assert torch.allclose(schedule.sample_path(x_0, x_1, t_1), x_1)

def test_flow_model_forward():
    model = KinetiXFlowModel(config)
    
    class DummyGraph:
        n_residues = 10
        aa_types_tensor = torch.zeros(10, dtype=torch.long)
        ca_coords_tensor = torch.randn(10, 3)
        edge_index_tensor = torch.randint(0, 10, (2, 50))
        edge_attr_tensor = torch.rand(50)
        
    graph = DummyGraph()
    t = torch.tensor([0.5])
    noisy_coords = torch.randn(10, 3)
    
    out = model(graph, noisy_coords, t)
    assert out.shape == (10, 3)

def test_sample_ensemble():
    model = KinetiXFlowModel(config)
    model.is_trained = False
    
    ca = np.random.rand(15, 3)
    graph = ProteinGraph(
        residue_ids=[('A', i, 'ALA') for i in range(15)],
        ca_coords=ca,
        cb_coords=ca,
        bb_coords=np.zeros((15, 4, 3)),
        sequence="A"*15,
        n_residues=15,
        distance_matrix=np.ones((15, 15)),
        edge_index=np.zeros((2, 10)),
        edge_attr=np.zeros(10)
    )
    
    gen = sample_ensemble(model, graph, n_samples=10, chunk_size=5)
    chunk = next(gen)
    assert len(chunk) == 5
    assert "ca_coords" in chunk[0]
    
    # test rmsd > 0 and < 10
    assert 0 < chunk[0]["rmsd_from_input"] < 10.0
