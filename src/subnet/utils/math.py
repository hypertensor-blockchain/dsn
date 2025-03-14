def safe_div(numerator, denominator):
  """
  Performs safe division. Returns 0 if a division error occurs (e.g., division by zero).
  
  Args:
      numerator (int or float): The numerator for the division.
      denominator (int or float): The denominator for the division.
  
  Returns:
      float: The result of the division, or 0 if there's an error (e.g., division by zero).
  """
  try:
    return numerator / denominator
  except ZeroDivisionError:
    return 0
    
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