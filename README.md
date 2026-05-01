# Probabilistic Multi-Hazard Forecasting for Tropical Cyclones Using MLM

This repository contains the scripts, notebooks, workflows, and documentation developed during my doctoral research stay at the University of Lausanne (UNIL), within the Institute of Earth Surface Dynamics. The project is part of my PhD research in Earth and Atmospheric Sciences and focuses on the analysis of tropical cyclone hazards affecting Mexico. In particular, the repository supports the study of relationships between tropical cyclone size, precipitation distribution, oceanic conditions, and hydrometeorological impacts such as extreme rainfall, flooding, and landslides.

The project integrates atmospheric and geospatial datasets to develop reproducible workflows for tropical cyclone analysis. These workflows include data preprocessing, spatial filtering, composite analysis, anomaly estimation, trend assessment, and visualization of storm-related environmental conditions. The repository is intended to serve both as a research archive and as an active development space for reproducible scientific analysis.

## Data

The project uses multiple datasets related to tropical cyclones, precipitation, and environmental conditions. These may include, but are not limited to:

- Tropical cyclone best-track data for the North Atlantic and Eastern Pacific basins.
- Gridded precipitation datasets used to evaluate rainfall associated with tropical cyclones.
- Regional geospatial layers used for spatial analysis and visualization.

Large raw datasets are not necessarily stored directly in this repository. When possible, scripts are provided to document how data were obtained, processed, filtered, and transformed. Processed or intermediate datasets may be included only when they are lightweight, reproducible, and appropriate for version control.

## Data Contact

For questions regarding data archiving, data removal, or reproducibility of the workflows, please contact:

**Adolfo Perez-Estrada**  
PhD Student in Earth and Atmospheric Sciences  
Universidad Nacional Autónoma de México / University of Lausanne  
GitHub: `@apereze`  
Email: `apereze@atmosfera.unam.mx`  /  `adolfo.perezestrada@unil.ch`
External email: `adolfopest@icloud.com`

**Expiration Date:** YYYYMMDD  
Data can be **archived** after the expiration date, unless required for reproducibility of publications, thesis chapters, or ongoing collaborations.

Most scripts, notebooks, and analysis files should be preserved because they require little storage and are essential for documenting the computational workflow. Large raw datasets should be archived externally or regenerated from the original data providers when possible.

## Getting Started

The repository is organized around the main stages of the analysis workflow:

1. Data acquisition and organization.
2. Preprocessing of tropical cyclone tracks datasets.
3. Spatial filtering by basin, region, or storm position.
4. Computation of precipitation and environmental composites.
5. Analysis of anomalies, trends, and regional contrasts.
6. Visualization of maps, figures, and diagnostic outputs.
7. Generation of processed datasets for statistical or machine learning analysis.

Primary analysis scripts and notebooks should be located in folders such as:

```text
scripts/
notebooks/
data/
figures/
outputs/
docs/
````

A typical workflow may involve running preprocessing scripts first, followed by regional analysis notebooks and visualization routines.

### Example workflow

```bash
# Clone the repository
git clone https://github.com/your-username/AITCHazard_Mexico.git

# Move into the project directory
cd AITCHazard_Mexico

# Create a Python environment
conda create -n tc-hazards python=3.11

# Activate the environment
conda activate tc-hazards

# Install required packages
pip install -r requirements.txt

# Run an example preprocessing script
python scripts/preprocess_tracks.py

# Run an example analysis script
python scripts/run_composite_analysis.py
```

## Requirements

This project is primarily developed in Python and relies on scientific computing, geospatial analysis, and visualization libraries.

Recommended core requirements include:

```text
python>=3.10
numpy
pandas
xarray
geopandas
shapely
rasterio
netCDF4
h5netcdf
matplotlib
cartopy
scipy
scikit-learn
tqdm
jupyter
```

Additional packages may be required depending on the specific analysis, dataset format, or visualization routine.

### Step 1: Create a development environment

```bash
conda create -n tc-hazards python=3.11
conda activate tc-hazards
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Organize input data

Input data should be placed in a structured directory, for example:

```text
data/
├── raw/
├── processed/
├── tracks/
├── precipitation/
├── ocean/
└── atmospheric/
```

### Step 4: Run the analysis

```bash
python scripts/run_analysis.py
```

### Step 5: Export figures or processed outputs

```bash
python scripts/make_figures.py
```

Final outputs may include processed datasets, regional composites, anomaly maps, statistical summaries, and publication-quality figures.

## Publications

This repository supports analyses related to my doctoral research on tropical cyclone hazards in Mexico.

Publications, thesis chapters, or manuscripts using this repository will be listed here as they become available.

Example format:

```text
Author(s).
Year. Title of the article or thesis chapter.
Journal or institution.
DOI: https://doi.org/xxxxx
```

## Contributing

Contributions are welcome in the context of academic collaboration. Before contributing, please open an issue or contact the repository maintainer to discuss proposed changes.

Recommended contribution practices:

* Use clear and descriptive commit messages.
* Keep scripts modular and documented.
* Follow Python best practices and readable coding conventions.
* Use meaningful variable names.
* Document input and output files clearly.
* Avoid committing large raw datasets.
* Include comments explaining non-trivial scientific or technical decisions.
* When possible, provide reproducible examples or notebooks.

Preferred coding style:

```text
- Python code should follow PEP 8 conventions.
- Functions should include docstrings.
- Analysis notebooks should be organized into clear sections.
- Figures should include labels, units, and metadata when appropriate.
```

## Notes

* Large climate and oceanographic datasets should not be committed directly unless explicitly justified.
* File paths should be configurable and not hard-coded to local machines.
* Intermediate files should be documented so they can be regenerated.
* All spatial analyses should clearly specify coordinate reference systems, spatial resolution, and temporal coverage.
* Results may depend on dataset version, preprocessing assumptions, spatial domain, and storm selection criteria.
* Users should verify data licensing terms from the original data providers before redistributing any dataset.

## Authors

**Adolfo Perez Estrada**
Initial work, data processing, analysis design, visualization, and documentation.
PhD Student in Earth and Atmospheric Sciences
Universidad Nacional Autónoma de México / University of Lausanne

Additional contributors will be listed here as the project develops.

**Milton Gomez (@ ) UNIL**
**Christian Dominguez (@dosach) UNAM**
**Tom Beucler (@ )   UNIL**

## License

This project is licensed under the MIT License. See the `LICENSE.md` file for details.

## Acknowledgments

This work was developed during a doctoral research stay at the University of Lausanne.

Acknowledgments are extended to:

* Prof. Tom Beucler and collaborators at the Institute of Earth Surface Dynamics, University of Lausanne.
* Universidad Nacional Autónoma de México.
* The doctoral committee and academic collaborators supporting this research.
* Data providers and scientific communities maintaining open-access atmospheric, oceanographic, and geospatial datasets.
* Developers of open-source scientific Python libraries used in this project.

This repository is inspired by reproducible research practices in climate science, atmospheric sciences, geospatial analysis, and data-driven hazard assessment.

```
```
