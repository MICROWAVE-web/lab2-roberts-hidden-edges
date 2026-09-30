"""
Выпуклый многогранник: 6 граней (многоугольники 3–4 стороны).

Объект — прямоугольный параллелепипед (выпуклое тело).
Буква «А» из ЛР1 невыпуклая, поэтому для алгоритма Робертса
нужен именно выпуклый многогранник (вариант 2 задания).
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Face = Tuple[int, ...]  # индексы вершин грани (обход против часовой, если смотреть снаружи)


def build_convex_box(
    width: float = 140.0,
    height: float = 100.0,
    depth: float = 90.0,
) -> Tuple[List[Vec3], List[Face], List[Tuple[int, int]]]:
    """
    Параллелепипед, центр в начале координат.
    8 вершин, 6 граней (четырёхугольники), рёбра выводятся из граней.
    """
    w, h, d = width / 2.0, height / 2.0, depth / 2.0
    # нумерация:
    #   4------5        z up
    #  /|     /|        y depth (на нас при y+)
    # 7------6 |        x right
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

    # Грани: обход CCW при взгляде снаружи (внешняя нормаль наружу)
    faces: List[Face] = [
        (0, 1, 5, 4),  # задняя  (y = -d) нормаль -Y
        (2, 3, 7, 6),  # передняя (y = +d) нормаль +Y
        (3, 0, 4, 7),  # левая   (x = -w) нормаль -X
        (1, 2, 6, 5),  # правая  (x = +w) нормаль +X
        (0, 3, 2, 1),  # нижняя  (z = -h) нормаль -Z
        (4, 5, 6, 7),  # верхняя (z = +h) нормаль +Z
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
    «Домик»: 5 боковых/торцевых + основание + 2 ската = 7 граней — многовато.

    Вместо него — квадратная пирамида: 5 граней (4 треугольника + основание).
    Подходит под «5–6 многоугольников».
    """
    w, h, d = width / 2.0, height / 2.0, depth / 2.0
    apex_z = h + roof
    vertices: List[Vec3] = [
        (-w, -d, -h),  # 0 основание
        (w, -d, -h),   # 1
        (w, d, -h),    # 2
        (-w, d, -h),   # 3
        (0.0, 0.0, apex_z),  # 4 вершина
    ]
    faces: List[Face] = [
        (0, 3, 2, 1),  # основание (нормаль вниз) — обход так, чтобы нормаль -Z
        (0, 1, 4),     # задний скат
        (1, 2, 4),     # правый
        (2, 3, 4),     # передний
        (3, 0, 4),     # левый
    ]
    return vertices, faces, edges_from_faces(faces)


def edges_from_faces(faces: Sequence[Face]) -> List[Tuple[int, int]]:
    """Уникальные рёбра (i < j) по всем граням."""
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
    return ["задняя", "передняя", "левая", "правая", "нижняя", "верхняя"]


def face_names_pyramid() -> List[str]:
    return ["основание", "скат −Y", "скат +X", "скат +Y", "скат −X"]
