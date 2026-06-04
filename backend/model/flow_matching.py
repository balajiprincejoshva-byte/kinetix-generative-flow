import torch
import torch.nn as nn
from backend.model.encoder import ProteinEncoder
from backend.model.decoder import CoordinateDecoder
from backend.model.noise_schedule import OTFlowSchedule

class KinetiXFlowModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.encoder = ProteinEncoder(
            latent_dim=config.LATENT_DIM,
            hidden_dim=config.HIDDEN_DIM,
            n_layers=config.N_LAYERS,
            n_heads=config.N_HEADS
        )
        self.decoder = CoordinateDecoder(
            latent_dim=config.LATENT_DIM,
            hidden_dim=config.HIDDEN_DIM
        )
        self.schedule = OTFlowSchedule()

    def forward(self, protein_graph, noisy_coords: torch.Tensor, t: torch.Tensor):
        """
        Training forward pass.
        Returns predicted velocity field.
        """
        # Convert inputs if necessary (or assume they are tensors)
        aa_types = protein_graph.aa_types_tensor # shape (N,)
        ca_coords = protein_graph.ca_coords_tensor # shape (N, 3)
        edge_index = protein_graph.edge_index_tensor # shape (2, E)
        edge_attr = protein_graph.edge_attr_tensor # shape (E,)
        
        node_emb, _ = self.encoder(aa_types, ca_coords, edge_index, edge_attr)
        pred_v = self.decoder(noisy_coords, node_emb, t)
        
        return pred_v

    def loss(self, protein_graph, x_1_coords: torch.Tensor):
        """
        Compute full training loss for a batch.
        Sample t ~ U(0,1), sample x_0 ~ N(0, I),
        compute x_t via schedule, predict velocity, compute MSE vs target.
        """
        N = x_1_coords.size(0)
        device = x_1_coords.device
        
        t = self.schedule.sample_t(1, device=device)
        x_0 = torch.randn_like(x_1_coords)
        
        x_t = self.schedule.sample_path(x_0, x_1_coords, t)
        target_v = self.schedule.target_vector_field(x_t, x_1_coords, t)
        
        pred_v = self.forward(protein_graph, x_t, t)
        
        loss = torch.nn.functional.mse_loss(pred_v, target_v)
        return loss
