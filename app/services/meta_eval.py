def calculate_alignment(data_points):
    """
    Compares list of (machine_score, human_score).
    Returns average error (MAE).
    """
    if not data_points:
        return 0.0
    
    total_diff = sum([abs(m - h) for (_, m, h, _) in data_points])
    return total_diff / len(data_points)