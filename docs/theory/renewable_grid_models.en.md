# Simplified Renewable Grid Models

[简体中文](renewable_grid_models.md)

These Stage 4 models are teaching-oriented average models for PV, storage, DC links, grid-following and grid-forming control, VSG, and LVRT. They do not model switching ripple or vendor protection details.

`PVArrayModel` uses the static approximation `I = Isc * (G/Gref) * max(0, 1 - (V/Voc)^k)` and `P = V*I`. `BatteryModel` is a Thevenin model with discharge-positive current: `Vt = Voc(SOC) - I*R_internal` and `SOC_k = SOC_(k-1) - I*dt/(capacity_Ah*3600)`.

`DCLink` updates voltage from capacitor energy: `0.5*C*Vdc_k^2 = 0.5*C*Vdc_(k-1)^2 + (P_source-P_load)*dt`. The grid-following controller uses P/Q power equations, a PI dq current loop, current limiting, and L-filter cross-coupling feed-forward.

`DroopController` implements P-f and Q-V droop. `VSGController` integrates virtual inertia and damping with the swing-equation form `d omega_pu/dt = ((Pref-P)/Sbase - D*(omega_pu-1))/(2H)` and `d theta/dt = omega0*omega_pu`.

`LVRTController` uses windowed RMS voltage in per unit; during LVRT it reduces active-power reference, increases reactive support, and exits after recovery. This is a teaching simplification, not a standards implementation. Examples are 13, 14, and 15.

## Model boundaries and checks

Check power direction, current limiting, DC-link energy balance, battery SOC bounds, controller saturation, and disturbance response. These models are not interchangeable with the network EMT workflow unless they are explicitly connected to `Circuit` and `Simulator`. A curve labelled inverter, PV, storage, or HVDC is not evidence that all device, control, protection, and line physics are represented.

## PV array parameters

`G` is irradiance, `Gref` is reference irradiance, `Isc` is short-circuit current, `Voc` is open-circuit voltage, and `k` controls the shape of the static curve. The maximum-power-point estimate uses `mpp_voltage * mpp_current` and scales with irradiance. This is a source-side approximation rather than a switching PV converter model.

## Battery and SOC

Battery current is positive during discharge, meaning that the battery sends power to the DC link. SOC is clamped to `min_soc` and `max_soc`. A case should check both the sign of terminal power and that a load step changes SOC in the expected direction.

## DC-link energy

The DC-link equation is an energy balance, not a direct voltage subtraction. If source power exceeds load power, capacitor energy and normally `Vdc` increase. If load power exceeds source power, they decrease. Tests should compare energy residuals and avoid accepting a voltage trend without checking the power signs.

## Grid-following and grid-forming limits

The grid-following controller calculates `id_ref` and `iq_ref` from active and reactive power targets, then applies current limits before the inner PI loop. The grid-forming droop and VSG controllers describe frequency, voltage, inertia, and damping trends; they do not implement a complete protection, virtual-impedance, current-priority, or islanding standard.

## LVRT sequence

The LVRT controller enters when windowed voltage RMS falls below the entry threshold, modifies active and reactive references, and exits only after the recovery threshold is met. Hysteresis and duration behavior should be stated by the case. The simplified logic must not be presented as compliance with a specific grid code.
