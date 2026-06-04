import torch
import torch.nn as nn
import torch.nn.functional as F

class RBFEmbedding(nn.Module):
    """Radial Basis Function embedding for distances."""
    def __init__(self, n_rbf: int = 20, d_min: float = 0.0, d_max: float = 20.0):
        super().__init__()
        self.n_rbf = n_rbf
        self.d_min = d_min
        self.d_max = d_max
        # Centers for the RBFs
        centers = torch.linspace(d_min, d_max, n_rbf)
        self.register_buffer("centers", centers)
        # Width parameter gamma (1 / 2 * sigma^2)
        width = (d_max - d_min) / n_rbf
        self.gamma = 1.0 / (2 * (width ** 2))

    def forward(self, d: torch.Tensor) -> torch.Tensor:
        # d shape: (E,)
        # output shape: (E, n_rbf)
        d = d.unsqueeze(-1)
        return torch.exp(-self.gamma * (d - self.centers) ** 2)

class MessagePassingLayer(nn.Module):
    def __init__(self, latent_dim: int, n_rbf: int, n_heads: int):
        super().__init__()
        self.latent_dim = latent_dim
        self.n_heads = n_heads
        self.head_dim = latent_dim // n_heads
        
        self.W_q = nn.Linear(latent_dim, latent_dim)
        self.W_k = nn.Linear(latent_dim, latent_dim)
        self.W_v = nn.Linear(latent_dim, latent_dim)
        
        # Project RBF to v dimension to gate messages
        self.rbf_proj = nn.Linear(n_rbf, latent_dim)
        
        self.out_proj = nn.Linear(latent_dim, latent_dim)
        self.layer_norm = nn.LayerNorm(latent_dim)
        
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, rbf_emb: torch.Tensor) -> torch.Tensor:
        # x: (N, latent_dim)
        # edge_index: (2, E) -> [src, dst]
        # rbf_emb: (E, n_rbf)
        
        N = x.size(0)
        src, dst = edge_index[0], edge_index[1]
        
        q = self.W_q(x) # (N, latent_dim)
        k = self.W_k(x) # (N, latent_dim)
        v = self.W_v(x) # (N, latent_dim)
        
        # Edge features
        q_dst = q[dst] # (E, latent_dim)
        k_src = k[src] # (E, latent_dim)
        v_src = v[src] # (E, latent_dim)
        
        # Multi-head dot product attention
        q_dst = q_dst.view(-1, self.n_heads, self.head_dim)
        k_src = k_src.view(-1, self.n_heads, self.head_dim)
        v_src = v_src.view(-1, self.n_heads, self.head_dim)
        
        attn_logits = (q_dst * k_src).sum(dim=-1) / (self.head_dim ** 0.5) # (E, n_heads)
        
        # Distance gating
        edge_gate = self.rbf_proj(rbf_emb) # (E, latent_dim)
        edge_gate = edge_gate.view(-1, self.n_heads, self.head_dim)
        
        v_src = v_src * edge_gate # apply gate
        
        # We need to softmax over neighbors.
        # Compute max logit per dst for numerical stability
        max_logits = torch.zeros(N, self.n_heads, device=x.device).scatter_reduce_(0, dst.unsqueeze(1).expand(-1, self.n_heads), attn_logits, reduce="amax", include_self=False)
        exp_logits = torch.exp(attn_logits - max_logits[dst])
        
        sum_exp = torch.zeros(N, self.n_heads, device=x.device).scatter_add_(0, dst.unsqueeze(1).expand(-1, self.n_heads), exp_logits)
        attn_weights = exp_logits / (sum_exp[dst] + 1e-10) # (E, n_heads)
        
        # Apply weights to v
        msg = v_src * attn_weights.unsqueeze(-1) # (E, n_heads, head_dim)
        msg = msg.view(-1, self.latent_dim) # (E, latent_dim)
        
        # Aggregate messages
        aggr_msg = torch.zeros(N, self.latent_dim, device=x.device).scatter_add_(0, dst.unsqueeze(1).expand(-1, self.latent_dim), msg)
        
        out = self.out_proj(aggr_msg)
        
        # Residual and layer norm
        return self.layer_norm(x + out)

class ProteinEncoder(nn.Module):
    def __init__(self, latent_dim: int, hidden_dim: int, n_layers: int, n_heads: int = 8):
        super().__init__()
        self.latent_dim = latent_dim
        # 21 AA types: 20 standard + 1 unknown
        self.aa_emb = nn.Embedding(21, latent_dim)
        self.rbf = RBFEmbedding(n_rbf=20, d_min=0.0, d_max=20.0)
        
        self.layers = nn.ModuleList([
            MessagePassingLayer(latent_dim, 20, n_heads)
            for _ in range(n_layers)
        ])

    def forward(self, aa_types: torch.Tensor, ca_coords: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor):
        # Returns: node_emb (N, latent_dim), graph_emb (latent_dim,)
        # Note: ca_coords is passed to maintain API signature, but our graph is built on it
        # and SE(3) invariance comes from using only pairwise distances `edge_attr`
        
        x = self.aa_emb(aa_types)
        rbf_emb = self.rbf(edge_attr)
        
        for layer in self.layers:
            x = layer(x, edge_index, rbf_emb)
            
        graph_emb = x.mean(dim=0)
        return x, graph_emb
