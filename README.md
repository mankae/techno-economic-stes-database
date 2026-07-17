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

The package provides functions to estimate investment and operating costs based on the selected technology and storage capacity. The database can be found [here](notebooks/STES_CAPEX_OPEX_database.xlsx).

## Heat-loss simulation

The package includes a simulation framework for modelling heat losses in PTES and TTES systems.

The simulation derives an effective **self-discharge rate** ($\eta_{\mathrm{self}}$), which can be directly used in the Simple Storage Model (SSM) frequently employed in optimization-based energy system models (ESMs):

$$Q_{\mathrm{sto,t+1}}=\eta_{\mathrm{self}} \cdot Q_{\mathrm{sto,t}}+\eta_{\mathrm{ch}} \cdot Q_{\mathrm{ch}} -\frac{Q_{\mathrm{disch}}}{\eta_{\mathrm{disch}}}$$

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
- storage capacity and its unit
- (temperature range)

The temperature range is an optional input. If it is not known, predefined energy density values are used. Supported technologies: (PTES, TTES, BTES, ATES)

---

### `OPEX_STES(technology)`

Returns the annual OPEX factor for the selected STES technology.

---

## Heat-loss simulation

### `data_import(file_path)`

Imports the operational data required for the heat-loss simulation from an Excel file.

The required Excel format is described in [
notebooks/Heat_Loss_Simulation_of_PTES.ipynb](notebooks/Heat_Loss_Simulation_of_PTES.ipynb)

### `temperature_map(n_layers, T_min, T_mid, T_max, n_points, stretch, sharpness, overlap, plot)`

Generates a stratified temperature distribution depending on the energy content of the storage used during the heat-loss simulation.

The parameters controlling the temperature profile are explained in [
notebooks/Heat_Loss_Simulation_of_PTES.ipynb](notebooks/Heat_Loss_Simulation_of_PTES.ipynb)

### `simulate_storage_simple(eta, Q_charge, Q_discharge, Q_storage_start)`

This function executes a heat loss simulation using a SSM and no knowledge about the capacity or type of the storage.

### Storage classes

The central class is `STES` which provides the common functionality for all storage types.

It is implemented through the following subclasses.

### `PTES`

```python
PTES(h,a,b,c,d,n_layers,T_min,T_max,T_ref)
```

Defines a Pit Thermal Energy Storage (PTES) system by specifying

- geometry (truncated and inverted pyramid)
- number of temperature layers
- operating temperature range
- reference temperature

### `TTES`

```python
TTES(h,r,n_layers,T_min,T_max,T_ref)
```

Defines a Tank Thermal Energy Storage (TTES) system

- geometry (cylinder)
- number of temperature layers
- operating temperature range
- reference temperature

### Functions of storage classes

- `.compute_energy_bounds()`: calculates `Q_min` and `Q_max` for a storage with defined temperature range and volume
- `.set_temperature_map(T_curves)`: links a temperature map to the storage. `T_curves` is a matrix containing vectors of temperature values for each layer at energy contents of the storage between `Q_min` and `Q_max`
- `.get_temperature_layers(Q_storage)`: is used to get a vector of the temperatures of each layer as a function of the energy content `Q_storage`
- `.set_U_values(U_lid, U_side, U_bottom)`: is used to set the U-values at the surfaces of the storage

### `PTES` specific functions
- `.volume_truncated_pyramid(h, a, b, c, d)`: is used to calculate the volume for a typical PTES
- `.volume_per_layer_truncated_pyramid(h, a, b, c, d, n)`: is used to calculate the volume of each layer for a typical PTES
- `.surface_area_truncated_pyramid(h, a, b, c, d)`: is used to calculate the surface areas for a typical PTES
- `.surface_area_per_layer_truncated_pyramid(h, a, b, c, d, n)`: is used to calculate the surface areas of each layer for a typical PTES
- `.simulate_PTES(file_path, Q_storage_start, sim_start=None, sim_end=None)`: this is the function which is used for the heat loss simulation. Additionaly the best fitting self-discharge rate is calculated
- `.calculate_U_values_PTES(file_path,Q_storage_start,Q_storage_end,share_loss_lid,share_loss_side,share_loss_bottom,start_idx=None,end_idx=None)`: this function calculates U-values based on reported data. It can be used to calibrate a storage. For that, the shares of heat lost through the lid, sides, and bottom must be known.

### `TTES` specific functions
- `.volume_cylinder(h, r)`: is used to calculate the volume for a typical TTES
- `.volume_per_layer(h, r, n)`: is used to calculate the volume of each layer for a typical TTES
- `.surface_area_cylinder(h, r)`: is used to calculate the surface areas for a typical TTES
- `.surface_area_per_layer(h, r, n)`: is used to calculate the surface areas of each layer for a typical TTES

---

# Examples

## Water property functions

```python
import stes_tools as st

rho = st.density_water(T=25)
cp = st.specific_heat_water(T=25)

print(f"The density of water at 25°C is {round(rho)} kg/m³ and the specific heat capacity is {round(cp)} J/(kg·K).")
```

Output

```text
The density of water at 25°C is 997 kg/m³ and the specific heat capacity is 4182 J/(kg·K).
```

---

## Cost functions

```python
import stes_tools as st

CAPEX = st.CAPEX_STES(technology="PTES",unit="per_volume",capacity=70000,T_min=45,T_max=85) * 70000
OPEX = CAPEX * st.OPEX_STES("PTES")

print(f"CAPEX: {round(CAPEX)} CHF")
print(f"OPEX: {round(OPEX)} CHF/a")
```

Output

```text
CAPEX: 4522103 CHF
OPEX: 44560 CHF/a
```

---

