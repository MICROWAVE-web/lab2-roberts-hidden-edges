"""
polyhedron.py — модели ВЫПУКЛЫХ многогранников для ЛР2.

Задание: 5–6 многоугольников в пространстве (по 3–6 сторон).
Вариант Робертса требует ВЫПУКЛОЕ тело → параллелепипед (6) или пирамида (5).

Формат данных:
  vertices : список (x, y, z)
  faces    : список кортежей индексов вершин (контур грани)
  edges    : уникальные пары (i, j), i < j

Система координат (как в ЛР1):
  X — вправо, Y — глубина, Z — вверх.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
# Face: обход вершин ПРОТИВ часовой (CCW), если смотреть СНАРУЖИ.
# Иначе внешняя нормаль в roberts.face_normal получится внутрь!
Face = Tuple[int, ...]


def build_convex_box(
    width: float = 140.0,
    height: float = 100.0,
    depth: float = 90.0,
) -> Tuple[List[Vec3], List[Face], List[Tuple[int, int]]]:
    """
    Прямоугольный параллелепипед (выпуклый), центр в (0,0,0).

    8 вершин, 6 четырёхугольных граней, 12 рёбер.
    Клавиша B в программе.
    """
    # половины размеров — чтобы центр был в начале координат
    w, h, d = width / 2.0, height / 2.0, depth / 2.0

    # Нумерация вершин (схема):
    #   4------5          Z вверх
    #  /|     /|          Y «на нас» при увеличении
    # 7------6 |          X вправо
    # | 0----|-1
    # |/     |/
    # 3------2
    vertices: List[Vec3] = [
        (-w, -d, -h),  # 0
        (w, -d, -h),   # 1
        (w, d, -h),    # 2
        (-w, d, -h),   # 3
        (-w, -d, h),   # 4
        (w, -d, h),    # 5
        (w, d, h),     # 6
        (-w, d, h),    # 7
    ]

    # Каждая грань: CCW снаружи → нормаль наружу (проверено в тестах: c·n > 0)
    faces: List[Face] = [
        (0, 1, 5, 4),  # задняя   y = −d → нормаль −Y
        (2, 3, 7, 6),  # передняя y = +d → нормаль +Y
        (3, 0, 4, 7),  # левая    x = −w → нормаль −X
        (1, 2, 6, 5),  # правая   x = +w → нормаль +X
        (0, 3, 2, 1),  # нижняя   z = −h → нормаль −Z
        (4, 5, 6, 7),  # верхняя  z = +h → нормаль +Z
    ]

    edges = edges_from_faces(faces)
    return vertices, faces, edges


def build_convex_house(
    width: float = 130.0,
    height: float = 80.0,
    depth: float = 90.0,
    roof: float = 55.0,
) -> Tuple[List[Vec3], List[Face], List[Tuple[int, int]]]:
    """
    Квадратная пирамида: 5 граней (основание + 4 треугольных ската).

    Имя функции историческое («домик»), по сути — пирамида.
    Клавиша P в программе. Подходит под «5–6 многоугольников».
    """
    w, h, d = width / 2.0, height / 2.0, depth / 2.0
    apex_z = h + roof  # вершина пирамиды над основанием

    vertices: List[Vec3] = [
        (-w, -d, -h),        # 0..3 — квадрат основания
        (w, -d, -h),
        (w, d, -h),
        (-w, d, -h),
        (0.0, 0.0, apex_z),  # 4 — вершина (apex)
    ]

    faces: List[Face] = [
        (0, 3, 2, 1),  # основание, нормаль −Z
        (0, 1, 4),     # скат со стороны −Y
        (1, 2, 4),     # скат +X
        (2, 3, 4),     # скат +Y
        (3, 0, 4),     # скат −X
    ]
    return vertices, faces, edges_from_faces(faces)


def edges_from_faces(faces: Sequence[Face]) -> List[Tuple[int, int]]:
    """
    Собрать уникальные рёбра по контурам всех граней.

    Каждое ребро встречается у двух граней — в список кладём один раз
    как упорядоченную пару (i, j), i < j.
    """
    seen = set()
    edges: List[Tuple[int, int]] = []
    for face in faces:
        n = len(face)
        for k in range(n):
            a, b = face[k], face[(k + 1) % n]
            key = (a, b) if a < b else (b, a)
            if key not in seen:
                seen.add(key)
                edges.append(key)
    return edges


def face_names_box() -> List[str]:
    """Подписи граней параллелепипеда для правой панели."""
    return ["задняя", "передняя", "левая", "правая", "нижняя", "верхняя"]


def face_names_pyramid() -> List[str]:
    """Подписи граней пирамиды для правой панели."""
    return ["основание", "скат −Y", "скат +X", "скат +Y", "скат −X"]
