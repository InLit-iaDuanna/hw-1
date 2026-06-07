# Paper Figures Generation System

Academic-quality figure generation for HW-1 quasi-passive biped research.

## Directory Structure

```
paper_figures/
├── generators/          # Figure generation scripts
│   ├── fig_version_evolution.py
│   ├── fig_stability_domain.py
│   ├── fig_energy_analysis.py
│   ├── fig_phase_portrait.py
│   └── fig_hardware_specs.py
├── styles/
│   └── paper_style.mplstyle   # Unified matplotlib style
├── output/              # Generated figures (svg/pdf/png)
├── generate_all.py      # Batch generation script
└── figures_index.tex    # LaTeX figure index (auto-generated)
```

## Quick Start

Generate all figures:

```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\python.exe paper_figures\generate_all.py
```

Generate individual figures:

```powershell
python paper_figures\generators\fig_version_evolution.py
python paper_figures\generators\fig_stability_domain.py
```

## Figure Specifications

### Figure 1: Version Evolution Timeline
- **Type**: Timeline with scatter plot
- **Content**: V01-V24 development progress, category breakdown
- **Key Features**: Performance maturity index, milestone annotations
- **Output**: `fig1_version_evolution.{svg,pdf,png}`

### Figure 2: Stability Domain Heatmap
- **Type**: Parameter space heatmap with contours
- **Content**: Hip/ankle stiffness vs. gait stability
- **Key Features**: Optimal point marking, design comparison
- **Output**: `fig2_stability_domain.{svg,pdf,png}`

### Figure 3: Energy Analysis
- **Type**: Multi-panel (bar chart + time series)
- **Content**: CoT comparison, mechanical energy decomposition
- **Key Features**: V08-V11 efficiency metrics, KE/PE exchange
- **Output**: `fig3_energy_analysis.{svg,pdf,png}`

### Figure 4: Phase Portrait
- **Type**: Phase space trajectories + Poincaré section
- **Content**: Hip/knee limit cycles, touchdown events
- **Key Features**: Convergence analysis, configuration space
- **Output**: `fig4_phase_portrait.{svg,pdf,png}`

### Figure 5: Hardware Specifications
- **Type**: Schematic + pie chart + table
- **Content**: V22 mechanical design, mass distribution, specs
- **Key Features**: Annotated robot diagram, component details
- **Output**: `fig5_hardware_specs.{svg,pdf,png}`

## Style Guidelines

All figures use `paper_style.mplstyle` for consistency:
- **Resolution**: 300 DPI
- **Formats**: SVG (editing), PDF (LaTeX), PNG (preview)
- **Fonts**: Sans-serif, LaTeX-compatible
- **Colors**: Colorblind-friendly palette (Wong 2011)
- **Grid**: Light gray, below data
- **Spines**: Top/right removed

## LaTeX Integration

After generation, `figures_index.tex` provides ready-to-use LaTeX code:

```latex
\input{paper_figures/figures_index.tex}
```

Reference figures in text:
```latex
Figure~\ref{fig:version_evolution} shows...
```

## Customization

### Modify Style
Edit `styles/paper_style.mplstyle`:
```python
font.size: 10          # Change base font size
figure.figsize: 8, 6   # Change default size
```

### Add New Figure
1. Create `generators/fig_new_figure.py`
2. Follow template from existing generators
3. Add import in `generate_all.py`
4. Run batch generation

## Dependencies

- matplotlib >= 3.5
- numpy >= 1.21
- Project `common/plot_styles.py` (for PALETTE)

## Color Palette

Inherited from `common/plot_styles.py`:
- `ok`: #2a7a3b (green)
- `warn`: #d68b00 (orange)
- `fail`: #b3331b (red)
- `neutral`: #3a3a3a (dark gray)
- `left`: #0c789f (blue)
- `right`: #b34a36 (brown-red)

## Output Verification

Check generated files:
```powershell
Get-ChildItem paper_figures\output\*.pdf
```

Preview PNG files in Windows Photo Viewer or open SVG in browser/Inkscape.

## Troubleshooting

**Import error**: Ensure `.venv-mujoco` is activated
**Missing data**: Some figures use synthetic data for demonstration
**Font warnings**: Fallback to DejaVu Sans if custom fonts unavailable
**LaTeX compatibility**: Use PDF output for pdflatex compilation

## Version History

- **v1.0** (2026-06-04): Initial system with 5 core figures
