# Lavalier Microphone Frequency Response Tester

A coupler-based test rig and measurement script for detecting frequency response
degradation in theater lavalier microphones. Designed for Audio-Technica BP899
and Bodymics DLF3 capsules with cH/cW connectors, but adaptable to any small
omnidirectional lav element.

## Why This Exists

Theater lav mics accumulate sweat, makeup, skin oils, and hairspray over time.
This gradually clogs the diaphragm and protective mesh, causing high-frequency
rolloff — usually starting around 6–8kHz — that degrades vocal intelligibility.
By the time it's audible in a show, the capsule is well past due for cleaning
or replacement.

This rig gives you a repeatable, quantitative way to catch degradation early
by comparing each mic's frequency response against a known-good baseline.

## How It Works

A small sealed PVC chamber (coupler) has an IEM earphone driver on one end and
a slot for the lav capsule on the other. The Python script generates a
logarithmic sine sweep, plays it through the IEM driver into the coupler, and
simultaneously records what the lav mic picks up. It then deconvolves the
recording to extract the impulse response, computes the frequency response via
FFT, and plots the result against a saved baseline. Any mic that deviates
significantly — especially in the high frequencies — gets flagged.

Because the coupler is tiny (~1–2 cm³), wavelengths are much larger than the
chamber dimensions across most of the audible range, effectively eliminating
internal acoustics as a variable. You're measuring the capsule's response
directly.

---

## Hardware

### Parts List

#### Home Depot (~$9)

| Qty | Item | Part # / SKU | Price |
|-----|------|-------------|-------|
| 1 | Charlotte Pipe 3/4" PVC Sch 40 FPT × FPT Coupling | PVC021020800HD / [SKU 203811424](https://www.homedepot.com/p/Charlotte-Pipe-3-4-in-PVC-Schedule-40-FPT-x-FPT-Coupling-PVC021020800HD/203811424) | $1.96 |
| 3 | Charlotte Pipe 3/4" PVC Sch 40 MPT Plug | PVC021130800HD / [SKU 203850342](https://www.homedepot.com/p/Charlotte-Pipe-3-4-in-PVC-Schedule-40-Plug-MPT-PVC021130800HD/203850342) | $2.37 ea |

Also grab a roll of PTFE/Teflon tape if you don't have one.

#### Amazon (~$37)

