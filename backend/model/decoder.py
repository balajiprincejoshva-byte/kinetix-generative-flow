import torch
import torch.nn as nn
import math

class SinusoidalTimeEmbedding(nn.Module):
    def __init__(self, dim: int = 64):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        # t shape: (B,) or (1,)
        # output shape: (B, dim)
        device = t.device
        half_dim = self.dim // 2
        emb = math.log(10000) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, device=device) * -emb)
        emb = t[:, None] * emb[None, :]
        emb = torch.cat((emb.sin(), emb.cos()), dim=-1)
        return emb

class CoordinateDecoder(nn.Module):
    def __init__(self, latent_dim: int, hidden_dim: int):
        super().__init__()
        self.time_emb = SinusoidalTimeEmbedding(dim=64)
        
        in_dim = 3 + latent_dim + 64
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, 3)
        )
        
        # We can implement a skip connection explicitly in forward if we wanted, 
        # but standard MLP is specified as "4-layer MLP with skip connections".
        # Let's add skip connections block-wise
        self.fc1 = nn.Linear(in_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.fc4 = nn.Linear(hidden_dim, 3)
        self.silu = nn.SiLU()

    def forward(self, noisy_coords: torch.Tensor, node_emb: torch.Tensor, t: torch.Tensor):
        # noisy_coords: (N, 3)
        # node_emb: (N, latent_dim)
        # t: (1,) or scalar tensor
        
        if t.dim() == 0:
            t = t.unsqueeze(0)
            
        N = noisy_coords.size(0)
        t_emb = self.time_emb(t) # (1, 64)
        t_emb_broadcast = t_emb.expand(N, -1) # (N, 64)
        
        x = torch.cat([noisy_coords, node_emb, t_emb_broadcast], dim=-1) # (N, in_dim)
        
        h1 = self.silu(self.fc1(x))
        h2 = self.silu(self.fc2(h1)) + h1  # Skip connection
        h3 = self.silu(self.fc3(h2)) + h2  # Skip connection
        out = self.fc4(h3) # (N, 3)
        
        return out
