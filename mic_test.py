#!/usr/bin/env python3
"""
Lavalier Microphone Frequency Response Tester

Generates a log sweep, plays it through a specified audio output,
simultaneously records the mic input, computes the transfer function,
and saves a frequency response graph.

Usage:
    python mic_test.py --list-devices
    python mic_test.py --output-device 3 --input-device 5 --label "BP899_mic01"
    python mic_test.py --output-device 3 --input-device 5 --label "BP899_mic01" --reference baseline.npz
"""

import argparse
import sys
import os
import time
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sounddevice as sd
from scipy.signal import fftconvolve
from scipy.io import wavfile


# ── Sweep generation ──────────────────────────────────────────────────────────

def generate_log_sweep(f_start: float, f_stop: float, duration: float,
                       sample_rate: int, amplitude: float = 0.3) -> np.ndarray:
    """Generate a logarithmic sine sweep (exponential chirp)."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    sweep = amplitude * np.sin(
        2 * np.pi * f_start * duration / np.log(f_stop / f_start)
        * (np.exp(t / duration * np.log(f_stop / f_start)) - 1)
    )

    # Apply short fade-in and fade-out to avoid clicks
    fade_samples = int(sample_rate * 0.01)
    sweep[:fade_samples] *= np.linspace(0, 1, fade_samples)
    sweep[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    return sweep.astype(np.float32)


def generate_inverse_filter(sweep: np.ndarray, f_start: float, f_stop: float,
                            duration: float, sample_rate: int) -> np.ndarray:
    """
    Generate the inverse filter for the log sweep.  Convolving the recorded
    signal with this yields the impulse response of the system under test.
    """
    # The inverse filter is the time-reversed sweep with amplitude envelope
    # correction.  For a log sweep the amplitude decays at 3 dB/octave, so
    # we compensate with an exponentially rising envelope.
    n = len(sweep)
    t = np.linspace(0, duration, n, endpoint=False)
    envelope = np.exp(-t / duration * np.log(f_stop / f_start))
    inv = sweep[::-1] * envelope
    # Normalize so that sweep * inv_filter produces unit impulse amplitude
    inv /= np.max(np.abs(fftconvolve(sweep, inv)))
    return inv.astype(np.float32)


# ── Measurement ───────────────────────────────────────────────────────────────

def measure(sweep: np.ndarray, sample_rate: int,
            output_device: int, input_device: int,
            output_channel: int = 0, input_channel: int = 0,
            latency: str = "high") -> np.ndarray:
    """Play the sweep and simultaneously record the microphone input."""

    # Add 0.5 s of silence before and after to capture full response + latency
    pad = np.zeros(int(sample_rate * 0.5), dtype=np.float32)
    stimulus = np.concatenate([pad, sweep, pad])

    # sounddevice playrec expects (frames, channels)
    play_buf = np.zeros((len(stimulus), 1), dtype=np.float32)
    play_buf[:, 0] = stimulus

    print(f"  Playing sweep ({len(stimulus)/sample_rate:.1f}s) …")
    recording = sd.playrec(
        play_buf,
        samplerate=sample_rate,
        input_mapping=[input_channel + 1],   # 1-indexed
        output_mapping=[output_channel + 1],  # 1-indexed
        device=(input_device, output_device),
        dtype="float32",
        latency=latency,
    )
    sd.wait()
    print("  Done.")
    return recording[:, 0]


# ── Analysis ──────────────────────────────────────────────────────────────────

def compute_frequency_response(recording: np.ndarray, inv_filter: np.ndarray,
                               sample_rate: int, f_start: float, f_stop: float,
                               smoothing_octave_fraction: float = 6):
    """
    Compute magnitude frequency response by convolving the recording with
    the inverse filter to get the impulse response, then taking the FFT.
    Returns (frequencies, magnitude_dB, ref_level_dB).

    ref_level_dB is the unnormalized average level in the 1-4 kHz band,
    useful for detecting overall sensitivity changes between mics.
    """
    # Deconvolve → impulse response
    ir = fftconvolve(recording, inv_filter, mode="full")

    # Window around the main peak (direct sound impulse)
    peak = np.argmax(np.abs(ir))
    # Take a window of ~50ms around the peak (enough for a small coupler)
    win_samples = int(sample_rate * 0.05)
    start = max(0, peak - win_samples // 10)  # slight pre-peak allowance
    end = min(len(ir), peak + win_samples)
    ir_windowed = ir[start:end]

    # Apply a half-Hann fade-out to avoid spectral leakage
    fade = np.ones(len(ir_windowed))
    fade_len = len(ir_windowed) // 2
    fade[-fade_len:] = 0.5 * (1 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    ir_windowed *= fade

    # FFT
    n_fft = len(ir_windowed)
    spectrum = np.fft.rfft(ir_windowed, n=n_fft)
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
    magnitude = np.abs(spectrum)

    # Avoid log of zero
    magnitude[magnitude < 1e-12] = 1e-12
    mag_db = 20 * np.log10(magnitude)

    # Normalize so that the average level in 1kHz–4kHz is 0 dB
    mask = (freqs >= 1000) & (freqs <= 4000)
    if np.any(mask):
        ref_level = np.mean(mag_db[mask])
        mag_db -= ref_level
    else:
        ref_level = 0.0

    # Smooth with fractional-octave moving average on log-frequency axis
    mag_db_smooth = fractional_octave_smooth(freqs, mag_db,
                                              smoothing_octave_fraction)

    # Trim to sweep range
    mask = (freqs >= f_start) & (freqs <= f_stop)
    return freqs[mask], mag_db_smooth[mask], ref_level


def fractional_octave_smooth(freqs: np.ndarray, mag_db: np.ndarray,
                              fraction: float = 6) -> np.ndarray:
    """Apply 1/N-octave smoothing on log-frequency axis."""
    smoothed = np.copy(mag_db)
    for i, f in enumerate(freqs):
        if f <= 0:
            continue
        f_lo = f / (2 ** (1 / (2 * fraction)))
        f_hi = f * (2 ** (1 / (2 * fraction)))
        mask = (freqs >= f_lo) & (freqs <= f_hi)
        if np.any(mask):
            smoothed[i] = np.mean(mag_db[mask])
    return smoothed


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot_response(freqs: np.ndarray, mag_db: np.ndarray, label: str,
                  output_path: str, ref_freqs: np.ndarray = None,
                  ref_mag_db: np.ndarray = None, ref_label: str = None):
    """Plot frequency response and optionally overlay a reference curve."""
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    if ref_freqs is not None and ref_mag_db is not None:
        ax.semilogx(ref_freqs, ref_mag_db, color="#4ecca3", linewidth=1.5,
                     alpha=0.6, label=ref_label or "Reference")

    ax.semilogx(freqs, mag_db, color="#e94560", linewidth=2, label=label)

    ax.set_xlabel("Frequency (Hz)", color="white", fontsize=12)
    ax.set_ylabel("Relative Level (dB)", color="white", fontsize=12)
    ax.set_title(f"Frequency Response — {label}", color="white", fontsize=14,
                 pad=15)

    # Derive axis limits from actual data range
    f_lo, f_hi = freqs[0], freqs[-1]
    ax.set_xlim(f_lo, f_hi)
    ax.set_ylim(-30, 15)

    all_ticks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    all_tick_labels = ["20", "50", "100", "200", "500", "1k", "2k", "5k",
                        "10k", "20k"]
    visible = [(t, l) for t, l in zip(all_ticks, all_tick_labels)
               if f_lo <= t <= f_hi]
    if visible:
        ticks, labels = zip(*visible)
        ax.set_xticks(list(ticks))
        ax.set_xticklabels(list(labels))

    ax.tick_params(colors="white")
    ax.grid(True, which="both", alpha=0.2, color="white")
    ax.legend(loc="lower left", fontsize=10, facecolor="#16213e",
              edgecolor="#4ecca3", labelcolor="white")

    # Add timestamp
    ax.text(0.99, 0.02, datetime.now().strftime("%Y-%m-%d %H:%M"),
            transform=ax.transAxes, ha="right", va="bottom",
            color="white", alpha=0.4, fontsize=8)

    for spine in ax.spines.values():
        spine.set_color("#4ecca3")
        spine.set_alpha(0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {output_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def list_devices():
    """Print available audio devices."""
    print("\nAvailable audio devices:\n")
    print(sd.query_devices())
    print(f"\nDefault input:  {sd.default.device[0]}")
    print(f"Default output: {sd.default.device[1]}")


def main():
    parser = argparse.ArgumentParser(
        description="Lavalier Microphone Frequency Response Tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-devices
  %(prog)s -o 3 -i 5 --label "BP899_mic01"
  %(prog)s -o 3 -i 5 --label "BP899_mic02" --reference results/BP899_mic01.npz
  %(prog)s -o 3 -i 5 --label "DLF3_mic01" --save-baseline
        """)

    parser.add_argument("--list-devices", action="store_true",
                        help="List audio devices and exit")
    parser.add_argument("-o", "--output-device", type=int, default=None,
                        help="Output audio device index")
    parser.add_argument("-i", "--input-device", type=int, default=None,
                        help="Input audio device index")
    parser.add_argument("--output-channel", type=int, default=0,
                        help="Output channel (0=left, 1=right). Default: 0")
    parser.add_argument("--input-channel", type=int, default=0,
                        help="Input channel (0-indexed). Default: 0")
    parser.add_argument("--label", type=str, default="mic_test",
                        help="Label for this mic (used in filenames & graph title)")
    parser.add_argument("--sample-rate", type=int, default=48000,
                        help="Sample rate in Hz. Default: 48000")
    parser.add_argument("--sweep-duration", type=float, default=3.0,
                        help="Sweep duration in seconds. Default: 3.0")
    parser.add_argument("--f-start", type=float, default=20.0,
                        help="Sweep start frequency in Hz. Default: 20")
    parser.add_argument("--f-stop", type=float, default=20000.0,
                        help="Sweep stop frequency in Hz. Default: 20000")
    parser.add_argument("--amplitude", type=float, default=0.3,
                        help="Sweep amplitude (0.0–1.0). Start low! Default: 0.3")
    parser.add_argument("--smoothing", type=float, default=6.0,
                        help="Smoothing in octave fractions (e.g. 6 = 1/6 oct). Default: 6")
    parser.add_argument("--reference", type=str, default=None,
                        help="Path to a .npz baseline file to overlay on the graph")
    parser.add_argument("--save-baseline", action="store_true",
                        help="Save this measurement as a baseline .npz file")
    parser.add_argument("--save-wav", action="store_true",
                        help="Save raw recorded audio as .wav")
    parser.add_argument("--output-dir", type=str, default="results",
                        help="Directory for output files. Default: results")
    parser.add_argument("--averages", type=int, default=1,
                        help="Number of sweeps to average. Default: 1")

    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        sys.exit(0)

    if args.output_device is None or args.input_device is None:
        print("Error: --output-device (-o) and --input-device (-i) are required.")
        print("       Use --list-devices to see available devices.")
        sys.exit(1)

    if not 0.0 < args.amplitude <= 1.0:
        print(f"Error: --amplitude must be between 0.0 (exclusive) and 1.0. "
              f"Got {args.amplitude}")
        sys.exit(1)

    if args.averages < 1:
        print(f"Error: --averages must be at least 1. Got {args.averages}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{args.label}_{timestamp}"

    print(f"\n{'='*60}")
    print(f"  Mic Test: {args.label}")
    print(f"  Sweep:    {args.f_start:.0f} – {args.f_stop:.0f} Hz, "
          f"{args.sweep_duration:.1f}s, amplitude {args.amplitude}")
    print(f"  Rate:     {args.sample_rate} Hz")
    print(f"  Output:   device {args.output_device}, ch {args.output_channel}")
    print(f"  Input:    device {args.input_device}, ch {args.input_channel}")
    print(f"  Averages: {args.averages}")
    print(f"{'='*60}\n")

    # Generate sweep and inverse filter
    print("Generating sweep …")
    sweep = generate_log_sweep(args.f_start, args.f_stop, args.sweep_duration,
                               args.sample_rate, args.amplitude)
    inv_filter = generate_inverse_filter(sweep, args.f_start, args.f_stop,
                                         args.sweep_duration, args.sample_rate)

    # Run measurement(s)
    recordings = []
    for run in range(args.averages):
        if args.averages > 1:
            print(f"\nSweep {run + 1}/{args.averages}:")
        rec = measure(sweep, args.sample_rate,
                      args.output_device, args.input_device,
                      args.output_channel, args.input_channel)
        recordings.append(rec)

        # Brief pause between sweeps to let any resonance die
        if run < args.averages - 1:
            time.sleep(0.5)

    # Average the recordings
    min_len = min(len(r) for r in recordings)
    recordings = [r[:min_len] for r in recordings]
    recording = np.mean(recordings, axis=0).astype(np.float32)

    # Check for silent or near-silent input
    rec_rms = np.sqrt(np.mean(recording ** 2))
    rec_dbfs = 20 * np.log10(rec_rms) if rec_rms > 0 else -np.inf
    if rec_dbfs < -60:
        print(f"\n  WARNING: Very low recording level ({rec_dbfs:.1f} dBFS)")
        print(f"     Check that the mic is connected and interface gain is set.")
        print(f"     Results may not be meaningful.\n")

    # Optionally save raw audio
    if args.save_wav:
        wav_path = os.path.join(args.output_dir, f"{base_name}.wav")
        wavfile.write(wav_path, args.sample_rate,
                      (recording * 32767).astype(np.int16))
        suffix = (f" (averaged from {args.averages} sweeps)"
                  if args.averages > 1 else "")
        print(f"  Saved WAV{suffix}: {wav_path}")

    # Compute frequency response
    print("Computing frequency response …")
    freqs, mag_db, ref_level = compute_frequency_response(
        recording, inv_filter, args.sample_rate,
        args.f_start, args.f_stop, args.smoothing
    )

    # Load reference if provided
    ref_freqs, ref_mag_db, ref_label, ref_ref_level = None, None, None, None
    if args.reference:
        if os.path.exists(args.reference):
            ref_data = np.load(args.reference)
            ref_freqs = ref_data["freqs"]
            ref_mag_db = ref_data["mag_db"]
            ref_label = (str(ref_data["label"]) if "label" in ref_data
                         else "Reference")
            ref_ref_level = (float(ref_data["ref_level"])
                             if "ref_level" in ref_data else None)
            print(f"  Loaded reference: {args.reference}")
        else:
            print(f"  Warning: reference file not found: {args.reference}")

    # Plot
    img_path = os.path.join(args.output_dir, f"{base_name}.png")
    plot_response(freqs, mag_db, args.label, img_path,
                  ref_freqs, ref_mag_db, ref_label)

    # Save baseline data
    if args.save_baseline:
        npz_path = os.path.join(args.output_dir, f"{base_name}.npz")
        np.savez(npz_path, freqs=freqs, mag_db=mag_db, label=args.label,
                 sample_rate=args.sample_rate, f_start=args.f_start,
                 f_stop=args.f_stop, timestamp=timestamp,
                 ref_level=ref_level)
        print(f"  Saved baseline: {npz_path}")

    # Print quick stats
    print(f"\n{'─'*60}")
    print(f"  Quick stats for {args.label}:")
    for band_name, (lo, hi) in [("Low (100–500 Hz)", (100, 500)),
                                 ("Mid (500–2kHz)", (500, 2000)),
                                 ("Presence (2k–6kHz)", (2000, 6000)),
                                 # Upper bound of 16kHz: coupler measurements
                                 # above 16kHz are unreliable due to chamber
                                 # resonances approaching wavelength scale
                                 ("Air (6k–16kHz)", (6000, 16000))]:
        band_mask = (freqs >= lo) & (freqs <= hi)
        if np.any(band_mask):
            avg = np.mean(mag_db[band_mask])
            pk = np.max(mag_db[band_mask])
            dip = np.min(mag_db[band_mask])
            print(f"    {band_name:24s}  avg {avg:+.1f} dB  "
                  f"(peak {pk:+.1f}, dip {dip:+.1f})")

    if ref_freqs is not None and ref_mag_db is not None:
        # Compute deviation from reference
        common_mask = (freqs >= args.f_start) & (freqs <= args.f_stop)
        ref_interp = np.interp(freqs[common_mask], ref_freqs, ref_mag_db)
        deviation = mag_db[common_mask] - ref_interp
        print(f"\n  Deviation from reference:")
        print(f"    Max: {np.max(np.abs(deviation)):.1f} dB")
        print(f"    Avg: {np.mean(np.abs(deviation)):.1f} dB")

        # Flag if HF is notably down (the gunk indicator)
        # Upper bound of 16kHz: same rationale as band analysis above
        hf_mask = (freqs[common_mask] >= 6000) & (freqs[common_mask] <= 16000)
        if np.any(hf_mask):
            hf_dev = np.mean(deviation[hf_mask])
            if hf_dev < -3:
                print(f"\n  ⚠  HIGH-FREQ ROLLOFF: {hf_dev:+.1f} dB avg above 6kHz")
                print(f"     This mic may need cleaning or replacement.")
            else:
                print(f"\n  ✓  HF response within spec ({hf_dev:+.1f} dB avg above 6kHz)")

        # Check for overall sensitivity loss/gain
        if ref_ref_level is not None:
            level_diff = ref_level - ref_ref_level
            if level_diff < -6:
                print(f"\n  ⚠  SENSITIVITY LOSS: {level_diff:+.1f} dB overall")
                print(f"     Broadband level drop suggests diaphragm damage.")
                print(f"     Cleaning the mesh will not fix this — capsule "
                      f"needs replacement.")
            elif level_diff > 6:
                print(f"\n  ⚠  SENSITIVITY GAIN: {level_diff:+.1f} dB overall")
                print(f"     Unexpected increase — check test setup "
                      f"consistency.")

    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
