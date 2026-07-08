import numpy as np
from scipy.optimize import minimize

from .import_functions import data_import
from .H2O_prop import density_water, specific_heat_water


# =====================================================================
# BASE CLASS: STES (Seasonal Thermal Energy Storage)
# =====================================================================

class STES:
    """
    Abstract base class for seasonal thermal energy storage (STES) models.

    Provides shared attributes and methods for geometry-specific subclasses
    (e.g. PTES for pit storage, TTES for tank storage). Subclasses must
    define the geometry-dependent attributes (volumes, areas) in their
    own __init__ before calling compute_energy_bounds().
    """

    def __init__(self, n_layers, T_min=12, T_max=90, T_ref=10):
        """
        Parameters
        ----------
        n_layers : int
            Number of horizontal layers used to discretize the storage volume.
            Corresponds to the number of temperature sensors in a real installation.
        T_min : float
            Minimum (cold) storage temperature [°C].
        T_max : float
            Maximum (hot) storage temperature [°C].
        T_ref : float
            Reference temperature for calculating stored energy content [°C].
            Typically the undisturbed ground or mains water temperature.
        """
        self.n_layers = n_layers
        self.T_min = T_min
        self.T_max = T_max
        self.T_ref = T_ref

        # --- Geometry (must be set by subclasses before use) ---
        self.V_storage = None       # Total storage volume [m³]
        self.V_layer = None         # Volume of each layer [m³], shape (n_layers,)
        self.A_side = None          # Total side surface area [m²]
        self.A_top = None           # Lid / top surface area [m²]
        self.A_bottom = None        # Bottom surface area [m²]
        self.A_side_layers = None   # Side area per layer [m²], shape (n_layers,)

        # --- Energy bounds (computed from geometry + temperatures) ---
        self.Q_storage_max = None   # Maximum stored energy at T_max [MWh]
        self.Q_storage_min = None   # Minimum stored energy at T_min [MWh]

        # --- Temperature map (set via set_temperature_map) ---
        self.T_curves = None        # Synthetic temperature profiles, shape (n_layers, n_points)
        self.T_curves_Q = None      # Energy content at each profile point [MWh], shape (n_points,)

        # --- Thermal loss parameters ---
        self.U_lid = None           # U-value of the lid [W/m²K]
        self.U_side = None          # U-value of the side walls [W/m²K]
        self.U_bottom = None        # U-value of the bottom [W/m²K]

        self.eta_self_discharge = None  # Fitted self-discharge rate per timestep [-]

    def compute_energy_bounds(self):
        """
        Compute Q_storage_max and Q_storage_min from the storage volume,
        water properties at T_max / T_min, and the reference temperature.

        Result is stored in MWh (dividing J by 3.6e9).
        Called automatically by subclass __init__ after geometry is set.
        """
        self.Q_storage_max = (
            self.V_storage
            * density_water(self.T_max)
            * specific_heat_water(self.T_max)
            * (self.T_max - self.T_ref)
            / 3.6e9
        )
        self.Q_storage_min = (
            self.V_storage
            * density_water(self.T_min)
            * specific_heat_water(self.T_min)
            * (self.T_min - self.T_ref)
            / 3.6e9
        )

    def set_temperature_map(self, T_curves):
        """
        Register a synthetic temperature map and pre-compute the
        corresponding energy content curve used for look-ups in
        get_temperature_layers().

        Parameters
        ----------
        T_curves : np.ndarray, shape (n_layers, n_points)
            Temperature [°C] at each layer for each charging state.
            Rows = layers (index 0 = top/hot), columns = time/charge points.
        """
        self.T_curves = T_curves

        # Water properties evaluated at every (layer, point) temperature
        rho_water = density_water(self.T_curves)    # [kg/m³]
        cp_water  = specific_heat_water(self.T_curves)  # [J/kgK]

        # Integrate over layers: Q [MWh] = sum_layers( V_layer * rho * cp * ΔT ) / 3.6e9
        # V_layer is a 1-D array, so @ performs a dot product over the layer axis.
        self.T_curves_Q = (
            self.V_layer @ (rho_water * cp_water * (self.T_curves - self.T_ref))
            / 3.6e9
        )

    def get_temperature_layers(self, Q_storage):
        """
        Return the layered temperature profile [°C] corresponding to
        a given storage energy content Q_storage [MWh] by linear
        interpolation in the pre-computed temperature map.

        If Q_storage falls outside [Q_storage_min, Q_storage_max], a
        uniform temperature profile is returned and a warning is printed.

        Parameters
        ----------
        Q_storage : float
            Current storage energy content [MWh].

        Returns
        -------
        T_layer : np.ndarray, shape (n_layers,)
            Temperature profile [°C], index 0 = top layer.
        """
        if self.Q_storage_min <= Q_storage <= self.Q_storage_max:

            # Find the two map columns that bracket Q_storage
            Q_1_idx = np.where(self.T_curves_Q <= Q_storage)[0][
                np.argmax(self.T_curves_Q[self.T_curves_Q <= Q_storage])
            ]
            Q_2_idx = np.where(self.T_curves_Q >= Q_storage)[0][
                np.argmin(self.T_curves_Q[self.T_curves_Q >= Q_storage])
            ]

            # Linear interpolation between the two bracketing profiles
            if self.T_curves_Q[Q_2_idx] != self.T_curves_Q[Q_1_idx]:
                T_layer = (
                    self.T_curves[:, Q_1_idx]
                    + (self.T_curves[:, Q_2_idx] - self.T_curves[:, Q_1_idx])
                    * (Q_storage - self.T_curves_Q[Q_1_idx])
                    / (self.T_curves_Q[Q_2_idx] - self.T_curves_Q[Q_1_idx])
                )
            else:
                # Duplicate point — no interpolation needed
                T_layer = self.T_curves[:, Q_1_idx]

        else:
            # Out-of-bounds: assume a fully mixed (uniform) storage
            print("WARNING: Q_storage is not between Q_storage_min and Q_storage_max")
            if Q_storage <= self.Q_storage_min:
                T_uniform = (
                    Q_storage * 3.6e9
                    / self.V_storage
                    / density_water(self.T_min)
                    / specific_heat_water(self.T_min)
                    + self.T_ref
                )
            else:
                T_uniform = (
                    Q_storage * 3.6e9
                    / self.V_storage
                    / density_water(self.T_max)
                    / specific_heat_water(self.T_max)
                    + self.T_ref
                )
            T_layer = np.full(self.T_curves.shape[0], T_uniform)

        return T_layer.T

    def set_U_values(self, U_lid, U_side, U_bottom):
        """
        Manually set thermal loss coefficients [W/m²K].

        Parameters
        ----------
        U_lid    : float  U-value of the lid/top surface.
        U_side   : float  U-value of the side walls.
        U_bottom : float  U-value of the bottom surface.
        """
        self.U_lid    = U_lid
        self.U_side   = U_side
        self.U_bottom = U_bottom


