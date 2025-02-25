from typing import Optional
import numpy as np

def iqr(data, q1: Optional[int] = 25, q3: Optional[int] = 75):
  """
  Calculates Interquartile Range (IQR) using numpy

  Args:
    data (list): list of integers.
    q1 (int): first quartile.
    q3 (int): third quartile.

  Returns:
    int: The sum of the two numbers.

  Example:
    >>> iqr([1, 3, 5, 7, 9, 11, 13, 15, 1000], q1=25, q3=75)
    8.0
  """

  Q1 = np.percentile(data, q1)
  Q3 = np.percentile(data, q3)

  IQR = Q3 - Q1

  return IQR

def remove_outliers_iqr(
  data, 
  q1: Optional[int] = 25, 
  q3: Optional[int] = 75,
  lower_multiplier: Optional[float] = 1.5,
  upper_multiplier: Optional[float] = 1.5
):
  """
  Removes outliers from a numpy array using the interquartile range (IQR) method

  Args:
    data (list): list of integers.
    q1 (int): first quartile.
    q3 (int): third quartile.

  Returns:
    int: Array from numpy array

  Example:
    >>> remove_outliers_iqr([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100], q1=25, q3=75)
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  """
  data = np.array(data)

  Q1 = np.percentile(data, q1)
  Q3 = np.percentile(data, q3)
  IQR = Q3 - Q1

  lower_bound = Q1 - lower_multiplier * IQR
  upper_bound = Q3 + upper_multiplier * IQR

  return data[(data >= lower_bound) & (data <= upper_bound)].tolist()

def remove_outliers_mad(data, threshold: Optional[float] = 3.5, mad_fallback: Optional[float] =1e-6):
    """
    Removes outliers using the Median Absolute Deviation (MAD) method.

    Args:
        data (list): List of numbers.
        threshold (float): Sensitivity for detecting outliers (default: 3.5).
        mad_fallback (float): Small fallback value for MAD if it is zero (default: 1e-6).

    Returns:
        list: Filtered data with outliers removed.
    """
    # If there's not enough data to determine outliers, return the original data
    if len(data) < 3:
        return data

    # Step 1: Calculate the median of the dataset
    median = np.median(data)

    # Step 2: Calculate the absolute deviation from the median
    abs_deviation = np.abs(np.array(data) - median)

    # Step 3: Calculate the median of the absolute deviations (MAD)
    mad = np.median(abs_deviation)

    # Step 4: If MAD is zero, use a small fallback value to prevent division by zero
    if mad == 0:
        mad = mad_fallback

    # Step 5: Calculate modified Z-scores using MAD (scaled by MAD)
    modified_z_scores = abs_deviation / mad

    # Step 6: Filter out values with modified Z-scores above the threshold
    filtered_data = [x for x, score in zip(data, modified_z_scores) if score < threshold]

    return filtered_data

def remove_outliers_zscore(data, threshold: Optional[float] = 2.0):
    """
    Removes outliers using the Z-score method.

    Args:
        data (list): List of numbers.
        threshold (float): Z-score threshold (default: 2.0).

    Returns:
        list: Filtered data with outliers removed.
    """
    if len(data) < 3:
        return data

    mean = np.mean(data)
    std_dev = np.std(data)

    if std_dev == 0:
        return data  # Prevent division by zero

    z_scores = [(x - mean) / std_dev for x in data]

    return [x for x, z in zip(data, z_scores) if abs(z) < threshold]

def remove_outliers_adaptive(data):
    """
    Automatically selects the best outlier removal method based on dataset size.
    """
    n = len(data)
    if n < 10:
      return remove_outliers_mad(data)  # Use MAD for very small datasets
    elif 10 <= n < 30:
      return remove_outliers_zscore(data)  # Use Z-score for medium datasets
    else:
      return remove_outliers_iqr(data)  # Use IQR for large datasets
