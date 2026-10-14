# Study Notes: Transistor to 5T OTA

Personal notes for review before interviews. Read, cover the answers, and explain each point out loud.

## 1. MOSFET basics

- **Regions:** cutoff (Vgs below Vth, almost no current), triode (small Vds, acts like a voltage-controlled resistor), saturation (Vds above Vgs - Vth, current set mainly by Vgs).
- **Saturation current (ideal):** Id ≈ ½ μCox (W/L) (Vgs - Vth)²
- **Triode current (ideal):** Id ≈ μCox (W/L) [(Vgs - Vth)Vds - Vds²/2]
- **Why current flattens in saturation:** the channel pinches off at the drain end; extra Vds drops across the small pinched region and does not add much current.
- **gm** = slope of Id vs Vgs = how strongly the gate controls the current.
- **ro** = output resistance = 1 / slope of Id vs Vds in saturation (the small tilt on the flat curves). Longer L gives a flatter curve and a higher ro.
- **Measured (SKY130 NMOS, W = 1, L = 0.5):** Vth about 0.6 V; gm levels off near 270 µA/V at high Vgs, so the square law is only approximate.
- **Scaling:** current and gm scale with W/L (W up gives more, L up gives less).

## 2. Common-source amplifier

- Gate bias sets the current. RD turns the current into an output voltage. The output is inverted.
- **Gain** ≈ -gm · (RD ∥ ro). **Bandwidth** ≈ 1 / (2π · RL · CL).
- **Gain × bandwidth** is about constant (≈ gm / 2πCL). More of one costs the other, unless gm goes up (more current and power) or CL goes down.
- Bias too close to Vth gives tiny gm and gain below 1 (my first run: -2.5 dB).
- **Saturation check:** v(out) must stay above about Vgs - Vth.

| Run | I | v(out) | Gain | f3db | UGF |
|---|---|---|---|---|---|
| Vin 0.7 V, RD 10k | 4.7 µA | 1.753 V | ≈ -2.5 dB | n/a | n/a |
| Vin 0.8 V, RD 10k | 16.9 µA | 1.631 V | 4.59 dB | 16.0 MHz | 22.0 MHz |
| Vin 0.8 V, RD 20k | 16.7 µA | 1.466 V | 10.44 dB | 8.11 MHz | 25.8 MHz |

Doubling RD: gain +6 dB, bandwidth halved, gain × bandwidth the same (about 27 MHz).

## 3. 5-transistor OTA

**Structure**
- M1, M2: NMOS differential pair (the inputs).
- M3, M4: PMOS current-mirror load. M3 is diode-connected (gate to drain).
- M5: NMOS tail current source. M6: diode-connected reference that M5 mirrors from Ib.

**How it works**
1. Tail current splits between M1 and M2 according to the input difference.
2. The mirror copies M1's current to the output side, where it combines with M2's current. This turns a differential input into a single-ended output and doubles the signal compared with using one side.
3. The signal current flows through the output resistance, ro2 ∥ ro4.

**Key formulas**
- Mirror: I_out = I_ref × (W/L)_out / (W/L)_ref
- Tail current = Ib × W5/W6 (L the same). Each side gets half.
- Supply current = Ib + tail current.
- DC gain ≈ gm1 · (ro2 ∥ ro4)
- UGF ≈ gm1 / (2π · CL)
- f3db = UGF / gain
- Power = VDD × supply current

**Checks I should always do**
- v(out) and v(d1) should be close, and away from 0 V and 1.8 V.
- v(tail) must be high enough that M5 stays in saturation.
- Supply current should be near Ib + tail current (mirrors are not exact).
- Gain × f3db should match UGF.

## 4. Session results (VDD 1.8 V, Ib 10 µA, CL 1 pF)

| Run | M1/M2 L | M3/M4 L | v(out) | I | Gain | f3db | UGF |
|---|---|---|---|---|---|---|---|
| Baseline | 0.5 | 0.5 | 0.666 V | 28.98 µA | 35.58 dB | 393 kHz | 23.7 MHz |
| L longer everywhere | 1 | 1 | 0.551 V | 28.84 µA | 35.57 dB | 316 kHz | 19.0 MHz |
| L longer on load only | 0.5 | 1 | 0.550 V | 28.97 µA | 35.34 dB | 399 kHz | 23.3 MHz |

Derived from baseline: gm ≈ 149 µS, Rout ≈ 400 kΩ.

## 5. Mistakes and surprises (the most useful part)

1. **Mirror ratio:** I answered 5 µA for the tail current. Correct: 10 µA × (W5/W6) = 20 µA, then 10 µA per side. The mirror multiplies, and the pair then splits.
2. **M4 wider than M3:** I said nothing changes. Correct: M4 tries to copy 2x the current, but M2 can only sink 1x, so the output drifts to a rail and the gain collapses. Use a 1:1 load mirror.
3. **Longer L:** I predicted gain up and UGF up. Result: gain unchanged (35.6 dB), UGF down 20%. Halving W/L lowers gm, and the output resistance rose only about 1.25x, not 2x.
4. **Load-only longer L:** gain did not rise (35.34 dB). Likely reasons (not yet tested): ro2 ∥ ro4 is dominated by the smaller one, and v(out) dropped to 0.55 V, leaving M2 only about 0.3 V of Vds.
5. **Why it matters:** no single transistor controls the gain. gm, output resistance, and headroom interact. Hand rules like "longer L means more gain" can fail, which is the motivation for learning from simulation data.
6. **Reading plots:** ngspice autoscales the axes. Always read the numbers (or use `meas`), not the shape.

## 6. Self-test (answer from memory)

1. What sets the current in a MOSFET in saturation, and what does W/L do?
2. Why does a current mirror need both transistors in saturation?
3. Why is the OTA's gain much higher than the common-source amplifier's?
4. If gain doubles and UGF stays the same, what happens to f3db?
5. Why can lengthening L fail to raise gain in my OTA?
6. Why will my dataset need to filter out some random sizings?

## 7. Open questions to test next

- Widen M3 and M4 (for example W = 8) with L = 1 and check whether v(out) rises back and the gain recovers. This tests the headroom explanation.
- Print gm, gds, and vdsat for M2 in each run to see directly how much headroom it has.
