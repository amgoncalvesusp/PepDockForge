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

## Windows Release

The packaged Windows build is distributed as a GitHub release asset:

- `PepDockForge-0.1.0-windows-x64.zip`
- `PepDockForge.exe`

The executable is built with PyInstaller and bundles the Python runtime and required scientific dependencies.

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

Build the Windows executable:

```powershell
python -m PyInstaller --noconfirm PepDockForge.spec
```

## Notes

PepDock Forge produces computational models and heuristic scores. Solubility, ranking, and minimized conformers are decision-support outputs, not experimental measurements or validated binding affinities.
