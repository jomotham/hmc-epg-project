# SCIDO
### *Supervised Classification of Insect Data & Observations*

<p align="center">
  <a href="url">
    <img src="cs/GUI/SCIDO.png" width="240">
  </a>
</p>

A PyQt-based GUI for electropenetrography (EPG). Supports live data acquisition from the HMC DR3 EPG board and post-acquisition data annotation and ML-based waveform classification. Developed by Harvey Mudd College and made in collaboration with the USDA and Auburn University.

#### [User Guide](https://docs.google.com/document/d/1EotUZ7dMRxNG9cC_OaZ0CuDczuERszNqkFvk_2-06NA/edit?usp=sharing)

### Installation
##### Users
Currently, contact the HMC team to get an runnable .exe of the program (or run from source, see below). In the future, each version's .exe will be bundled with their source code into the "Releases" section of the repository on GitHub.

##### Developers
We highly recommend using [**uv**](https://docs.astral.sh/uv/) to install and manage this project's dependencies, but pip with venv works too. The dependencies are listed in [`pyproject.toml`](/pyproject.toml). If a uv project is set up, the following can be used to obtain the source and install the dependencies.
```
git clone https://github.com/jomotham/scido
cd scido
uv sync
```
If you are not using uv, the dependencies can be installed from [`pyproject.toml`](/pyproject.toml) with pip with 
```
pip install .
```

**NOTE**: the wheels for `torch`, `torchvision`, and `torchaudio` linked in `[tool.uv.sources]` in [`pyproject.toml`](/pyproject.toml) are specific to a Windows computer running Python 3.13.X with an AMD CPU and a GPU supporting CUDA >=12.9. Change these wheel links as needed from https://download.pytorch.org/whl/ to match your system.

**Running from source**
```
uv run ./cs/GUI/main.py              # launch directly into the main window
uv run ./cs/GUI/AppLauncherDialog.py # launch to the dedicated launcher
```
[**Link to project Drive**](https://drive.google.com/drive/folders/1IeiOQtImzPjvFvvDDb7daoPg8Atfd-Y5?usp=sharing)
