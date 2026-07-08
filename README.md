# Techno-Economic STES Database

This repository was developed as part of the ETH Zurich semester project **"Seasonal Thermal Energy Storage: Recent Techno-Economic Developments and Modeling Approaches."**

It provides techno-economic data and simulation tools for **Seasonal Thermal Energy Storage (STES)** technologies, with a particular focus on their representation in optimization-based Energy System Models (ESMs).

The accompanying Python package, `stes_tools`, includes:

- Cost functions for PTES, TTES, BTES and ATES
- Water property functions
- A heat-loss simulation framework for PTES and TTES
- Tools for generating stratified temperature maps
- Validation examples based on operational PTES data

---

# Features

## Cost database

The repository contains CAPEX and OPEX data for the following Seasonal Thermal Energy Storage technologies:

- PTES – Pit Thermal Energy Storage
- TTES – Tank Thermal Energy Storage
- BTES – Borehole Thermal Energy Storage
- ATES – Aquifer Thermal Energy Storage

The package provides functions to estimate investment and operating costs based on the selected technology and storage capacity.

## Heat-loss simulation

The package includes a simulation framework for modelling heat losses in PTES and TTES systems.

The simulation derives an effective **self-discharge rate** ($\eta_{\mathrm{self}}$), which can be directly used in the Simple Storage Model (SSM) frequently employed in optimization-based energy system models:

$$
Q_{\mathrm{sto,t+1}}
=
\eta_{\mathrm{self}}Q_{\mathrm{sto,t}}
+
\left(
\eta_{\mathrm{ch}}\dot{Q}_{\mathrm{ch}}
-
\frac{\dot{Q}_{\mathrm{disch}}}{\eta_{\mathrm{disch}}}
\right)
\Delta t
$$

---

# Package overview

The Python package `stes_tools` provides the following functionality.

## Water properties

### `density_water(T)`

Returns the density of water (kg/m³) at temperature `T` (°C).

### `specific_heat_water(T)`

Returns the specific heat capacity of water (J/(kg·K)) at temperature `T` (°C).

---

## Cost functions

### `CAPEX_STES(technology, unit, capacity, T_min, T_max)`

Returns the **specific CAPEX** of the selected STES technology as a function of

- technology type
- storage capacity
- temperature range

Supported technologies:

- PTES
- TTES
- BTES
- ATES

---

### `OPEX_STES(technology)`

Returns the annual OPEX factor for the selected STES technology.

---

## Heat-loss simulation

### `data_import(file_path)`

Imports the operational data required for the heat-loss simulation from an Excel file.

The required Excel format is described in

```
src/stes_tools/import_functions.py
```

---

### Storage classes

The central class is

```
STES
```

which provides the common functionality for all storage types.

It is implemented through the following subclasses.

### `PTES`

```python
PTES(
    h,
    a,
    b,
    c,
    d,
    n_layers,
    T_min,
    T_max,
    T_ref
)
```

Defines a Pit Thermal Energy Storage (PTES) system by specifying

- geometry
- number of temperature layers
- operating temperature range
- reference temperature

---

### `TTES`

```python
TTES(
    h,
    r,
    n_layers,
    T_min,
    T_max,
    T_ref
)
```

Defines a Tank Thermal Energy Storage (TTES) system.

---

### Temperature map

```
temperature_map(...)
```

Generates a stratified temperature distribution used during the heat-loss simulation.

The parameters controlling the temperature profile are explained in

```
notebooks/Heat_Loss_Simulation_of_PTES.ipynb
```

---

# Examples

## Water property functions

```python
import stes_tools as st

rho = st.density_water(T=25)
cp = st.specific_heat_water(T=25)

print(
    f"The density of water at 25°C is {round(rho)} kg/m³ "
    f"and the specific heat capacity is {round(cp)} J/(kg·K)."
)
```

Output

```text
The density of water at 25°C is 997 kg/m³ and the specific heat capacity is 4182 J/(kg·K).
```

---

## Cost functions

```python
import stes_tools as st

CAPEX = (
    st.CAPEX_STES(
        technology="PTES",
        unit="per_volume",
        capacity=70000,
        T_min=45,
        T_max=85,
    )
    * 70000
)

OPEX = CAPEX * st.OPEX_STES("PTES")

print(
    f"CAPEX: {round(CAPEX)} CHF\n"
    f"OPEX: {round(OPEX)} CHF/a"
)
```

Output

```text
CAPEX: 4522103 CHF
OPEX: 44560 CHF/a
```

---

## Heat-loss simulation

A complete example demonstrating the calibration and validation of the PTES model using operational data from the Dronninglund pit thermal storage can be found below.

*(Keep your existing example here. It is already well written.)*

Result:

- Black dashed: reported storage energy content
- Red: simulated storage energy content
- Blue dashed: Simple Storage Model (SSM)

The Mean Absolute Percentage Error (MAPE) quantifies the deviation between simulated and reported storage energy content.

---

# Installation

## Clone the repository

```bash
git clone https://github.com/mankae/techno-economic-stes-database.git
cd techno-economic-stes-database
```

---

## Create a virtual environment (recommended)

```bash
python -m venv .venv
```

Activate the environment.

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

---

## Install the package

```bash
pip install -e .
```

The package is installed in **editable mode**, allowing source code changes to be used immediately without reinstalling the package.

---

## Import

```python
import stes_tools as st
```

---

## Optional: Install development dependencies

```bash
pip install -e ".[dev]"
```

This installs the additional dependencies required to run the example notebooks.

---

## Repository structure

```
techno-economic-stes-database/
│
├── .venv/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── stes_tools/
│
├── notebooks/
│
└── figures/
```

---

# Documentation

Additional examples are available in the notebooks.

- **Cost function database**
  - `notebooks/CAPEX_OPEX_database_STES.ipynb`

- **Heat-loss simulation**
  - `notebooks/Heat_Loss_Simulation_of_PTES.ipynb`

---

# Data sources

The techno-economic data are compiled from published literature. References are provided throughout the source code.

The validation examples use operational data from the following open repositories:

- Høje Taastrup
- Dronninglund

---

# License

See the `LICENSE` file for licensing information.
