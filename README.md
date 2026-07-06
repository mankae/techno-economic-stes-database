# techno-economic-stes-database

This repository was created during a semester project "Seasonal Thermal Energy Storage: Recent Techno-Economic Developments and Modeling Approaches" at Eidgenössische Technische Hochschule Zürich (ETHZ). The motivation of the project was the modeling of Seasonal Thermal Energy Storage (STES) in optimization-based energy system models (ESMs)

The repository contains CAPEX and OPEX data for PTES, TTES, BTES, and ATES. There are functions (OPEX_STES() and CAPEX_STES()) to get the CAPEX and OPEX value of these technologies depending on the type of technology and its capacity.

There is also a simulation framework for simple heat-loss modeling of PTES and TTES. The goal of the simulation is, to describe the heat loss with a parameter called self-discharge rate ($\eta_{\mathrm{self}}$). This parameter can be used in the simple storage model (SSM) which is often used in ESM:

$$Q_{\mathrm{sto,t+1}}=\eta_{\mathrm{self}} \cdot Q_{\mathrm{sto,t}}+\left(\eta_{\mathrm{ch}} \cdot \dot{Q}_{\mathrm{ch}} -\frac{\dot{Q}_{\mathrm{disch}}}{\eta_{\mathrm{disch}}}\right) \cdot \Delta t$$

The python package stes-tools contains the cost data function and also the simulation framework to simulate heat loss of PTES and TTES. The following functions are contained within the package:

Water properties:
- density_water(T)
- specific_heat_water(T)

Cost data:
- CAPEX_STES(technology, unit, capacity, T_min, T_max): CAPEX for a given type of STES (PTES, TTES, BTES, ATES) based on the capacity and the unit of the capacity.
- OPEX_STES(technology): OPEX for a given type of STES (PTES, TTES, BTES, ATES)

Heat loss simulation:
- data_import(file_path): imports data from Excel file for heat loss simulation. Formatting requirements for the Excel file can be found [here](src/stes_tools/import_functions.py).
- STES: Is the class which is used to define the simulated storages. It is divided in the following two subclasses:
  - PTES(h, a, b, c, d, n_layers, T_min, T_max, T_ref): Define a PTES storage by defining the geometry (h, a, b, c, d), the number of layers, the temperature range (T_min to T_max) and the reference temperature
  - TTES(h, r, n_layers, T_min, T_max, T_ref): Define a TTES storage by defining the geometry (h, r), the number of layers, the temperature range (T_min to T_max) and the reference temperature.
 
The class and subclasses contain also functions. For more information, see the example below or [Heat loss simulation of PTES](notebooks/Heat_Loss_Simulation_of_PTES.ipynb).

- temperature_map(n_layers, T_min, T_mid, T_max, n_points, stretch, sharpness, overlap, plot): The temperature map is used to consider stratification in the storage. For more information on the input parameters, see [Heat loss simulation of PTES](notebooks/Heat_Loss_Simulation_of_PTES.ipynb)

## Examples

