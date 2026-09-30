"""
Алгоритм Робертса (упрощённый) — удаление невидимых рёбер выпуклого тела.

Идея для выпуклого многогранника:
1. Для каждой грани вычислить внешнюю нормаль.
2. Классифицировать грань относительно наблюдателя:
   - лицевая (front), если нормаль смотрит на камеру;
   - тыльная (back), если нормаль смотрит от камеры.
3. Ребро НЕВИДИМО, если обе смежные грани — тыльные.
4. Ребро ВИДИМО, если хотя бы одна смежная грань — лицевая
   (в том числе рёбра контура: front+back).

Для невыпуклых тел (буква «А» из ЛР1) этого недостаточно —
нужны более сложные методы. Вариант 2 задания — именно выпуклое тело.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Face = Tuple[int, ...]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _len(a: Vec3) -> float:
    return (_dot(a, a)) ** 0.5


def _normalize(a: Vec3) -> Vec3:
    L = _len(a)
    if L < 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / L, a[1] / L, a[2] / L)


def face_normal(vertices: Sequence[Vec3], face: Face) -> Vec3:
    """Внешняя нормаль грани (по первым трём вершинам, CCW снаружи)."""
    p0 = vertices[face[0]]
    p1 = vertices[face[1]]
    p2 = vertices[face[2]]
    return _normalize(_cross(_sub(p1, p0), _sub(p2, p0)))


def face_center(vertices: Sequence[Vec3], face: Face) -> Vec3:
    n = len(face)
    sx = sy = sz = 0.0
    for i in face:
        x, y, z = vertices[i]
        sx += x
        sy += y
        sz += z
    return (sx / n, sy / n, sz / n)


def is_front_face(
    vertices: Sequence[Vec3],
    face: Face,
    eye: Vec3,
) -> Tuple[bool, Vec3, float]:
    """
    Грань лицевая, если нормаль и вектор «к наблюдателю» сонаправлены
    (скалярное произведение > 0).

    eye — положение камеры в той же СК, что и вершины (после model-transform).
    Для перспективной камеры из ЛР1: eye ≈ (0, -focal, 0) в «мировой»
    системе до проекции, а вершины уже преобразованы моделью —
    поэтому eye передаём в мировых координатах сцены.
    """
    n = face_normal(vertices, face)
    c = face_center(vertices, face)
    # вектор от центра грани к глазу
    to_eye = _normalize(_sub(eye, c))
    nd = _dot(n, to_eye)
    return nd > 1e-9, n, nd


def build_edge_faces(faces: Sequence[Face]) -> Dict[Tuple[int, int], List[int]]:
    """Для каждого ребра (i<j) — список индексов смежных граней (1 или 2)."""
    mapping: Dict[Tuple[int, int], List[int]] = {}
    for fi, face in enumerate(faces):
        m = len(face)
        for k in range(m):
            a, b = face[k], face[(k + 1) % m]
            key = (a, b) if a < b else (b, a)
            mapping.setdefault(key, []).append(fi)
    return mapping


def roberts_classify(
    vertices: Sequence[Vec3],
    faces: Sequence[Face],
    edges: Sequence[Tuple[int, int]],
    eye: Vec3,
) -> Tuple[List[bool], List[bool], List[dict]]:
    """
    Классификация по Робертсу.

    Возвращает:
      face_front[i]  — True, если грань i лицевая;
      edge_visible[j] — True, если ребро j видимо;
      face_info — список словарей для демонстрации алгоритма.
    """
    face_front: List[bool] = []
    face_info: List[dict] = []
    for fi, face in enumerate(faces):
        front, normal, ndot = is_front_face(vertices, face, eye)
        face_front.append(front)
        face_info.append(
            {
                "index": fi,
                "front": front,
                "normal": normal,
                "n_dot_view": ndot,
                "sides": len(face),
            }
        )

    edge_to_faces = build_edge_faces(faces)
    edge_visible: List[bool] = []
    for a, b in edges:
        key = (a, b) if a < b else (b, a)
        adj = edge_to_faces.get(key, [])
        # Ребро видимо, если хотя бы одна смежная грань лицевая.
        # (Если грань одна — на границе; для замкнутого тела обычно две.)
        if not adj:
            visible = True
        else:
            visible = any(face_front[fi] for fi in adj)
        edge_visible.append(visible)

    return face_front, edge_visible, face_info
