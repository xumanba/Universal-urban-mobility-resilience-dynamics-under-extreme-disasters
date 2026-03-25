# Urban Mobility Data Analysis Pipeline

This repository accompanies our paper on urban mobility resilience under extreme disasters. The `san_jose_pipeline/` section provides the complete code and private SafeGraph datasets to reproduce the empirical results (degree distribution `pk` and net inflow distribution `px`) presented in the paper. You can run the pipeline on the included datasets to verify and replicate the figures reported in our study.

## Directory Structure

```
.
├── san_jose_pipeline/          # San Jose data processing pipeline
│   ├── san_jose_pipeline.py    # Main processing script
│   ├── CA_SanJose_08-14.csv    # SafeGraph raw data (pre-disaster)
│   ├── CA_SanJose_08-21.csv    # SafeGraph raw data (during disaster)
│   ├── CA_SanJose_08-28.csv    # SafeGraph raw data (post-disaster)
│   └── output/                 # Output directory (auto-generated)
│
└── fig4-plot-code/             # Figure 4 plotting code
    ├── opt4.ipynb              # Plotting notebook
    ├── fig4.1/                 # Fig 4.1 data
    ├── fig4.2/                 # Fig 4.2 data
    └── fig4.3/                 # Fig 4.3 data
```

## Requirements

```bash
pip install numpy pandas adjustText xlrd openpyxl matplotlib
```

## Usage

### San Jose Pipeline

```bash
cd san_jose_pipeline
python san_jose_pipeline.py
```

Results will be saved in the `output/` directory.

### Figure 4 Plotting

Open `fig4-plot-code/opt4.ipynb` in Jupyter Notebook and run all cells sequentially to generate the figures.
