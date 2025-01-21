
RADIUS_ZOOM_MULTIPLIER = {
    30000.0: 1000, # 1
    15000.0: 500, # 2
    7500.0: 250, # 3
    3750.0: 125, # 4
    1875.0: 62.5, # 5
    937.5: 31.25, # 6
    468.75: 15.625 # 7
}

def calculate_category_multiplier(index):
    """Calculate category multiplier based on result position."""
    if 0 <= index < 5:  # Category A
        return 1.0
    elif 5 <= index < 10:  # Category B
        return 0.8
    elif 10 <= index < 15:  # Category C
        return 0.6
    else:  # Category D
        return 0.4