**Example for water property functions:**
```python
import stes_tools as st

# get the density and specific heat capacity of water at 25°C
rho = st.density_water(T=25)
c_p = st.specific_heat_water(T=25)
print("The density of water at 25°C is", round(rho), "kg/m^3 and the specific heat capacity", round(c_p), "J/(kg·K).")
```
**Output:**
```text
The density of water at 25°C is 997 kg/m^3 and the specific heat capacity 4182 J/(kg·K).
```
**Example cost functions:**
```python
import stes_tools as st

# get the CAPEX and OPEX value of a PTES plant
CAPEX = st.CAPEX_STES(technology='PTES', unit='per_volume', capacity=70000, T_min=45, T_max=85) * 70000
OPEX = CAPEX * st.OPEX_STES('PTES')
print("CAPEX of a PTES with a volume of 70000 m^3 and temperature range from 45°C to 85°C:", round(CAPEX), "CHF, OPEX of the same PTES:", round(OPEX), "CHF/a")
```
**Output:**
```text
CAPEX of a PTES with a volume of 70000 m^3 and temperature range from 45°C to 85°C: 4522103 CHF, OPEX of the same PTES: 44560 CHF/a
```
**Example for heat loss simulation:**
```python
import stes_tools as st

import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error

file_path = "dronninglund_data_2014.xlsx"

# geometry parameters for a truncated pyramid (Reference: https://doi.org/10.1016/j.energy.2018.03.152)
h, a, b, c, d = 16, 91, 91, 26, 26

dronninglund_PTES = st.PTES(h, a, b, c, d, n_layers=32, T_min=12, T_max=90, T_ref=10)
dronninglund_PTES.set_temperature_map(st.temperature_map(n_layers=32, T_min=12, T_mid=45, T_max=90, n_points=2000, stretch=1, sharpness=10, overlap=0.3, plot=False))

data = st.data_import(file_path)
Q_storage_2014 = data['Q_storage'].to_numpy() # Q_storage_2014 is used for validation of the PTES model for 2014.
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
plt.plot(time_2014, Q_storage_2014, label=r"$Q_{\mathrm{sto}}$", color="black", linestyle="dashed")
plt.scatter([time_2014_to_2017[699],time_2014_to_2017[1065],time_2014_to_2017[1430]], [Q_storage_end_2015,Q_storage_end_2016,Q_storage_end_2017], color="black", marker="x", label="_nolegend_")
plt.plot(time_2014_to_2017, Q_storage_sim_2014_to_2017, label=r"$Q_{\mathrm{sto,sim}}$", color="#C04F15", alpha=0.7)
plt.plot(time_2014_to_2017, Q_storage_ssm_2014_to_2017, label=r"$Q_{\mathrm{sto,ssm}}$", color="#4E95D9", linestyle="dashed", alpha=0.9)
plt.text(0.02, 0.975, f"MAPE = {mape_2014:.2f} %", transform=plt.gca().transAxes, fontsize=13, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
plt.xticks(rotation=90)
plt.title("Energy Content Dronninglund 2014 - 2017")
plt.ylabel(r"$Q_{\mathrm{sto}}$ [MWh]")
plt.legend(loc="upper right", labelspacing=0.4)
plt.grid()
plt.show()
```
**Output:**

<img src="figures/dronninglund_demo.png" alt="Dronninglund Demo" width="60%">
- black-dashed: reported data
- red: simulated data
- blue-dashed: data calculated with the SSM
The MAPE quantifies the deviation of the simulated data from the reported data

**More details on the python package:**
- [Cost function data treatment and example](notebooks/CAPEX_OPEX_database_STES.ipynb)
- [Heat loss simulation of PTES](notebooks/Heat_Loss_Simulation_of_PTES.ipynb)

## Installation guide:

1. Clone the repository from GitHub (git bash):

```bash
git clone https://github.com/mankae/techno-economic-stes-database.git
```

2. Move into the project folder:

```bash
cd techno-economic-stes-database
```

3. It is recommended to use a separate Python environment:

```bash
python -m venv .venv
```

Activate the environment.

On Windows:
```bash
.venv\Scripts\activate
```
On Linux/macOS:
```bash
source .venv/bin/activate
```

4. Install the package in editable mode:
```bash
pip install -e .
```

5. The package can now be imported:
```python
import stes_tools as st
```

### Install development dependencies (optional)

To run the notebooks:

```bash
pip install -e ".[dev]"
```

**Illustration where to create virtual environment**

```markdown
 techno-economic-stes-database/ ← run commands 2. to 5. here
  │
  ├── .venv/                    ← created in step 3.
  │
  ├── pyproject.toml             
  ├── README.md
  ├── LICENSE
  ├── src/
  │   └── stes_tools/
  └── notebooks/
```

## Comment on used data:

The references of the used data is mentioned in the code. The most important data sources were two git repositories containing PTES operational data ([Høje Taastrup](https://github.com/PitStorages/HojeTaastrupData), [Dronninglund](https://github.com/PitStorages/DronninglundData))

