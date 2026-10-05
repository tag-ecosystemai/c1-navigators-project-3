import statistics


def z_score(values, value):
    if len(values) < 2: return 0.0
    deviation = statistics.pstdev(values)
    return 0.0 if deviation == 0 else abs(value - statistics.mean(values)) / deviation
