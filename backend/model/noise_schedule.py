import torch
import numpy as np

class OTFlowSchedule:
    def __init__(self, sigma_min: float = 0.001):
        self.sigma_min = sigma_min

    def sample_path(self, x_0: torch.Tensor, x_1: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        """Interpolate between noise x_0 and data x_1 at time t."""
        # ψ_t(x_0, x_1) = (1 - (1 - σ_min) * t) * x_0 + t * x_1
        # Handle broadcasting of t to match x dimensions
        t_expand = t.view(-1, 1, 1) if t.dim() == 1 and x_0.dim() == 3 else t
        return (1 - (1 - self.sigma_min) * t_expand) * x_0 + t_expand * x_1

    def target_vector_field(self, x_t: torch.Tensor, x_1: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        """The target vector field u_t(x_t | x_1)."""
        # u_t = (x_1 - (1 - σ_min) * x_t) / (1 - (1 - σ_min) * t)
        t_expand = t.view(-1, 1, 1) if t.dim() == 1 and x_t.dim() == 3 else t
        return (x_1 - (1 - self.sigma_min) * x_t) / (1 - (1 - self.sigma_min) * t_expand + 1e-8)

    def sample_t(self, batch_size: int, device: str = "cpu") -> torch.Tensor:
        """Sample time uniformly from (0, 1)."""
        return torch.rand(batch_size, device=device)
