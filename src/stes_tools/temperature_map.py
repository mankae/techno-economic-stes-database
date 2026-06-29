import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


def temperature_map_simple(
    n_layers=32,    # number of storage layers = number of temperature sensors
    T_min=12,       # minimum (cold) storage temperature [°C]
    T_max=90,       # maximum (hot)  storage temperature [°C]
    n_points=2000,  # number of points along the charging-state axis
    stretch=1,      # controls how spread-out the curves are across layers
    sharpness=20,   # steepness of each sigmoid; higher = sharper transition
    plot=False      # if True, display the generated curves
    ):
    """
    Generate a set of synthetic layered temperature curves using shifted
    sigmoids, one curve per storage layer.

    Each curve represents how the temperature of a given layer evolves
    as the storage charges from empty (Q=0 %) to full (Q=100 %).  The
    curves are spread apart by shifting the inflection point of the
    sigmoid across layers, so upper (hotter) layers heat up earlier and
    lower (colder) layers heat up later.

    Parameters
    ----------
    n_layers   : int    Number of layers (= rows in output).
    T_min      : float  Temperature at Q=0 % [°C].
    T_max      : float  Temperature at Q=100 % [°C].
    n_points   : int    Resolution along the charging-state axis (= columns).
    stretch    : float  Total spread of inflection-point shifts across layers.
                        Larger values make curves more distinct from each other.
    sharpness  : float  Sigmoid steepness; higher values give a sharper step.
    plot       : bool   Whether to display the curves after generation.

    Returns
    -------
    curves : np.ndarray, shape (n_layers, n_points)
        Temperature [°C] per layer at each charging state.
        Row 0 = top/hottest layer, row n_layers-1 = bottom/coldest layer.
    """

    # Charging-state axis: 0 (empty) → 1 (full)
    x = np.linspace(0, 1, n_points)

    # Each layer gets a different inflection point, spread symmetrically
    # around 0.5 (the midpoint of the charging axis)
    shifts = np.linspace(-0.5 * stretch, 0.5 * stretch, n_layers)

    curves = []
    for s in shifts:
        # Sigmoid shifted by s; larger s → curve bends earlier (higher layer)
        y = 1 / (1 + np.exp(-sharpness * (x - 0.5 + s)))

        # Normalize each curve individually so it spans exactly [0, 1],
        # removing the flat tails that sigmoids never actually reach
        y = (y - y.min()) / (y.max() - y.min())
        curves.append(y)

    # Scale from [0, 1] to [T_min, T_max]
    curves = np.array(curves) * (T_max - T_min) + T_min

    # Flip row order so index 0 is the hottest (top) layer
    curves = np.flip(curves, axis=0)

    # --- Optional plot ---
    if plot:
        plt.rcParams.update({'font.size': 19})
        plt.figure(figsize=(10, 5))

        # Brown-to-cream gradient: dark = hot (top), light = cold (bottom)
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "custom_brown", ["#833C0C", "#ED7D31", "#FCE4D6"]
        )

        for i in range(n_layers):
            plt.plot(x * 100, curves[i], color=cmap(i / (n_layers - 1)), linewidth=3, alpha=1.0)

        plt.xlabel(r"$Q_t$ [%]", fontsize=21)
        plt.ylabel(r"$T_n$ [°C]", fontsize=21)
        plt.show()
        plt.rcParams.update({'font.size': 10})

    return np.array(curves)


