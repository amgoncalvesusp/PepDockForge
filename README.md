# PepDock Forge

PepDock Forge is a desktop application for peptide library construction, sequence-level triage, 3D peptide building, OpenMM minimization, and export for downstream molecular workflows.

## Features

- Build peptide libraries manually or combinatorially.
- Limit peptide sequences to 20 standard amino-acid residues.
- Analyze descriptors, ranking, and sequence-based solubility.
- Select soluble candidates before 3D building.
- Generate and minimize peptide structures with RDKit and OpenMM.
- Force-field presets:
  - Amber19 + GBn2 implicit solvent
  - CHARMM36 vacuum
- Export structures as PDB, SDF, MOL2, and PDBQT.
- Choose PDB record type: `ATOM` or `HETATM`.
- Preview PDB structures in the desktop GUI.

## Releases

The active release version is `0.1.0`.

- `PepDockForge-0.1.0-windows-x64.zip`
- `PepDockForge.exe`
- `PepDockForge-0.1.0-ubuntu-24.04-x86_64.tar.gz`
- `PepDockForge`

The executables are built with PyInstaller and bundle the Python runtime and required scientific dependencies. PyInstaller builds are platform-specific, so the Ubuntu asset must be built on Linux.

## Authors and Inventors

- Bruna Flôres Negrisoli (FMVZ-USP)
- Isabel Cristina Conceição Periquito (FMVZ-USP)
- Adriano Marques Gonçalves (UNIARA e FMVZ-USP)

## Development

Install dependencies in a Python 3.11 environment:

```powershell
pip install -r requirements.txt
```

Run from source:

```powershell
python pepdock_forge.py
```

Run the built-in self-test:

```powershell
python pepdock_forge.py --self-test
```

Build the executable for the current platform:

```powershell
python -m PyInstaller --noconfirm PepDockForge.spec
```

On Ubuntu 24.04, build and package the Linux release with:

```bash
python3 -m venv .venv-linux
source .venv-linux/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python pepdock_forge.py --self-test
python -m PyInstaller --noconfirm PepDockForge.spec
tar -C dist -czf dist/PepDockForge-0.1.0-ubuntu-24.04-x86_64.tar.gz PepDockForge
```

## Notes

PepDock Forge produces computational models and heuristic scores. Solubility, ranking, and minimized conformers are decision-support outputs, not experimental measurements or validated binding affinities.