# =====================================================================
# STANDALONE SIMPLE STORAGE MODEL
# =====================================================================
#
# Extracted from PTES.simulate_PTES so it can be reused on its own,
# without running the full (slow) detailed simulation first. Behavior
# is unchanged from the original nested function.

def simulate_storage_simple(eta, Q_charge, Q_discharge, Q_storage_start):
    """
    Simple self-discharge storage model.

        Q_simple[t] = (1 - eta) * Q_simple[t-1] + Q_charge[t] - Q_discharge[t]

    Parameters
    ----------
    eta : float
        Fractional self-discharge loss per timestep [-].
    Q_charge : array-like
        Charging energy per timestep [MWh].
    Q_discharge : array-like
        Discharging energy per timestep [MWh].
    Q_storage_start : float
        Storage energy content used to seed Q_simple[-1], i.e. the
        value the recursion wraps around from at t=0, matching the
        convention used in simulate_PTES.

    Returns
    -------
    Q_simple : np.ndarray
        Simulated storage energy content [MWh], same length as Q_charge.
    """
    Q_charge    = np.asarray(Q_charge)
    Q_discharge = np.asarray(Q_discharge)

    Q_simple     = np.zeros_like(Q_charge, dtype=float)
    Q_simple[-1] = Q_storage_start  # seed the wrap-around index

    for t in range(len(Q_charge)):
        Q_simple[t] = (1 - eta) * Q_simple[t - 1] + Q_charge[t] - Q_discharge[t]

    return Q_simple

# def calculate_self_discharge_yearly(file_path, Q_storage_start_by_year, Q_storage_end_by_year):
#     """
#     Fit a self-discharge rate (eta) for each calendar year independently,
#     using only the fast simple model (no detailed heat-loss simulation).
 
