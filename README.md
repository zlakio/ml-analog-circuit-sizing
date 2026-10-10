# ML-Guided Analog Circuit Sizing

Train a machine-learning surrogate model to predict the performance of an analog circuit (gain, bandwidth, power) from its transistor sizing, then use it with an optimizer to find designs that meet a target specification. Results are checked against a real SPICE simulator.

> **Status:** in progress. The simulation toolchain, single-transistor characterization, a common-source amplifier, and a 5-transistor OTA are done. Automated dataset generation, the ML models, and the optimizer are next.

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
| `cs_amp.cir` | Common-source amplifier: operating point, AC gain, bandwidth, unity-gain frequency |
| `ota5t.cir` | 5-transistor OTA: operating point, AC gain, bandwidth, unity-gain frequency, power |
| `figures/` | Plots from the simulations above |
| `notes/` | Study notes |

## How to run

1. Start Docker Desktop, then start the IIC-OSIC-TOOLS container (for example with `start_vnc.bat` from its repo) and open `http://localhost/` in a browser.
2. Place the `.cir` files in the shared designs folder (`/foss/designs/` in the container).
3. In the container terminal:

```
cd /foss/designs/<project folder>
ngspice ota5t.cir
```

If the SKY130 library path in the `.lib` line differs on your setup, update it to match your install.

## Results so far

### 1. NMOS characteristics (SKY130, W = 1, L = 0.5)

<img width="1919" height="928" alt="id_vs_gm_plots" src="https://github.com/user-attachments/assets/9c6ed3d6-62f7-43e7-8459-ebae452c0c1f" />


- Threshold voltage is about 0.6 V, where the drain current starts to rise.
- Doubling W roughly doubled the drain current and gm. Increasing L reduced the current.
- The device does not follow the ideal square law: Id becomes nearly linear at high Vgs and gm levels off near 270 µA/V, which is typical of short-channel devices.

### 2. Common-source amplifier (W = 2, L = 0.5, CL = 1 pF, VDD = 1.8 V)

<img width="615" height="332" alt="rd_20kANDvout0 8" src="https://github.com/user-attachments/assets/7a6d55ac-8ce6-4c81-a98c-b9931f5bd1f2" />


| Gate bias | RD | Supply current | v(out) | Power | DC gain | -3 dB bandwidth | Unity-gain freq |
|---|---|---|---|---|---|---|---|
| 0.7 V | 10 kΩ | 4.7 µA | 1.753 V | ≈ 8.5 µW | ≈ -2.5 dB | not measured | not measured |
| 0.8 V | 10 kΩ | 16.9 µA | 1.631 V | ≈ 30.4 µW | 4.59 dB | 16.0 MHz | 22.0 MHz |
| 0.8 V | 20 kΩ | 16.7 µA | 1.466 V | ≈ 30.1 µW | 10.44 dB | 8.11 MHz | 25.8 MHz |

The gain at 0.7 V is read from the plot. The other values come from ngspice `meas` commands.

### 3. 5-transistor OTA (VDD = 1.8 V, Ib = 10 µA, CL = 1 pF)

```
                    VDD
              ┌──────┴──────┐
         M3 ──┤             ├── M4        PMOS mirror load (gates tied to d1)
              │ d1          │ out ── CL
         M1 ──┤             ├── M2        NMOS pair (inp on M1, inn on M2)
              └──────┬──────┘
                   tail
                     │
                 M5 (gate = nb)           NMOS tail source
                     │
                    GND

  Bias: Ib = 10 µA flows into diode-connected M6, which sets nb; M5 mirrors it.
```

Sizing in the baseline: M1-M4 W = 4, L = 0.5; M5 W = 4, L = 1; M6 W = 2, L = 1. Both inputs at 1.0 V DC.

<img width="885" height="682" alt="ota5t" src="https://github.com/user-attachments/assets/95814776-1b66-498d-897a-c31306f1e938" />


| Run | M1/M2 L | M3/M4 L | v(out) | v(tail) | Supply current | Power | DC gain | -3 dB bandwidth | Unity-gain freq |
|---|---|---|---|---|---|---|---|---|---|
| Baseline | 0.5 | 0.5 | 0.666 V | 0.247 V | 28.98 µA | ≈ 52.2 µW | 35.58 dB | 393 kHz | 23.7 MHz |
| Longer L everywhere | 1 | 1 | 0.551 V | 0.232 V | 28.84 µA | ≈ 51.9 µW | 35.57 dB | 316 kHz | 19.0 MHz |
| Longer L on load only | 0.5 | 1 | 0.550 V | 0.245 V | 28.97 µA | ≈ 52.1 µW | 35.34 dB | 399 kHz | 23.3 MHz |

