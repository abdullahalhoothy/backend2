def convert_strings_to_ints(d):
    """
    Recursively converts all string values in a nested dictionary to integers
    where possible. Leaves other values unchanged.
    """
    if isinstance(d, dict):
        # Process each key-value pair in the dictionary
        return {k: convert_strings_to_ints(v) for k, v in d.items()}
    elif isinstance(d, list):
        # Process each item in a list (if the dictionary contains lists)
        return [convert_strings_to_ints(i) for i in d]
    elif isinstance(d, str):
        # Try converting the string to an integer
        try:
            return int(d)
        except ValueError:
            return d  # Leave as is if conversion fails
    else:
        # Return the value as is for non-dict, non-list, non-str types
        return d