#     For each year, eta is chosen so that the simple model's energy
#     content at the final timestep matches Q_storage_end_by_year[year].
#     The relative squared error is minimized to make the result
#     scale-invariant across years with different storage levels.
 
#     Moved out of PTES: this only depends on data_import and
#     simulate_storage_simple, and doesn't use any storage geometry
#     (self.V_storage, self.get_temperature_layers, etc.), so it doesn't
#     need to be a bound method on a PTES/STES instance.
 
#     Parameters
#     ----------
#     file_path                : str   Path to the input data file.
#     Q_storage_start_by_year  : dict  {year: Q_start [MWh]}
#     Q_storage_end_by_year    : dict  {year: Q_end   [MWh]}
 
#     Returns
#     -------
#     results : dict
#         {
#             year: {
#                 "eta_self_discharge":    float,
#                 "time":                  DatetimeIndex for that year,
#                 "Q_storage_simple":      np.ndarray [MWh],
#                 "optimization_success":  bool,
#                 "optimization_message":  str,
#             }
#         }
#     """
#     data  = data_import(file_path)
#     years = np.array(data.index.year)
 
#     results = {}
 
#     for year, Q_storage_start in Q_storage_start_by_year.items():
 
#         if year not in Q_storage_end_by_year:
#             continue  # skip years without a target end value
 
#         Q_storage_end = Q_storage_end_by_year[year]
 
#         # Slice all arrays to this calendar year
#         idx = np.where(years == year)[0]
#         if len(idx) == 0:
#             continue
 
#         time_year        = data.index[idx]
#         Q_charge_year    = data['Q_charge'].to_numpy()[idx]
#         Q_discharge_year = data['Q_discharge'].to_numpy()[idx]

def calculate_self_discharge_yearly(time, Q_charge, Q_discharge, Q_storage_start_by_year, Q_storage_end_by_year):
    """
    Fit a self-discharge rate (eta) for each calendar year independently,
    using only the simple storage model (no detailed heat-loss simulation).

    For each year, eta is chosen so that the simple model's energy
    content at the final timestep matches Q_storage_end_by_year[year].
    The relative squared error is minimized to make the result
    scale-invariant across years with different storage levels.

    Moved out of PTES: this only depends on simulate_storage_simple,
    and doesn't use any storage geometry (self.V_storage,
    self.get_temperature_layers, etc.), so it doesn't need to be a
    bound method on a PTES/STES instance.

    Parameters
    ----------
    time                     : DatetimeIndex  Full time axis, same length as Q_charge/Q_discharge.
    Q_charge                 : array-like     Charging energy per timestep [MWh].
    Q_discharge              : array-like     Discharging energy per timestep [MWh].
    Q_storage_start_by_year  : dict  {year: Q_start [MWh]}
    Q_storage_end_by_year    : dict  {year: Q_end   [MWh]}

    Returns
    -------
    results : dict
        {
            year: {
                "eta_self_discharge":    float,
                "time":                  DatetimeIndex for that year,
                "Q_storage_simple":      np.ndarray [MWh],
                "optimization_success":  bool,
                "optimization_message":  str,
            }
        }
    """
    Q_charge    = np.asarray(Q_charge)
    Q_discharge = np.asarray(Q_discharge)
    years       = np.array(time.year)

    results = {}

    for year, Q_storage_start in Q_storage_start_by_year.items():

        if year not in Q_storage_end_by_year:
            continue  # skip years without a target end value

        Q_storage_end = Q_storage_end_by_year[year]

        # Slice all arrays to this calendar year
        idx = np.where(years == year)[0]
        if len(idx) == 0:
            continue

        time_year        = time[idx]
        Q_charge_year    = Q_charge[idx]
        Q_discharge_year = Q_discharge[idx]

        # ... rest unchanged (loss_function, minimize, results[year] = {...})
 
        # Minimize relative squared end-of-year error
        def loss_function(
            eta,
            Q_charge_year=Q_charge_year,
            Q_discharge_year=Q_discharge_year,
            Q_storage_start=Q_storage_start,
            Q_storage_end=Q_storage_end,
        ):
            eta      = float(eta[0])
            Q_simple = simulate_storage_simple(eta, Q_charge_year, Q_discharge_year, Q_storage_start)
            rel_error = (Q_simple[-1] - Q_storage_end) / Q_storage_end
            return rel_error**2
 
        result  = minimize(loss_function, x0=[0.01], bounds=[(0, 1)])
        eta_opt = float(result.x[0])
 
        Q_storage_simple_year = simulate_storage_simple(
            eta_opt, Q_charge_year, Q_discharge_year, Q_storage_start
        )
 
        results[year] = {
            "eta_self_discharge":   eta_opt,
            "time":                 time_year,
            "Q_storage_simple":     Q_storage_simple_year,
            "optimization_success": result.success,
            "optimization_message": result.message,
        }
 
    return results