def temperature_map(
    n_layers=32,
    T_min=12,
    T_mid=45,       # intermediate temperature; set to None for a single-stage map
    T_max=90,
    n_points=2000,
    stretch=1,
    sharpness=10,
    overlap=0.3,    # fraction [0, 1] of the two stages that overlap in charging state
    plot=False
    ):
    """
    Generate a synthetic temperature map for a storage with an optional
    two-stage charging profile (e.g. direct solar charging up to T_mid,
    then heat-pump assisted charging up to T_max).

    Single-stage mode (T_mid=None)
    --------------------------------
    Delegates directly to temperature_map_simple spanning T_min → T_max.

    Two-stage (cascaded) mode (T_mid is set)
    -----------------------------------------
    Three base curve sets are generated and blended:

      curves_1 : T_min → T_mid  (first charging stage)
      curves_2 : T_mid → T_max  (second charging stage, offset in time)
      curves_3 : T_min → T_max  (softer background used for upper layers
                                  that blend between the two stages)

    Two spatial–temporal masks control the blending:
      mask_1 / mask_2  : time-domain crossfade between stage 1 and stage 2
      mask_3           : layer-domain blend that fades the cascaded result
                         into the smooth background for the top half of layers

    Parameters
    ----------
    n_layers  : int    Number of storage layers.
    T_min     : float  Minimum storage temperature [°C].
    T_mid     : float  Intermediate temperature between the two stages [°C],
                       or None to use a single-stage map.
    T_max     : float  Maximum storage temperature [°C].
    n_points  : int    Number of charging-state points per stage.
    stretch   : float  Layer spread (passed to temperature_map_simple).
    sharpness : float  Sigmoid steepness (passed to temperature_map_simple).
    overlap   : float  Fractional overlap [0, 1] between the two stages.
                       Higher values → smoother transition between stages.
    plot      : bool   Whether to display the final curves.

    Returns
    -------
    T_curves : np.ndarray, shape (n_layers, n_total_points)
        Temperature map [°C].  Row 0 = top layer, last row = bottom layer.
        n_total_points = n_points + shift  where shift = int(n_points*(1-overlap)).
    """

    if T_mid is None:
        # ----------------------------------------------------------------
        # Single-stage fallback: one smooth sigmoid map from T_min to T_max
        # ----------------------------------------------------------------
        T_curves = temperature_map_simple(
            n_layers, T_min, T_max, n_points, stretch, sharpness, False
        )

    else:
        # ----------------------------------------------------------------
        # Two-stage cascaded map
        # ----------------------------------------------------------------

        # shift = number of columns by which stage 2 is delayed relative
        # to stage 1.  A larger overlap shrinks the delay (more simultaneous).
        shift = int(n_points * (1 - overlap))

        # --- Base curve sets ---
        # Stage 1: storage charges from T_min to T_mid
        curves_1 = temperature_map_simple(n_layers, T_min, T_mid,       n_points,         stretch, sharpness,     False)
        # Stage 2: storage charges from 0 to (T_max - T_mid); T_mid offset added later
        curves_2 = temperature_map_simple(n_layers, 0,     T_max - T_mid, n_points,        stretch, sharpness,     False)
        # Background: smooth single-stage map at lower sharpness, used for top layers
        curves_3 = temperature_map_simple(n_layers, T_min, T_max,       n_points + shift,  stretch, sharpness - 4, False)

        # --- Extend curves_1 and curves_2 to the full time axis ---
        # curves_1 holds its final value (≈ T_mid) during the stage-2 delay period
        shift_T_mid = np.column_stack([curves_1[:, -1]] * shift)
        curves_1    = np.hstack((curves_1, shift_T_mid))

        # curves_2 stays at T_mid (zero offset columns) during stage 1,
        # then adds the T_mid baseline so it starts exactly at T_mid
        shift_zeros = np.zeros((n_layers, shift))
        curves_2    = np.hstack((shift_zeros, curves_2))
        curves_2   += T_mid

        # --- Time-domain crossfade masks (mask_1, mask_2) ---
        # Sinusoidal transition from stage 1 → stage 2 over the non-overlapping window
        transition_1 = np.linspace(-np.pi / 2, np.pi / 2, n_points - shift)
        transition_1 = (np.sin(transition_1) + 1) / 2          # smooth 0→1 ramp

        # mask_1: 1 during stage 1, fades to 0 at the end
        mask_1 = np.hstack((np.ones(shift), 1 - transition_1, np.zeros(shift)))
        # mask_2: 0 during stage 1, fades to 1 at the end
        mask_2 = np.hstack((np.zeros(shift), transition_1,     np.ones(shift)))

        # --- Layer-domain blend mask (mask_3) ---
        # The top half of layers blend into the smoother background (curves_3),
        # while the bottom half use the fully cascaded result.
        shift_transition_2 = int(n_layers / 2)
        transition_2 = np.linspace(-np.pi / 2, np.pi / 2, shift_transition_2)
        transition_2 = (np.sin(transition_2) + 1) / 2          # smooth 0→1 ramp

        # Pad with zeros for the bottom half (no blending there)
        transition_2 = np.hstack((np.zeros(n_layers - shift_transition_2), transition_2))
        transition_2 = np.flip(transition_2)  # index 0 (top) gets weight 1 → curves_3

        # Broadcast the per-layer weights across all time columns
        mask_3 = np.column_stack([transition_2.T] * len(mask_1))

        # --- Blend: cascaded stages + background ---
        T_curves = (curves_1 * mask_1 + curves_2 * mask_2) * (1 - mask_3) + curves_3 * mask_3

    # --- Optional plot ---
    if plot:
        plt.rcParams.update({'font.size': 19})

        cmap = mcolors.LinearSegmentedColormap.from_list(
            "custom_brown", ["#833C0C", "#ED7D31", "#FCE4D6"]
        )

        plt.figure(figsize=(10, 5))
        for i in range(n_layers):
            x = np.linspace(0, 1, T_curves.shape[1]) * 100
            plt.plot(x, T_curves[i], color=cmap(i / (n_layers - 1)), linewidth=3, alpha=0.9)

        plt.xlabel(r"$Q_t$ [%]", fontsize=21)
        plt.ylabel(r"$T_n$ [°C]", fontsize=21)
        plt.show()
        plt.rcParams.update({'font.size': 10})

    return T_curves