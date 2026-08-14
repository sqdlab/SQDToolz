import matplotlib.pyplot as plt
import numpy as np
from laboneq.simple import *
import laboneq.dsl.experiment.pulse

"""
Pulse library for use with ZI hardware. Imported with instantiation of ZIQubit.
"""

@pulse_library.register_pulse_functional
def flattop_gaussian_buffer(x, relative_length_flat=0.7, relative_length_buffer=0.1, buffer_amp_proportion=0.8, **_ ):
    """
    Two-stage flat-top Gaussian pulse (right half, mirrored on the left):

      [0, b0]   flat at 1                          (top plateau)
      [b0, b1]  Gaussian ramp: 1 -> buffer_amp_proportion
      [b1, b2]  flat at buffer_amp_proportion       (buffer plateau)
      [b2, 1]   Gaussian ramp: buffer_amp_proportion -> 0

    relative_length_flat   : half-width of the top plateau
    relative_length_buffer : width of the intermediate buffer plateau
    buffer_amp_proportion  : amplitude of the buffer plateau (0-1)

    Whatever length remains after the two plateaus is split evenly
    between the two Gaussian ramps.
    """
    x = np.asarray(x, dtype=float)
    res = np.ones(len(x))

    ramp_width = (1 - relative_length_flat - relative_length_buffer) / 2
    if ramp_width <= 0:
        raise ValueError("relative_length_flat + relative_length_buffer must be < 1")
    sigma = ramp_width / 3

    b0 = relative_length_flat
    b1 = b0 + ramp_width
    b2 = b1 + relative_length_buffer

    # first ramp: 1 -> buffer_amp_proportion
    mask = (np.abs(x) > b0) & (np.abs(x) <= b1)
    res[mask] = buffer_amp_proportion + (1 - buffer_amp_proportion) * np.exp( -((np.abs(x[mask]) - b0) ** 2) / (2 * sigma**2) )
    # buffer plateau
    mask = (np.abs(x) > b1) & (np.abs(x) <= b2)
    res[mask] = buffer_amp_proportion

    # second ramp: buffer_amp_proportion -> 0
    mask = np.abs(x) > b2
    res[mask] = buffer_amp_proportion * np.exp( -((np.abs(x[mask]) - b2) ** 2) / (2 * sigma**2) )

    return res

@pulse_library.register_pulse_functional
def impulse(x, relative_location=0.0, num_samples=1, **_):
    """
    Discrete impulse (delta) pulse, expressed in the same x-array,
    mask-based style as the other pulse shapes.

    x is assumed to be a normalized sample-index array (e.g. via
    np.linspace(-1, 1, num_samples)), but relative_location is
    expressed as a fraction of total length: 0.0 = start of the
    array, 1.0 = end, 0.5 = center. The impulse holds at amplitude 1
    for `num_samples` consecutive samples starting at that location;
    every other sample is zero.

    relative_location : fraction of total length (0-1) at which the
                         impulse starts
    num_samples        : number of consecutive samples the impulse
                         holds at amplitude 1
    """
    x = np.asarray(x, dtype=float)
    res = np.zeros(len(x))
    assert isinstance(num_samples, int), "Provide num_samples as an int."

    # map the 0-1 fraction onto x's own domain, then snap to the
    # nearest sample so any location value maps to a specific index
    target = x[0] + relative_location * (x[-1] - x[0])
    idx = np.argmin(np.abs(x - target))

    end_idx = min(idx + num_samples, len(x))
    res[idx:end_idx] = 1

    return res

@pulse_library.register_pulse_functional
def square(x, **_):
    x = np.asarray(x, dtype=float)
    return np.ones(len(x))

@pulse_library.register_pulse_functional
def flattop_gaussian_buffer_asymmetric(x, relative_length_flat=0.7, relative_length_buffer=0.1, buffer_amp_proportion=0.8, **_ ):
    """
    Asymmetric flat-top Gaussian pulse: buffer plateau only on the
    left-hand (trailing, x < 0) side. The right-hand (leading, x > 0)
    side is a single, quick Gaussian ramp straight down to zero.

    The top plateau itself is asymmetric: it ends at -b0_left on the
    left, but extends further out to +b0_right on the right, since the
    right side doesn't need to reserve space for a buffer plateau. This
    avoids a dead flat-zero region at the tail of the right-side ramp.

      LEFT side (x < 0):
        [-b0_left, 0]   flat at 1                        (top plateau)
        [-b1, -b0_left] Gaussian ramp: 1 -> buffer_amp_proportion
        [-b2, -b1]      flat at buffer_amp_proportion     (buffer plateau)
        [-1, -b2]       Gaussian ramp: buffer_amp_proportion -> 0

      RIGHT side (x > 0):
        [0, b0_right]  flat at 1                          (top plateau, extended)
        [b0_right, 1]  quick Gaussian ramp: 1 -> 0, ending exactly at x=1

    relative_length_flat   : half-width of the top plateau on the LEFT side
    relative_length_buffer : width of the buffer plateau (left side only);
                              also how much further the RIGHT plateau
                              extends, to absorb the space the left side
                              spends on its buffer
    buffer_amp_proportion  : amplitude of the buffer plateau (0-1)
    """
    x = np.asarray(x, dtype=float)
    res = np.ones(len(x))

    b0_left = relative_length_flat

    # left-side (buffered) ramp geometry
    ramp_width_left = (1 - relative_length_flat - relative_length_buffer) / 2
    if ramp_width_left <= 0:
        raise ValueError("relative_length_flat + relative_length_buffer must be < 1")
    sigma_left = ramp_width_left / 3
    b1 = b0_legenerate_sampled_pulseft + ramp_width_left
    b2 = b1 + relative_length_buffer

    # right-side plateau is shifted out by relative_length_buffer, so the
    # single ramp after it has exactly enough (and no more) room to reach
    # x=1 with the same sigma-scaling convention as the left ramps
    b0_right = relative_length_flat + relative_length_buffer
    ramp_width_right = 1 - b0_right  # == 1 - relative_length_flat - relative_length_buffer
    sigma_right = ramp_width_right / 3

    # LEFT: ramp 1 -> buffer_amp_proportion
    mask = (x < -b0_left) & (x >= -b1)
    res[mask] = buffer_amp_proportion + (1 - buffer_amp_proportion) * np.exp( -((np.abs(x[mask]) - b0_left) ** 2) / (2 * sigma_left**2) )

    # LEFT: buffer plateau
    mask = (x < -b1) & (x >= -b2)
    res[mask] = buffer_amp_proportion

    # LEFT: ramp buffer_amp_proportion -> 0
    mask = x < -b2
    res[mask] = buffer_amp_proportion * np.exp( -((np.abs(x[mask]) - b2) ** 2) / (2 * sigma_left**2) )

    # RIGHT: single ramp 1 -> 0, starting from the extended plateau edge
    mask = x > b0_right
    res[mask] = np.exp(-((x[mask] - b0_right) ** 2) / (2 * sigma_right**2))

    return res