# =====================================================================
# PTES — PIT THERMAL ENERGY STORAGE (truncated-pyramid geometry)
# =====================================================================

class PTES(STES):
    """
    Pit Thermal Energy Storage with a truncated-pyramid (trapezoidal
    cross-section) geometry.

    The pit is described by its depth h and the dimensions of its
    rectangular top (a × b) and bottom (c × d) faces.
    """

    def __init__(self, h, a, b, c, d, n_layers, T_min=12, T_max=90, T_ref=10):
        """
        Parameters
        ----------
        h        : float  Pit depth [m].
        a, b     : float  Top face dimensions (length × width) [m].
        c, d     : float  Bottom face dimensions (length × width) [m].
        n_layers : int    Number of horizontal discretization layers.
        T_min    : float  Minimum storage temperature [°C].
        T_max    : float  Maximum storage temperature [°C].
        T_ref    : float  Reference temperature for energy calculations [°C].
        """
        super().__init__(n_layers, T_min, T_max, T_ref)

        self.h, self.a, self.b, self.c, self.d = h, a, b, c, d

        # Total volume and per-layer volumes (flipped: index 0 = top)
        self.V_storage = self.volume_truncated_pyramid(h, a, b, c, d)
        self.V_layer   = np.flip(self.volume_per_layer_truncated_pyramid(h, a, b, c, d, n_layers))

        # Surface areas
        self.A_side, self.A_bottom, self.A_top = self.surface_area_truncated_pyramid(h, a, b, c, d)

        # Per-layer side areas (flipped to match V_layer ordering)
        self.A_side_layers = np.flip(self.surface_area_per_layer_truncated_pyramid(h, a, b, c, d, n_layers))

        self.compute_energy_bounds()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def volume_truncated_pyramid(self, h, a, b, c, d):
        """
        Volume of a truncated rectangular pyramid [m³].
        Formula: V = h/6 * ((2a+c)*b + (2c+a)*d)
        Reference: https://doi.org/10.1016/j.energy.2018.03.152
        """
        return (h / 6) * ((2 * a + c) * b + (2 * c + a) * d)

    def volume_per_layer_truncated_pyramid(self, h, a, b, c, d, n):
        """
        Split the truncated pyramid into n equal-height layers and
        return each layer's volume [m³].  Layers are ordered bottom→top.
        """
        volume_per_layer = []

        diff_a_c = (a - c) / n   # linear taper per layer (length direction)
        diff_b_d = (b - d) / n   # linear taper per layer (width direction)
        h_layer  = h / n

        cx, dx = c, d  # start from the bottom face

        for _ in range(n):
            ax = cx + diff_a_c
            bx = dx + diff_b_d
            V  = self.volume_truncated_pyramid(h_layer, ax, bx, cx, dx)
            volume_per_layer.append(float(V))
            cx, dx = ax, bx  # step up one layer

        return volume_per_layer

    def surface_area_truncated_pyramid(self, h, a, b, c, d):
        """
        Side, bottom, and top surface areas of a truncated rectangular
        pyramid [m²].
        Reference: https://doi.org/10.1016/j.energy.2018.03.152

        Returns
        -------
        A_side   : float  Total slanted side area.
        A_bottom : float  Bottom face area (c × d).
        A_top    : float  Top face area    (a × b).
        """
        A_side = (
            (a + c) * ((h**2) + ((a - c) / 2)**2)**0.5
            + (b + d) * ((h**2) + ((b - d) / 2)**2)**0.5
        )
        return A_side, c * d, a * b

    def surface_area_per_layer_truncated_pyramid(self, h, a, b, c, d, n):
        """
        Side surface area for each of the n equal-height layers [m²].
        Ordered bottom→top (same order as volume_per_layer_*).
        """
        surface_area_per_layer = []

        diff_a_c = (a - c) / n
        diff_b_d = (b - d) / n
        h_layer  = h / n

        cx, dx = c, d

        for _ in range(n):
            ax = cx + diff_a_c
            bx = dx + diff_b_d
            A  = self.surface_area_truncated_pyramid(h_layer, ax, bx, cx, dx)[0]
            surface_area_per_layer.append(float(A))
            cx, dx = ax, bx

        return surface_area_per_layer

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_PTES(self, file_path, Q_storage_start, sim_start=None, sim_end=None):
        """
        Run the detailed day-by-day PTES simulation and fit a simple
        self-discharge model to the result.

        For each timestep the layered temperature profile is looked up
        from the temperature map, heat losses through lid, side, and
        bottom are computed, and the storage energy balance is updated.

        After the detailed simulation, scipy.optimize.minimize fits a
        single eta parameter so that simulate_storage_simple reproduces
        the detailed Q_storage trajectory as closely as possible (MSE).

        Parameters
        ----------
        file_path       : str    Path to the input data file.
        Q_storage_start : float  Initial storage energy content [MWh].
        sim_start       : int    Start slice index into data (None = beginning).    If Q_storage_start is not to the same time as the first row of data (e.g. T_air, T_soil, Q_charge, Q_discharge)
        sim_end         : int    End slice index into data   (None = end).          If simulation end for Q_storage is not to the same time as the last row of data (e.g. T_air, T_soil, Q_charge, Q_discharge)

        Returns
        -------
        time              : DatetimeIndex  Simulation time axis.
        Q_storage_sim     : np.ndarray     Detailed storage energy [MWh].
        Q_loss_sim        : np.ndarray     Heat loss per timestep [MWh].
        Q_storage_simple  : np.ndarray     Simple-model energy [MWh].
        """
        data = data_import(file_path)

        # Slice to the requested simulation window
        time        = data.index[sim_start:sim_end]
        Q_charge    = data['Q_charge'].to_numpy()[sim_start:sim_end]
        Q_discharge = data['Q_discharge'].to_numpy()[sim_start:sim_end]
        T_air       = data['T_air'].to_numpy()[sim_start:sim_end]
        T_soil      = data['T_soil'].to_numpy()[sim_start:sim_end]

        # Derive the timestep size from the time index [hours]
        hours     = time.view('int64') / 1e6 / 3600
        time_step = (hours[-1] - hours[0]) / time.shape[0]

        Q_loss_sim        = np.zeros_like(Q_charge)
        Q_storage_sim     = np.zeros_like(Q_charge)
        Q_storage_sim[-1] = Q_storage_start  # wrap-around seed (same convention as simple model)

        for i in range(len(Q_storage_sim)):

            # Temperature profile from the previous timestep's storage state
            T_layers = self.get_temperature_layers(Q_storage_sim[i - 1])

            # Area-weighted average side temperature for side-wall loss calculation
            T_side_average = np.nansum(T_layers * self.A_side_layers / self.A_side)
            T_bottom = T_layers[-1]  # bottom layer (coldest)
            T_top    = T_layers[0]   # top layer    (hottest)

            # Heat loss through each boundary [MWh] = U * A * ΔT * Δt / 1e6
            Q_loss_sim[i] = (
                self.U_lid    * self.A_top    * (T_top           - T_air[i])  * time_step / 1e6
                + self.U_side   * self.A_side   * (T_side_average  - T_soil[i]) * time_step / 1e6
                + self.U_bottom * self.A_bottom * (T_bottom         - T_soil[i]) * time_step / 1e6
            )

            # Energy balance: Q[t] = Q[t-1] + charge - discharge - loss
            Q_storage_sim[i] = Q_storage_sim[i - 1] + Q_charge[i] - Q_discharge[i] - Q_loss_sim[i]

        # --- Fit simple self-discharge model to the detailed result ---
        def loss_function(eta):
            eta      = float(eta[0])
            Q_simple = simulate_storage_simple(eta, Q_charge, Q_discharge, Q_storage_start)
            return np.nanmean((Q_simple - Q_storage_sim)**2)

        result              = minimize(loss_function, x0=[0.01], bounds=[(0, 1)])
        eta_self_discharge  = result.x[0]
        Q_storage_simple    = simulate_storage_simple(eta_self_discharge, Q_charge, Q_discharge, Q_storage_start)

        self.eta_self_discharge = eta_self_discharge

        return time, Q_storage_sim, Q_loss_sim, Q_storage_simple

    def calculate_U_values_PTES(
        self,
        file_path,
        Q_storage_start,
        Q_storage_end,
        share_loss_lid=0.56,
        share_loss_side=0.41,
        share_loss_bottom=0.03,
        start_idx=None,
        end_idx=None,
    ):
        """
        Calibrate U-values (lid, side, bottom) by matching:
          1. The simulated final storage energy to Q_storage_end.
          2. The fractional heat-loss shares through each boundary to
             the user-supplied target shares.

        The optimization uses L-BFGS-B with physically sensible bounds
        (0.01–2.0 W/m²K per surface).

        Parameters
        ----------
        file_path        : str    Path to the input data file.
        Q_storage_start  : float  Storage energy at start of period [MWh].
        Q_storage_end    : float  Measured storage energy at end of period [MWh].
        share_loss_lid   : float  Target fraction of total loss through the lid [-].
        share_loss_side  : float  Target fraction of total loss through the side [-].
        share_loss_bottom: float  Target fraction of total loss through the bottom [-].
        start_idx        : int    Start slice index into data (None = beginning).
        end_idx          : int    End slice index into data   (None = end).

        Returns
        -------
        dict with keys:
            U_lid, U_side, U_bottom     : calibrated U-values [W/m²K]
            Q_storage_sim               : np.ndarray of simulated storage energy [MWh]
            Q_loss                      : np.ndarray of total loss per timestep [MWh]
            optimization_success        : bool
            optimization_message        : str
        """

        # --- Normalize loss shares so they always sum to 1 ---
        total_share       = share_loss_lid + share_loss_side + share_loss_bottom
        share_loss_lid    /= total_share
        share_loss_side   /= total_share
        share_loss_bottom /= total_share

        # --- Load and slice data ---
        data        = data_import(file_path)
        time        = data.index[start_idx:end_idx]
        T_air       = data['T_air'].to_numpy()[start_idx:end_idx]
        T_soil      = data['T_soil'].to_numpy()[start_idx:end_idx]
        Q_charge    = data['Q_charge'].to_numpy()[start_idx:end_idx]
        Q_discharge = data['Q_discharge'].to_numpy()[start_idx:end_idx]

        hours     = time.view('int64') / 1e6 / 3600
        time_step = (hours[-1] - hours[0]) / time.shape[0]
        n         = len(time)

        # --- Initial guesses and bounds ---
        # Typical large PTES U-values (W/m²K):
        #   lid:    0.2–0.6   side:  0.1–0.4   bottom: 0.1–0.3
        k0     = np.array([0.35, 0.20, 0.15])
        bounds = [(0.01, 2.0)] * 3  # (lid, side, bottom)

        # --- Forward simulation given a set of U-values ---
        def simulate_storage(U_values):
            U_lid, U_side, U_bottom = U_values

            Q_storage_sim        = np.zeros(n)
            Q_storage_sim[0]     = Q_storage_start
            Q_loss               = np.zeros(n)
            Q_loss_lid_array     = np.zeros(n)
            Q_loss_side_array    = np.zeros(n)
            Q_loss_bottom_array  = np.zeros(n)

            for i in range(1, n):
                T_layers = self.get_temperature_layers(Q_storage_sim[i - 1])

                T_side_average = np.nansum(T_layers * self.A_side_layers / self.A_side)
                T_bottom       = T_layers[-1]
                T_top          = T_layers[0]

                Q_loss_lid_i    = U_lid    * self.A_top    * (T_top          - T_air[i])  * time_step / 1e6
                Q_loss_side_i   = U_side   * self.A_side   * (T_side_average - T_soil[i]) * time_step / 1e6
                Q_loss_bottom_i = U_bottom * self.A_bottom * (T_bottom        - T_soil[i]) * time_step / 1e6

                Q_loss_lid_array[i]    = Q_loss_lid_i
                Q_loss_side_array[i]   = Q_loss_side_i
                Q_loss_bottom_array[i] = Q_loss_bottom_i

                Q_loss[i] = Q_loss_lid_i + Q_loss_side_i + Q_loss_bottom_i

                Q_storage_sim[i] = Q_storage_sim[i - 1] + Q_charge[i] - Q_discharge[i] - Q_loss[i]

            return Q_storage_sim, Q_loss_lid_array, Q_loss_side_array, Q_loss_bottom_array

        # --- Objective: penalize final-energy mismatch + loss-share mismatch ---
        def objective(U_values):
            Q_storage_sim, Q_loss_lid, Q_loss_side, Q_loss_bottom = simulate_storage(U_values)

            # Term 1: squared deviation of final storage energy from measurement
            final_error = Q_storage_sim[-1] - Q_storage_end

            # Term 2: squared deviation of per-surface loss fractions from targets
            total_loss       = np.sum(Q_loss_lid) + np.sum(Q_loss_side) + np.sum(Q_loss_bottom)
            simulated_shares = np.array([
                np.sum(Q_loss_lid)    / total_loss,
                np.sum(Q_loss_side)   / total_loss,
                np.sum(Q_loss_bottom) / total_loss,
            ])
            target_shares = np.array([share_loss_lid, share_loss_side, share_loss_bottom])
            share_error   = np.sum((simulated_shares - target_shares)**2)

            # Weight share error heavily so both conditions are satisfied simultaneously
            return final_error**2 + 1e6 * share_error

        # --- Run optimization ---
        result = minimize(objective, x0=k0, bounds=bounds, method='L-BFGS-B')

        self.U_lid, self.U_side, self.U_bottom = result.x
        Q_storage_sim, Q_loss_lid, Q_loss_side, Q_loss_bottom = simulate_storage(result.x)
        Q_loss = Q_loss_lid + Q_loss_side + Q_loss_bottom

        return {
            "U_lid":                   self.U_lid,
            "U_side":                  self.U_side,
            "U_bottom":                self.U_bottom,
            "Q_storage_sim":           Q_storage_sim,
            "Q_loss":                  Q_loss,
            "optimization_success":    result.success,
            "optimization_message":    result.message,
        }

