# ML-Guided Analog Circuit Sizing

Train a machine-learning surrogate model to predict the performance of an analog circuit (gain, bandwidth, power) from its transistor sizing, then use it with an optimizer to find designs that meet a target specification. Results are checked against a real SPICE simulator.

> **Status:** in progress. The simulation toolchain and the basic building blocks (single transistor and common-source amplifier) are done. The OTA, dataset, and ML stages are next.

## Why this project

Sizing an analog circuit is usually trial and error: pick transistor sizes, simulate, look at the result, adjust, repeat. A surrogate model that has learned the sizing-to-performance relationship can predict results instantly, so an optimizer can search thousands of designs in seconds and only the best candidate needs a real simulation.

## Approach

1. **Generate data.** Simulate the circuit in ngspice across thousands of random sizings and record gain, bandwidth, and power.
2. **Train models.** Compare linear regression, a tree-based model, and a small neural network at predicting performance from sizing.
3. **Optimize.** Use the fastest accurate model inside a genetic algorithm or Bayesian optimizer to hit a target spec.
4. **Verify.** Run the winning design in the real simulator and report the gap between predicted and simulated values.
5. **Cross-check.** Reproduce the design in Cadence Virtuoso/Spectre.

## Tools

- **Simulation:** ngspice, Xschem
- **Process models:** SkyWater SKY130 open-source PDK
- **Environment:** [IIC-OSIC-TOOLS](https://github.com/iic-jku/iic-osic-tools) running in Docker
- **ML and optimization (planned):** Python, scikit-learn, PyTorch or scikit-learn MLP, Optuna or pymoo, Streamlit

## Repository contents

| File | What it does |
|---|---|
| `nmos_iv.cir` | NMOS drain current vs. drain voltage for several gate voltages |
| `nmos_gm.cir` | NMOS drain current and transconductance (gm) vs. gate voltage |
| `cs_amp.cir` | Common-source amplifier: DC operating point, AC gain, bandwidth, unity-gain frequency |
| `figures/` | Plots from the simulations above |

## How to run

1. Start Docker Desktop, then start the IIC-OSIC-TOOLS container (for example with `start_vnc.bat` from its repo) and open `http://localhost/` in a browser.
2. Place the `.cir` files in the shared designs folder (`/foss/designs/` in the container).
3. In the container terminal:

```
cd /foss/designs/<project folder>
ngspice cs_amp.cir
```

If the SKY130 library path in the `.lib` line differs on your setup, update it to match your install.

## Results so far

### 1. NMOS characteristics (SKY130, W = 1, L = 0.5)

<img width="1919" height="928" alt="id_vs_gm_plots" src="https://github.com/user-attachments/assets/11096cb8-1d3a-4329-9bdd-61001f58b5e0" />


- Threshold voltage is about 0.6 V, where the drain current starts to rise.
- Doubling W roughly doubled the drain current and gm. Increasing L reduced the current.
- The device does not follow the ideal square law: Id becomes nearly linear at high Vgs and gm levels off near 270 µA/V, which is typical of short-channel devices.

### 2. Common-source amplifier (W = 2, L = 0.5, CL = 1 pF, VDD = 1.8 V)

<img width="615" height="332" alt="rd_20kANDvout0 8" src="https://github.com/user-attachments/assets/1ba7d2fc-6a24-438b-902c-26d03686a94d" />


| Gate bias | RD | Supply current | v(out) | Power | DC gain | -3 dB bandwidth | Unity-gain freq |
|---|---|---|---|---|---|---|---|
| 0.7 V | 10 kΩ | 4.7 µA | 1.753 V | ≈ 8.5 µW | ≈ -2.5 dB | not measured | not measured |
| 0.8 V | 10 kΩ | 16.9 µA | 1.631 V | ≈ 30.4 µW | 4.59 dB | 16.0 MHz | 22.0 MHz |
| 0.8 V | 20 kΩ | 16.7 µA | 1.466 V | ≈ 30.1 µW | 10.44 dB | 8.11 MHz | 25.8 MHz |

The gain at 0.7 V is read from the plot. The other values come from ngspice `meas` commands.

## What I learned

- **Gate bias sets the current.** In saturation the drain current is controlled by the gate voltage, not by the load resistor. Changing RD from 10k to 20k left the supply current at about 16.7 to 16.9 µA.
- **A weakly biased amplifier can have gain below 1.** At a 0.7 V gate bias, only about 0.1 V above threshold, gm was small and the circuit attenuated the signal (about -2.5 dB). Raising the bias to 0.8 V gave about 17 µA and real gain.
- **Gain and bandwidth trade off.** Doubling RD added about 6 dB of gain and halved the bandwidth. Gain times bandwidth stayed near 27 MHz in both runs, so getting more of both needs more gm (more current and power) or less load capacitance. This tradeoff is what the ML model will have to learn.
- **Output resistance shows up as small deviations.** The supply current was slightly higher at the lower RD because the drain sat at a higher voltage, which matches the small upward tilt of the I-V curves in saturation.
- **Current flattens in saturation because the channel pinches off.** Once Vds reaches about Vgs minus Vth, extra drain voltage drops across a small pinched-off region near the drain instead of adding current, so the current is set mainly by the gate.
- **Read the axis numbers, not the plot shape.** ngspice autoscales its axes, so two plots can look identical while their values differ by 2x.

## Roadmap

- [x] Set up simulation toolchain (Docker, ngspice, Xschem, SKY130)
- [x] NMOS I-V curves and transconductance (gm)
- [x] Common-source amplifier (gain, bandwidth, power)
- [ ] 5-transistor OTA
- [ ] Automated dataset generation from Python
- [ ] ML models and comparison
- [ ] Optimization and interactive demo app
- [ ] Cadence Virtuoso/Spectre validation
- [ ] Final write-up
