"""Compiled matrix capacity; distinct from the browser's mesh budget."""
try:
    from _reasitic_numeric import matrix_capacity
except ImportError:
    MATRIX_CAPACITY=0
else:
    MATRIX_CAPACITY=int(matrix_capacity())
