from typing import Optional
import numpy as np

def saturating_add(a, b, min_val=0, max_val=None):
  """
  Infallible addition that saturates
  """
  result = a + b
  if max_val is not None and result > max_val:
      return max_val
  if result < min_val:
      return min_val
  return result
    
def saturating_sub(a, b, min_val=0, max_val=None):
  """
  Infallible subtraction that saturates
  """
  result = a - b
  if max_val is not None and result > max_val:
      return max_val
  if result < min_val:
      return min_val
  return result
    
def saturating_mul(a, b, min_val=0, max_val=None):
  """
  Infallible multiplication that saturates
  """
  result = a * b
  if max_val is not None and result > max_val:
      return max_val
  if result < min_val:
      return min_val
  return result
  
def saturating_div(a, b, min_val=0, max_val=None):
  """
  Infallible division that saturates, returns min_val on division errors
  """
  try:
    result = a / b
  except (ZeroDivisionError, OverflowError):
    return min_val  # Return min_val if an error occurs
  if max_val is not None and result > max_val:
      return max_val
  if result < min_val:
      return min_val
  return result

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

def remove_outliers_iqr(data, q1: Optional[int] = 25, q3: Optional[int] = 75):
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

  lower_bound = Q1 - 1.5 * IQR
  upper_bound = Q3 + 1.5 * IQR

  return data[(data >= lower_bound) & (data <= upper_bound)].tolist()
