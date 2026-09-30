"""
math3d.py — матричная алгебра и аффинные преобразования в R^3.

Все операции реализованы вручную (без NumPy / OpenGL).
Точки задаются в однородных координатах: p = (x, y, z, 1)^T.
Преобразование: p' = M * p, где M — матрица 4×4.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

# Типы для наглядности
Vec3 = Tuple[float, float, float]       # декартовы (x, y, z)
Vec4 = Tuple[float, float, float, float]  # однородные (x, y, z, w)
Mat4 = List[List[float]]                # матрица 4×4 как список строк


def identity() -> Mat4:
    """Единичная матрица 4×4 (преобразование «ничего не менять»)."""
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def mat_mul(a: Mat4, b: Mat4) -> Mat4:
    """
    Умножение матриц 4×4: result = a * b.

    Порядок важен: (A*B)*p значит «сначала B, потом A»
    (вектор-столбец умножается справа).
    """
    result = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            # строка i матрицы a · столбец j матрицы b
            result[i][j] = (
                a[i][0] * b[0][j]
                + a[i][1] * b[1][j]
                + a[i][2] * b[2][j]
                + a[i][3] * b[3][j]
            )
    return result


def mat_vec(m: Mat4, v: Sequence[float]) -> Vec4:
    """
    Умножение матрицы 4×4 на вектор: p' = M * p.

    Если переданы только (x, y, z), четвёртая координата w = 1
    (обычная точка в однородных координатах).
    """
    x, y, z, w = v[0], v[1], v[2], v[3] if len(v) > 3 else 1.0
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3] * w,
        m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3] * w,
        m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3] * w,
        m[3][0] * x + m[3][1] * y + m[3][2] * z + m[3][3] * w,
    )


def translate(dx: float, dy: float, dz: float) -> Mat4:
    """
    Матрица переноса T.

        | 1  0  0  dx |
        | 0  1  0  dy |
        | 0  0  1  dz |
        | 0  0  0   1 |

    x' = x + dx,  y' = y + dy,  z' = z + dz.
    """
    m = identity()
    m[0][3] = dx
    m[1][3] = dy
    m[2][3] = dz
    return m


def scale(sx: float, sy: float, sz: float) -> Mat4:
    """
    Матрица масштабирования S.

        | sx  0   0  0 |
        |  0 sy   0  0 |
        |  0  0  sz  0 |
        |  0  0   0  1 |

    x' = sx*x,  y' = sy*y,  z' = sz*z.
    При sx = sy = sz — равномерный масштаб.
    """
    m = identity()
    m[0][0] = sx
    m[1][1] = sy
    m[2][2] = sz
    return m


def rotate_x(angle_rad: float) -> Mat4:
    """
    Поворот вокруг оси X на угол angle_rad (в радианах).
    c = cos φ, s = sin φ:

        | 1  0   0  0 |
        | 0  c  -s  0 |
        | 0  s   c  0 |
        | 0  0   0  1 |
    """
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rotate_y(angle_rad: float) -> Mat4:
    """
    Поворот вокруг оси Y на угол angle_rad (в радианах).
    c = cos φ, s = sin φ:

        |  c  0  s  0 |
        |  0  1  0  0 |
        | -s  0  c  0 |
        |  0  0  0  1 |
    """
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rotate_z(angle_rad: float) -> Mat4:
    """
    Поворот вокруг оси Z на угол angle_rad (в радианах).
    c = cos φ, s = sin φ:

        | c  -s  0  0 |
        | s   c  0  0 |
        | 0   0  1  0 |
        | 0   0  0  1 |
    """
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def transform_points(matrix: Mat4, points: Iterable[Vec3]) -> List[Vec3]:
    """
    Применить матрицу M ко всем точкам списка.

    1) Точка дополняется до однородных: (x, y, z, 1).
    2) Умножение: (x', y', z', w') = M * (x, y, z, 1).
    3) Если w' ≠ 1 (и ≠ 0) — возврат к декартовым: x'/w', y'/w', z'/w'.
    """
    out: List[Vec3] = []
    for x, y, z in points:
        tx, ty, tz, tw = mat_vec(matrix, (x, y, z, 1.0))
        # перспектива / однородные: деление на w'
        if abs(tw) > 1e-12:
            tx, ty, tz = tx / tw, ty / tw, tz / tw
        out.append((tx, ty, tz))
    return out


def perspective_project(
    point: Vec3,
    *,
    focal: float,
    screen_w: int,
    screen_h: int,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> Tuple[float, float]:
    """
    Центральная (перспективная) проекция 3D → 2D (пиксели экрана).

    Система координат сцены:
      X — вправо, Y — глубина, Z — вверх.

    Камера смотрит вдоль оси Y. Глубина точки: d = y + focal.
    Чем больше d, тем меньше проекция (дальше — меньше):

      xp = x * focal / d
      zp = z * focal / d

    Перевод в пиксели (начало — центр окна; экранная Y вниз):

      sx = W/2 + xp
      sy = H/2 - zp
    """
    x, y, z = point

    # расстояние от камеры до точки (не даём делить на ноль / «за камерой»)
    depth = y + focal
    if depth < 0.1:
        depth = 0.1

    # перспективное сжатие
    px = (x * focal) / depth
    py = (z * focal) / depth

    # в координаты окна
    sx = screen_w * 0.5 + px + offset_x
    sy = screen_h * 0.5 - py + offset_y  # минус: ось Y экрана вниз
    return sx, sy