# =====================================================================
# TTES — TANK THERMAL ENERGY STORAGE (cylindrical geometry)
# =====================================================================

class TTES(STES):
    """
    Tank Thermal Energy Storage with a cylindrical geometry.

    All layers have identical volume and side area because the
    cross-section is constant throughout the cylinder height.
    """

    def __init__(self, h, r, n_layers, T_min=12, T_max=90, T_ref=10):
        """
        Parameters
        ----------
        h        : float  Cylinder height [m].
        r        : float  Cylinder radius [m].
        n_layers : int    Number of horizontal layers.
        T_min    : float  Minimum storage temperature [°C].
        T_max    : float  Maximum storage temperature [°C].
        T_ref    : float  Reference temperature for energy calculations [°C].
        """
        super().__init__(n_layers, T_min, T_max, T_ref)

        self.h = h
        self.r = r

        self.V_storage = self.volume_cylinder(h, r)
        self.V_layer   = self.volume_per_layer(h, r, n_layers)

        self.A_side, self.A_top, self.A_bottom = self.surface_area_cylinder(h, r)
        self.A_side_layers = self.surface_area_per_layer(h, r, n_layers)

        self.compute_energy_bounds()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def volume_cylinder(self, h, r):
        """Total cylinder volume [m³] = π r² h."""
        return np.pi * r**2 * h

    def volume_per_layer(self, h, r, n):
        """
        Equal-height layer volumes [m³].
        Returns a list of n identical values (π r² h/n each).
        """
        h_layer = h / n
        V_layer = np.pi * r**2 * h_layer
        return [V_layer] * n

    def surface_area_cylinder(self, h, r):
        """
        Side, top, and bottom surface areas [m²].

        Returns
        -------
        A_side   : float  Lateral surface area (2πrh).
        A_top    : float  Top disc area        (πr²).
        A_bottom : float  Bottom disc area     (πr²).
        """
        A_side   = 2 * np.pi * r * h
        A_top    = np.pi * r**2
        A_bottom = np.pi * r**2
        return A_side, A_top, A_bottom

    def surface_area_per_layer(self, h, r, n):
        """
        Lateral surface area per layer [m²].
        Returns a list of n identical values (2πr h/n each).
        """
        h_layer = h / n
        A_layer = 2 * np.pi * r * h_layer
        return [A_layer] * n