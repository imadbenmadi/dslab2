"""
Progress bar wrapper using tqdm.
"""

from tqdm import tqdm

def progress(iterable=None, desc=None, unit='it', total=None, leave=True):
    """
    Wrapper around tqdm for progress bars.
    """
    return tqdm(iterable=iterable, desc=desc, unit=unit, total=total, leave=leave)