Derived from the baseline: gm of the input pair ≈ 2π · UGF · CL ≈ 149 µS, and output resistance ≈ gain / gm ≈ 400 kΩ (compared with 20 kΩ for the resistor load in the common-source amplifier).

## What I learned

**Single transistor**
- **Current scales with W/L.** Doubling W doubled the drain current and gm; doubling L reduced the current.
- **Real devices deviate from the square law.** Id becomes nearly linear at high Vgs and gm flattens, which is typical of short-channel transistors, so hand formulas are only a rough guide.
- **Current flattens in saturation because the channel pinches off.** Once Vds reaches about Vgs minus Vth, extra drain voltage drops across a small pinched-off region instead of adding current, so the gate sets the current.
- **Read the axis numbers, not the plot shape.** ngspice autoscales its axes, so two plots can look identical while their values differ by 2x.

**Common-source amplifier**
- **Gate bias sets the current.** Changing RD from 10k to 20k left the supply current at about 16.7 to 16.9 µA.
- **A weakly biased amplifier can have gain below 1.** At a 0.7 V gate bias, only about 0.1 V above threshold, gm was small and the circuit attenuated the signal.
- **Gain and bandwidth trade off.** Doubling RD added about 6 dB of gain and halved the bandwidth. Gain times bandwidth stayed near 27 MHz in both runs, so getting more of both needs more gm (more current and power) or less load capacitance.

**5-transistor OTA**
- **Mirror ratio scales the current.** With M5 twice as wide as M6 and Ib = 10 µA, the ideal tail current is 20 µA, split into 10 µA per side. I first answered this wrongly (5 µA), by treating the mirror as 1:1.
- **Mirrors are not exact.** The measured supply current was 28.98 µA instead of the ideal 30 µA, so the tail current is about 19 µA. M6 sits at Vds of about 0.78 V while M5 sits at about 0.25 V, and a lower drain voltage gives slightly less current.
- **The load mirror should be 1:1.** If M4 were wider than M3 it would try to source more current than M2 can sink, pushing the output node toward VDD and collapsing the gain.
- **The mirror load gives high gain.** Gain ≈ gm1 · (ro2 ∥ ro4). The OTA reached about 60x (35.6 dB) with a 1 pF load, because the output resistance (about 400 kΩ) is far higher than a practical resistor.
- **Gain times bandwidth is consistent.** 60 × 393 kHz ≈ 23.7 MHz, matching the measured unity-gain frequency, so UGF ≈ gm / (2π · CL) describes this circuit well.
- **My prediction about longer L failed.** I predicted that making M1-M4 longer would raise both gain and UGF. In simulation the gain stayed at 35.6 dB and the UGF fell 20% (23.7 to 19.0 MHz). Halving W/L lowered gm, but the output resistance rose only about 1.25x instead of 2x.
- **Lengthening the load alone did not raise gain either.** Gain was 35.34 dB and UGF was unchanged. A likely explanation, not yet tested, is that the output resistance is dominated by the smaller of ro2 and ro4, and the longer PMOS load lowered `v(out)` from 0.67 V to 0.55 V, leaving M2 only about 0.3 V of drain-source voltage and degrading its output resistance.
- **Takeaway for the ML work.** Gain was not controlled by any single transistor. It depends on gm, output resistance, and voltage headroom interacting, which is why the dataset should vary all sizing parameters together instead of one at a time, and why broken or out-of-saturation circuits must be filtered out.

## Roadmap

- [x] Set up simulation toolchain (Docker, ngspice, Xschem, SKY130)
- [x] NMOS I-V curves and transconductance (gm)
- [x] Common-source amplifier (gain, bandwidth, power)
- [x] 5-transistor OTA (baseline and length experiments)
- [ ] Test the headroom hypothesis (widen the PMOS load and check whether `v(out)` and gain recover)
- [ ] Automated dataset generation from Python
- [ ] ML models and comparison
- [ ] Optimization and interactive demo app
- [ ] Cadence Virtuoso/Spectre validation
- [ ] Final write-up
