# ML-Guided Analog Circuit Sizing

Train an ML surrogate model to predict analog circuit performance (gain,
bandwidth, power) from transistor sizing, then use it with an optimizer to
find designs that meet a target spec, validated against a real SPICE
simulator.

## Tools
ngspice, Xschem, SkyWater SKY130 PDK (via IIC-OSIC-TOOLS in Docker), Python

## Progress
- [x] Set up simulation toolchain
- [x] NMOS I-V curves and transconductance (gm)
- [ ] Common-source amplifier
- [ ] 5-transistor OTA
- [ ] Dataset generation
- [ ] ML models and comparison
- [ ] Optimization and demo app
- [ ] Cadence validation

## What I learned
1)- <img width="1919" height="928" alt="id_vs_gm_plots" src="https://github.com/user-attachments/assets/f6640138-d66e-4282-94c3-980b883811e4" />
- Increasing W doubled the drain current and the gm (current scales with W/L). Increasing L reduced the current.
- The threshold voltage (Vth) of the SKY130 NMOS is about 0.6 V, where the current starts to rise in the Id vs Vgs plot.
- In the Id-Vds curves, the current rises steeply in the triode region, then flattens in saturation. 
- The transistor doesn't follow the ideal square-law equation. Id becomes almost linear at high Vgs and gm levels off around 270 µA/V, which is typical of short-channel devices.
- ngspice autoscales plot axes, so I have to read the axis values instead of judging by shape.

