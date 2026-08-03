import matplotlib.pyplot as plt
import numpy as np
from laboneq.simple import *

"""
Pulse library for use with ZI hardware. Imported with instantiation of ZIQubit.
"""

@pulse_library.register_pulse_functional
def flattop_gaussian_two_stage(
    x,
    relative_length_flat=0.7,
    relative_length_buffer=0.1,
    buffer_amp_proportion=0.8, 
    **_
):
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
    res[mask] = buffer_amp_proportion + (1 - buffer_amp_proportion) * np.exp(
        -((np.abs(x[mask]) - b0) ** 2) / (2 * sigma**2)
    )

    # buffer plateau
    mask = (np.abs(x) > b1) & (np.abs(x) <= b2)
    res[mask] = buffer_amp_proportion

    # second ramp: buffer_amp_proportion -> 0
    mask = np.abs(x) > b2
    res[mask] = buffer_amp_proportion * np.exp(
        -((np.abs(x[mask]) - b2) ** 2) / (2 * sigma**2)
    )

    return res

@pulse_library.register_pulse_functional
def flattop_gaussian_buffer_asymmetric(
    x,
    relative_length_flat=0.7,
    relative_length_buffer=0.1,
    buffer_amp_proportion=0.8,
    **_
):
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
    b1 = b0_left + ramp_width_left
    b2 = b1 + relative_length_buffer

    # right-side plateau is shifted out by relative_length_buffer, so the
    # single ramp after it has exactly enough (and no more) room to reach
    # x=1 with the same sigma-scaling convention as the left ramps
    b0_right = relative_length_flat + relative_length_buffer
    ramp_width_right = 1 - b0_right  # == 1 - relative_length_flat - relative_length_buffer
    sigma_right = ramp_width_right / 3

    # LEFT: ramp 1 -> buffer_amp_proportion
    mask = (x < -b0_left) & (x >= -b1)
    res[mask] = buffer_amp_proportion + (1 - buffer_amp_proportion) * np.exp(
        -((np.abs(x[mask]) - b0_left) ** 2) / (2 * sigma_left**2)
    )

    # LEFT: buffer plateau
    mask = (x < -b1) & (x >= -b2)
    res[mask] = buffer_amp_proportion

    # LEFT: ramp buffer_amp_proportion -> 0
    mask = x < -b2
    res[mask] = buffer_amp_proportion * np.exp(
        -((np.abs(x[mask]) - b2) ** 2) / (2 * sigma_left**2)
    )

    # RIGHT: single ramp 1 -> 0, starting from the extended plateau edge
    mask = x > b0_right
    res[mask] = np.exp(-((x[mask] - b0_right) ** 2) / (2 * sigma_right**2))

    return res