def plot_sampled_pulse(pulse, iq=True, amp_phi=False, function=None, title=None):
    assert isinstance(pulse, tuple), "Provide a sampled pulse, which should be a tuple containing an array of time points, and an equal length array of complex values."
    if amp_phi:
        iq = False
    assert iq ^ amp_phi, "Either 'iq' or 'amp_phi' must be True."
    #
    if title:
        title = title
    elif function:
        title = function
    else:
        title = ""
    #
    times, samples = pulse
    times = times*1e9
    samples = np.asarray(samples)
    if iq:
        fig, ax = plt.subplots(figsize=(8,4))
        ax.plot(times, samples.real, label="I", color="tab:blue")
        ax.plot(times, samples.imag, label="Q", color="tab:orange")
        ax.set_xlabel("t (ns)")
        ax.set_ylabel("Amplitude")
        ax.legend()
        ax.set_title(f"{title}")
    else:  # amp_phi
        amplitude = np.abs(samples)
        phase = np.angle(samples)
        #
        fig, ax_amp = plt.subplots(figsize=(8, 4))
        ax_phi = ax_amp.twinx()
        #
        line_amp, = ax_amp.plot(times, amplitude, color="tab:blue", label="Amplitude")
        ax_amp.set_xlabel("t (ns)")
        ax_amp.set_ylabel("Amp", color="tab:blue")
        ax_amp.tick_params(axis="y", labelcolor="tab:blue")
        #
        line_phi, = ax_phi.plot(times, phase, color="tab:orange", label="Phase")
        ax_phi.set_ylabel("$\phi$ (rad)", color="tab:orange")
        ax_phi.tick_params(axis="y", labelcolor="tab:orange")
        #
        _align_zero(ax_amp, ax_phi)
        ax_amp.set_title(f"{title}")
    plt.tight_layout()
    plt.show()
    return ax;

def plot_pulse(pulse, iq=True, amp_phi=False, title=None):
    if isinstance(pulse, tuple):
        sampled_pulse = pulse
        function = None
    elif isinstance(pulse, laboneq.dsl.experiment.pulse.PulseFunctional):
        sampled_pulse = pulse.generate_sampled_pulse()
        function = pulse.function
    elif isinstance(pulse, laboneq.dsl.experiment.pulse.PulseSampled):
        sampled_pulse = pulse.samples
        function = pulse.uid
    ax = plot_sampled_pulse(sampled_pulse, iq=iq, amp_phi=amp_phi, function=function, title=title)
    return ax;

def _align_zero(ax1, ax2):
    """Rescale y-limits of two twin axes so that y=0 lines up on both."""
    y1_min, y1_max = ax1.get_ylim()
    y2_min, y2_max = ax2.get_ylim()
    frac1 = -y1_min / (y1_max - y1_min) if (y1_max - y1_min) != 0 else 0.5
    frac2 = -y2_min / (y2_max - y2_min) if (y2_max - y2_min) != 0 else 0.5
    frac = max(frac1, frac2)  # use the larger "below zero" fraction for both
    def rescale(ymin, ymax, frac):
        span_above = ymax
        span_below = -ymin
        if frac == 0:
            new_min = ymin
            new_max = ymax
        else:
            total_below = max(span_below, span_above * frac / (1 - frac)) if frac < 1 else span_below
            total_above = max(span_above, span_below * (1 - frac) / frac) if frac > 0 else span_above
            new_min = -total_below
            new_max = total_above
        return new_min, new_max

    ax1.set_ylim(*rescale(y1_min, y1_max, frac))
    ax2.set_ylim(*rescale(y2_min, y2_max, frac))

# def apply_pulse_precompensation(x, filter):
#     return 0

# We need to add a few more pulse shapes in the future
#   - Slepian
#
#
#
#import laboneq.dsl.experiment.pulse