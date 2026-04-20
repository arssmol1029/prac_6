def sqroots(coeffs:str) -> str:
    """Return ax^2 + bx + c = 0 roots"""
    try:
        a, b, c = map(float, coeffs.split())
    except ValueError:
        raise ValueError("Invalid coefficients")

    if a == 0:
        raise ValueError("a cannot be zero")

    d = b**2 - 4*a*c
    if d < 0:
        return ""
    elif d == 0:
        x = -b / (2*a)
        return f"{x}"
    else:
        x1, x2 = sorted([(-b + d**0.5) / (2*a), (-b - d**0.5) / (2*a)])
        return f"{x1} {x2}"
