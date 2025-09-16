To ML team: complete this readme


# Installation
We recommend using [**uv**](https://docs.astral.sh/uv/) to manage this project’s environment and dependencies.  
If you prefer, you can use `pip` with a `venv`, but uv is simpler and fully reproducible.

### Setup with uv
From the `machine-learning` folder of the git repository (open this as your workspace in your editor):

```bash
uv sync --extra <compute-platform>
```
#### Valid compute platform options
- `cpu` – CPU-only (default for macOS)  
- `cu129` – CUDA 12.9 (Windows/Linux with compatible NVIDIA drivers)  
- `cu128` – CUDA 12.8  
- `cu126` – CUDA 12.6  

To check which CUDA version your system supports (Windows/Linux only; **macOS does not support CUDA**):

```bash
nvcc --version
```


### Setup with pip (alternative)
If you’re not using uv, you can install the base dependencies directly:

```bash
pip install .
```

**Important:** pip will **not** automatically install PyTorch.  
You must install the correct wheel for your system from the [PyTorch installation guide](https://pytorch.org/get-started/locally/).  