## Heat-loss simulation

A complete example demonstrating the calibration and validation of the PTES model using operational data from the Dronninglund pit thermal storage can be found below.

```python
import stes_tools as st

import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error

file_path = "dronninglund_data_2014.xlsx"

# geometry parameters for a truncated pyramid (Reference: https://doi.org/10.1016/j.energy.2018.03.152)
h, a, b, c, d = 16, 91, 91, 26, 26

# define PTES storage and temperature map
dronninglund_PTES = st.PTES(h, a, b, c, d, n_layers=32, T_min=12, T_max=90, T_ref=10)
dronninglund_PTES.set_temperature_map(st.temperature_map(n_layers=32, T_min=12, T_mid=45, T_max=90, n_points=2000, stretch=1, sharpness=10, overlap=0.3, plot=False))

data = st.data_import(file_path)
Q_storage_2014 = data['Q_storage'].to_numpy()

# Q_storage_2014 is used for validation of the PTES model for 2014.
Q_storage_2014 = Q_storage_2014[30:] # the first 30 days are ignored because data quality is bad
Q_storage_start_2014 = Q_storage_2014[0]
Q_storage_end_2014 = Q_storage_2014[-1]

# calculate the heat transfer coefficients of the PTES model based on the storage energy content for 2014.
dronninglund_PTES.calculate_U_values_PTES(file_path, Q_storage_start_2014, Q_storage_end_2014, 0.56, 0.42, 0.02, 30, None)

# simulate PTES for 2014.
time_2014, Q_storage_sim_2014, Q_loss_sim_2014, Q_storage_ssm_2014 = dronninglund_PTES.simulate_PTES(file_path, Q_storage_start=Q_storage_start_2014, sim_start=30)

# defining the starting point of the simulation for 2015-2017.
Q_storage_start_2015_to_2017 = Q_storage_sim_2014[-1]

new_file_path = "dronninglund_data_2015_to_2017.xlsx"

# simulate PTES for 2015-2017.
time_2015_to_2017, Q_storage_sim_2015_to_2017, Q_loss_sim_2015_to_2017, Q_storage_ssm_2015_to_2017 = dronninglund_PTES.simulate_PTES(new_file_path, Q_storage_start=Q_storage_start_2015_to_2017)

# Combine the simulated storage energy content for 2014-2017.
Q_storage_sim_2014_to_2017 = np.concatenate((Q_storage_sim_2014, Q_storage_sim_2015_to_2017))
Q_storage_ssm_2014_to_2017 = np.concatenate((Q_storage_ssm_2014, Q_storage_ssm_2015_to_2017))
time_2014_to_2017 = np.concatenate((time_2014, time_2015_to_2017))

# Validation points for 2015-2017 based on the reported data at the end of each year.
Q_storage_end_2014 = 1663 + Q_storage_start_2014
Q_storage_end_2015 = Q_storage_end_2014 - 497
Q_storage_end_2016 = Q_storage_end_2015 + 93
Q_storage_end_2017 = Q_storage_end_2016 - 583

# calculate the mean absolute percentage error (MAPE) between the simulated and reported storage energy content for 2014
mape_2014 = mean_absolute_error(Q_storage_2014,Q_storage_sim_2014) / np.nanmean(Q_storage_2014) * 100

# plotting
plt.plot(time_2014, Q_storage_2014, label=r"$Q_{\mathrm{sto}}$", color="black", linestyle="dashed") plt.scatter([time_2014_to_2017[699],time_2014_to_2017[1065],time_2014_to_2017[1430]], [Q_storage_end_2015,Q_storage_end_2016,Q_storage_end_2017], color="black", marker="x", label="_nolegend_")
plt.plot(time_2014_to_2017, Q_storage_sim_2014_to_2017, label=r"$Q_{\mathrm{sto,sim}}$", color="#C04F15", alpha=0.7)
plt.plot(time_2014_to_2017, Q_storage_ssm_2014_to_2017, label=r"$Q_{\mathrm{sto,ssm}}$", color="#4E95D9", linestyle="dashed", alpha=0.9)
plt.text(0.02, 0.975, f"MAPE = {mape_2014:.2f} %", transform=plt.gca().transAxes, fontsize=13, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)) plt.xticks(rotation=90)
plt.title("Energy Content Dronninglund 2014 - 2017")
plt.ylabel(r"$Q_{\mathrm{sto}}$ [MWh]")
plt.legend(loc="upper right", labelspacing=0.4)
plt.grid()
plt.show()
```

Result:

<img src="figures/dronninglund_demo.png" alt="Dronninglund Demo" width="60%">

- Black dashed: reported storage energy content
- Red: simulated storage energy content
- Blue dashed: Simple Storage Model (SSM)

The Mean Absolute Percentage Error (MAPE) quantifies the deviation between simulated and reported storage energy content.

```python
print(f"Self-discharge rate: {dronninglund_PTES.eta_self_discharge * 100:.2f} % per day")
```

```text
Self-discharge rate: 0.12 % per day
```

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
  - [notebooks/CAPEX_OPEX_database_STES.ipynb](notebooks/CAPEX_OPEX_database_STES.ipynb)

- **Heat-loss simulation**
  - [notebooks/Heat_Loss_Simulation_of_PTES.ipynb](notebooks/Heat_Loss_Simulation_of_PTES.ipynb)

---

# Data sources

The techno-economic data are compiled from published literature. References are provided throughout the source code.

The validation examples use operational data from the following open repositories:

- [Høje Taastrup](https://github.com/PitStorages/HojeTaastrupData)
- [Dronninglund](https://github.com/PitStorages/DronninglundData)

---

# License

See the `LICENSE` file for licensing information.
