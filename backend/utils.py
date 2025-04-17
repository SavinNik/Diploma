def string_to_bool(value):
    """
    Convert string to boolean.
    
    Args:
        value: String value to convert
        
    Returns:
        bool: True for 'true', '1', 'yes', 'on', 'y'
              False for 'false', '0', 'no', 'off', 'n'
              
    Raises:
        ValueError: If the value cannot be converted to boolean
    """
    if isinstance(value, bool):
        return value
    if value.lower() in ('true', '1', 'yes', 'on', 'y'):
        return True
    elif value.lower() in ('false', '0', 'no', 'off', 'n'):
        return False
    raise ValueError(f"Invalid boolean value: {value}")

