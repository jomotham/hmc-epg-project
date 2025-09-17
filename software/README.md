# SCIDO
### *Supervised Classification of Insect Data & Observations*

<p align="center">
  <a href="url">
    <img src="cs/gui/SCIDO.png" width="240">
  </a>
</p>

A PyQt-based GUI for electropenetrography (EPG). Supports live data acquisition from the HMC DR3 EPG board and post-acquisition data annotation and ML-based waveform classification. Developed by Harvey Mudd College and made in collaboration with the USDA and Auburn University.

#### [User Guide](https://docs.google.com/document/d/1EotUZ7dMRxNG9cC_OaZ0CuDczuERszNqkFvk_2-06NA/edit?usp=sharing)

# Installation
## Users
Currently, contact the HMC team to get an runnable .exe of the program (or run from source, see below). In the future, each version's .exe will be bundled with their source code into the "Releases" section of the repository on GitHub.

## Developers
We recommend using [**uv**](https://docs.astral.sh/uv/) to manage this folder's environment and dependencies.  
If you prefer, you can use `pip` with a `venv`, but uv is simpler and fully reproducible.

### Setup with uv
From the `software` folder of the git repository (open this as your workspace in your editor):

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


### Running from source
```
cd hmc-epg-project/software
uv run ./cs/gui/main.py              # launch directly into the main window
uv run ./cs/gui/AppLauncherDialog.py # launch to the dedicated launcher
```
[**Link to project Drive**](https://drive.google.com/drive/folders/1IeiOQtImzPjvFvvDDb7daoPg8Atfd-Y5?usp=sharing)