| Item | Link | Price |
|------|------|-------|
| KZ ZSN Pro X IEM (without mic) | [amazon.com/dp/B08TQX99P3](https://amzn.to/3NCxEO7) | ~$15 |
| Sugru Moldable Glue, 3-pack black | [amazon.com/dp/B089WHGQDP](https://amzn.to/3NCxEO7) | ~$10 |
| Silicone tubing, 3mm ID × 5mm OD (for DLF3) | [amazon.com/dp/B0CS9SDWPF](https://amzn.to/4cI4F5K) | ~$6 |
| Silicone tubing, 5mm ID × 7mm OD (for BP899) | [amazon.com/dp/B0CS9V1R5T](https://www.amazon.com/dp/B0CS9V1R5T) | ~$6 |

#### Audio-Technica Power Module (~$110–122)

| Item | Link | Price |
|------|------|-------|
| AT8545 power module (cH → XLR) | [amazon.com/dp/B07TY2GK1C](https://amzn.to/4s9H7vk) | ~$122 |

The AT8545 accepts cH-style connectors and outputs XLR with 11–52V phantom
power. If your mics are cW-terminated, use your existing cW-to-cH adapter
cable, or buy the AT8539 (cW → XLR) instead.

**Important:** The AT8545 has a recessed HP filter switch. Set it to **flat**
(not roll-off) for testing, or you'll measure the module's 80Hz filter instead
of the capsule's actual low-end response.

#### Things You Probably Already Have

- Audio interface with +48V phantom power and a headphone/line output
- 1/8" to 1/4" (3.5mm to 6.35mm) headphone adapter
- Drill and small bits (~6mm for the IEM nozzle, ~5mm and ~7mm for the tubing)
- Step drill bit (optional but makes cleaner holes in PVC)
- Computer with Python 3

### Assembly

#### Overview

The coupler consists of three parts: one PVC coupling (the chamber body), one
permanently sealed IEM driver plug, and interchangeable mic-end plugs (one per
capsule size). All three plugs thread into the coupling.

```
  ┌─────────────────────────────────────────────┐
  │              PVC FPT×FPT Coupling           │
  │              (chamber body)                 │
  │                                             │
  │  ┌──────────┐                ┌──────────┐   │
  │  │ IEM Plug │  sealed air    │ Mic Plug │   │
  │  │ (fixed)  │◄── volume ───► │ (swap)   │   │
  │  └──────────┘                └──────────┘   │
  │                                             │
  └─────────────────────────────────────────────┘
       ▲                              ▲
       │                              │
   IEM cable                    Lav capsule
   to interface                 to AT8545
   headphone out                to interface
                                mic input
```

#### Step 1: Prepare the IEM Driver Plug

1. Remove the detachable cable from the KZ ZSN Pro X. Note which earbud
   you're using (left or right) — you'll need to match the output channel
   in the software later.

2. Remove the silicone ear tip from the earbud. The exposed sound nozzle is
   approximately 6mm in diameter.

3. Drill a hole in the center of one PVC plug, sized so the IEM nozzle fits
   through snugly. Start slightly undersized and widen gradually. The nozzle
   should protrude slightly into the chamber side (the threaded end) of the
   plug.

4. Insert the IEM from the outside (flat end) of the plug, nozzle pointing
   inward through the hole.

5. Pack Sugru moldable glue generously around the IEM shell on the outside
   of the plug. Ensure a complete seal — no air gaps. Shape it so the IEM
   body is mechanically locked in place.

6. Let the Sugru cure for 24–48 hours before use.

7. Reconnect the detachable cable from outside.

**Test before sealing:** Plug in the cable, play a tone, and verify sound
comes out of the nozzle before you commit with Sugru.

#### Step 2: Prepare the Mic-End Plugs

You need two plugs — one for each capsule diameter.

**For the BP899 (5.3mm capsule):**

1. Drill a hole in the center of a PVC plug, slightly larger than the 7mm
   outer diameter of the 5mm ID silicone tubing.

2. Push a 10–15mm section of 5mm ID × 7mm OD silicone tubing through the
   hole so it sits flush with the inner face (threaded end) of the plug.

3. Apply Sugru around the tubing on the outer face of the plug to permanently
   bond it in place and seal any air gap. Let cure 24 hours.

4. The BP899 capsule (5.3mm) friction-fits into the 5mm ID tubing — the
   silicone stretches slightly to grip it.

**For the DLF3 (3mm capsule):**

1. Same process, but drill the hole for the 5mm OD of the 3mm ID tubing.

2. Insert a section of 3mm ID × 5mm OD silicone tubing, Sugru it in place.

3. The DLF3 capsule (3mm) fits directly into the 3mm bore.

**Capsule seating depth:** The capsule face should sit roughly flush with the
inner surface of the plug. Consistent depth matters for repeatability.

#### Step 3: Assemble the Coupler

1. Wrap PTFE tape on the threads of the IEM driver plug. Thread it into one
   end of the coupling and tighten firmly. This end is permanent.

2. Wrap PTFE tape on the threads of whichever mic plug you're using. Thread
   it into the other end hand-tight. This end gets removed to swap capsules
   and to swap between BP899 and DLF3 plugs.

#### Signal Chain

```
Audio Interface          Audio Interface
Headphone/Line Out       Mic Input (48V phantom on)
      │                        ▲
      ▼                        │
  3.5mm→6.35mm adapter    XLR cable
      │                        │
      ▼                        │
  KZ IEM cable             AT8545 power module
      │                    (set to FLAT)
      ▼                        ▲
  IEM driver in coupler    Lav capsule in coupler
      │                        │
      └──── sealed air ────────┘
           chamber
```

---

## Software

### Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

On macOS you also need PortAudio:
```bash
brew install portaudio
```

On Linux (Debian/Ubuntu):
```bash
sudo apt install libportaudio2
```

**Without uv** (pip fallback):
```bash
pip install sounddevice scipy matplotlib numpy
```

### Quick Start

#### 1. Find your audio devices

```bash
uv run mic_test.py --list-devices
```

Note the index numbers for your audio interface's input and output.

#### 2. Establish a baseline with a known-good mic

```bash
uv run mic_test.py \
  -o 3 -i 5 \
  --label "BP899_reference" \
  --save-baseline \
  --amplitude 0.3
```

Start with `--amplitude 0.3` and watch your input meters. The DLF3 clips at
125 dB SPL and the BP899 at 140 dB SPL, so increase gradually. If you see
clipping on the interface input, lower the amplitude.

#### 3. Test mics against the baseline

```bash
uv run mic_test.py \
  -o 3 -i 5 \
  --label "BP899_mic04" \
  --reference results/BP899_reference_20260313_141500.npz
```

The script overlays the curves, computes deviation stats, and flags any mic
with significant high-frequency rolloff.

#### 4. Batch test with averaging

```bash
uv run mic_test.py \
  -o 3 -i 5 \
  --label "DLF3_mic07" \
  --reference results/DLF3_reference_20260313_142000.npz \
  --averages 3 \
  --save-wav
```

Multiple sweeps are averaged together to reduce noise. `--save-wav` saves
the raw recording for later re-analysis.

### Command Reference

| Flag | Default | Notes |
|------|---------|-------|
| `--list-devices` | — | Print audio devices and exit |
| `-o` / `--output-device` | — | Output device index (required) |
| `-i` / `--input-device` | — | Input device index (required) |
| `--output-channel` | 0 | 0=left, 1=right. Match to your IEM wiring |
| `--input-channel` | 0 | Interface input channel (0-indexed) |
| `--label` | mic_test | Label for filenames and graph title |
| `--amplitude` | 0.3 | Sweep level 0.0–1.0. **Start low!** |
| `--sweep-duration` | 3.0 | Longer = better SNR, diminishing returns past 5s |
| `--f-start` | 20 | Low frequency bound (Hz) |
| `--f-stop` | 20000 | High frequency bound (Hz) |
| `--smoothing` | 6 | 1/N octave smoothing (6 = 1/6 oct, 3 = 1/3 oct) |
| `--averages` | 1 | Number of sweeps to average |
| `--reference` | — | Path to a .npz baseline file to overlay |
| `--save-baseline` | off | Save measurement as a .npz baseline file |
| `--save-wav` | off | Save raw recorded audio as .wav |
| `--output-dir` | results | Directory for all output files |
| `--sample-rate` | 48000 | Sample rate in Hz |

### Output Files

All files are saved to `results/` (or the directory specified by `--output-dir`):

- `{label}_{timestamp}.png` — frequency response graph
- `{label}_{timestamp}.npz` — baseline data (with `--save-baseline`)
- `{label}_{timestamp}.wav` — raw recording (with `--save-wav`)

---

## Interpreting Results

The graph is normalized so that the 1kHz–4kHz range averages to 0 dB. The
script also prints band-by-band stats to the console.

**Healthy mic:** Closely tracks the reference curve across the spectrum.
Deviations of ±2 dB are normal and within manufacturing tolerance.

**Gunk buildup (most common failure):** Progressive high-frequency rolloff,
typically starting around 6–8kHz and worsening with frequency. The script
flags any mic averaging >3 dB down from reference above 6kHz. This mic needs
its mesh cleaned or the capsule replaced.

**Sensitivity loss:** Overall level drop across all frequencies, not just HF.
This indicates the diaphragm itself is compromised — cleaning the mesh won't
fix it. The capsule needs replacement.

**Notch or resonance:** A sharp dip or peak at a specific frequency can
indicate physical damage to the capsule or a foreign object lodged in the
mesh. Inspect under magnification.

---

## Tips for Repeatable Measurements

- Always use the **same power module** for a given comparison set. The AT8545
  and AT8539 have slightly different electronics and aren't interchangeable
  for baseline comparisons.

- Set the AT8545/AT8539 filter switch to **flat**, not roll-off.

- **Seat the capsule to the same depth** every time. Mark the cable with a
  small piece of tape as a depth reference.

- After inserting a capsule, **wait 30 seconds** before measuring. Pushing the
  capsule into the sealed tubing compresses the air slightly; give it time to
  equalize through the small gaps around the cable.

- Keep the coupler **stationary** during measurement. Handling noise from the
  cable or chamber can contaminate results.

- **Don't swap between BP899 and DLF3 plugs and compare across capsule types.**
  Different plug geometries mean different chamber volumes and tubing
  acoustics. Only compare BP899 against BP899 baseline, DLF3 against DLF3
  baseline.

- For the most reliable results, use `--averages 3` to reduce random noise.

- Store baseline .npz files somewhere safe. Label them with the specific
  capsule serial number or ID and the date. Re-establish baselines
  periodically (e.g. once a season with a fresh capsule).

---

## Mic Cleaning Notes

If you find degraded capsules, try cleaning before replacing:

1. Remove any windscreen or resonance cap.
2. Gently brush the protective mesh with a soft, dry toothbrush.
3. Dab the mesh with 90%+ isopropyl alcohol on a lint-free wipe. Don't
   submerge the capsule.
4. Let it dry completely (at least 30 minutes) before re-testing.
5. Re-measure and compare to the pre-cleaning curve to confirm improvement.

If cleaning doesn't recover the HF response to within ~3 dB of baseline,
the capsule likely needs replacement.

---

## Compatible Microphones

This rig was designed for:

- **Audio-Technica BP899** (5.3mm omnidirectional capsule, cH or cW connector)
- **Bodymics DLF3** (3mm omnidirectional capsule, cH or cW connector)

It will work with any small omnidirectional lav capsule as long as you make a
mic-end plug with appropriately sized silicone tubing. Common candidates:

- DPA 4060/6060 series
- Countryman B3/B6
- Sanken COS-11
- Sennheiser MKE series
- Point Source CO-8WD

Each capsule type needs its own baseline reference and its own mic-end plug.
The IEM driver plug and coupling body are shared across all types.

---

## Total Cost

| Category | Cost |
|----------|------|
| PVC fittings (Home Depot) | ~$9 |
| KZ ZSN Pro X IEM | ~$15 |
| Sugru moldable glue | ~$10 |
| Silicone tubing (2 sizes) | ~$12 |
| AT8545 power module | ~$110–122 |
| **Total** | **~$156–168** |

If you already own an AT8545 or AT8539, the rig itself costs under $46.
