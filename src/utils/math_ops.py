"""Модуль с математическими утилитами."""

def factorial(n: int) -> int:
    """Вычисляет факториал числа n.

    Args:
        n (int): Число, для которого вычисляется факториал.

    Returns:
        int: Факториал числа n.

    Raises:
        ValueError: Если n отрицательное.
    """
    if n < 0:
        raise ValueError("Факториал определен только для неотрицательных чисел.")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result