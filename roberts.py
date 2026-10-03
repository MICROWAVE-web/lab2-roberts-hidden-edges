"""
roberts.py — алгоритм Робертса (упрощённый вариант).

Задача: какие РЁБРА выпуклого многогранника невидимы для наблюдателя?

Идея (только для ВЫПУКЛОГО тела!):
  1) У каждой грани считаем ВНЕШНЮЮ нормаль n.
  2) Смотрим, «повернута» ли грань к камере:
       front  ⇔  n · to_eye > 0
       back   ⇔  иначе
  3) Ребро принадлежит двум граням. Если ОБЕ грани back — ребро сзади
     тела и его не рисуем. Если хотя бы одна front — ребро видно
     (в т.ч. контур: front+back).

Почему не буква «А» из ЛР1?
  Она невыпуклая. Тогда ребро с двумя front-гранями всё равно может
  быть закрыто другой частью фигуры — нужен z-буфер / Варнок и т.п.

Связь с проекцией:
  to_eye должен соответствовать тому, КАК мы проектируем на экран.
  Перспектива → точка камеры eye.
  Ортогональ/аксонометрия → одно направление view_dir на все грани.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]
Face = Tuple[int, ...]  # индексы вершин одной грани


# ---------------------------------------------------------------------------
# Вспомогательная векторная алгебра (без NumPy)
# ---------------------------------------------------------------------------

def _sub(a: Vec3, b: Vec3) -> Vec3:
    """a − b."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vec3, b: Vec3) -> Vec3:
    """Векторное произведение a × b (результат ⊥ плоскости a,b)."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Vec3, b: Vec3) -> float:
    """Скалярное произведение a · b."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _len(a: Vec3) -> float:
    """Длина вектора |a|."""
    return (_dot(a, a)) ** 0.5


def _normalize(a: Vec3) -> Vec3:
    """Единичный вектор a/|a| (или нуль, если a ≈ 0)."""
    L = _len(a)
    if L < 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / L, a[1] / L, a[2] / L)


# ---------------------------------------------------------------------------
# Геометрия грани
# ---------------------------------------------------------------------------

def face_normal(vertices: Sequence[Vec3], face: Face) -> Vec3:
    """
    Внешняя нормаль грани.

    Берём первые три вершины P0, P1, P2.
    n = normalize( (P1−P0) × (P2−P0) ).

    Важно: вершины грани должны обходиться ПРОТИВ часовой стрелки,
    если смотреть СНАРУЖИ (CCW). Иначе нормаль будет внутрь тела,
    и front/back перепутаются.
    """
    p0 = vertices[face[0]]
    p1 = vertices[face[1]]
    p2 = vertices[face[2]]
    return _normalize(_cross(_sub(p1, p0), _sub(p2, p0)))


def face_center(vertices: Sequence[Vec3], face: Face) -> Vec3:
    """Центр грани = среднее арифметическое её вершин."""
    n = len(face)
    sx = sy = sz = 0.0
    for i in face:
        x, y, z = vertices[i]
        sx += x
        sy += y
        sz += z
    return (sx / n, sy / n, sz / n)


# ---------------------------------------------------------------------------
# Классификация «лицевая / тыльная»
# ---------------------------------------------------------------------------

def is_front_face(
    vertices: Sequence[Vec3],
    face: Face,
    *,
    eye: Optional[Vec3] = None,
    view_dir: Optional[Vec3] = None,
) -> Tuple[bool, Vec3, float]:
    """
    Грань лицевая (front), если нормаль смотрит на наблюдателя.

    Параметры (нужен ровно один):
      eye      — точка камеры (перспектива).
                 to_eye = normalize(eye − c)  — разный для каждой грани.
      view_dir — направление К камере (параллельная проекция).
                 одно на все грани (камера «в бесконечности»).

    Возвращает: (is_front, normal, n·to_eye).
    n·to_eye удобно смотреть на панели демо: >0 front, <0 back.
    """
    n = face_normal(vertices, face)
    c = face_center(vertices, face)

    if view_dir is not None:
        # Ортогональ / аксонометрия: все лучи параллельны
        to_eye = _normalize(view_dir)
    elif eye is not None:
        # Перспектива: лучи сходятся в точке eye
        to_eye = _normalize(_sub(eye, c))
    else:
        raise ValueError("Нужен eye или view_dir")

    nd = _dot(n, to_eye)
    # небольшой порог 1e-9, чтобы «ребро на грани» не мерцало из-за float
    return nd > 1e-9, n, nd


def build_edge_faces(faces: Sequence[Face]) -> Dict[Tuple[int, int], List[int]]:
    """
    Карта: ребро → список индексов смежных граней.

    Ребро храним как пару (min_index, max_index), чтобы (1,2) и (2,1)
    считались одним и тем же ребром.
    У замкнутого многогранника у каждого ребра обычно ровно 2 грани.
    """
    mapping: Dict[Tuple[int, int], List[int]] = {}
    for fi, face in enumerate(faces):
        m = len(face)
        for k in range(m):
            a, b = face[k], face[(k + 1) % m]  # соседние вершины по контуру
            key = (a, b) if a < b else (b, a)
            mapping.setdefault(key, []).append(fi)
    return mapping


# ---------------------------------------------------------------------------
# Главная функция: Робертс для всего объекта
# ---------------------------------------------------------------------------

def roberts_classify(
    vertices: Sequence[Vec3],
    faces: Sequence[Face],
    edges: Sequence[Tuple[int, int]],
    *,
    eye: Optional[Vec3] = None,
    view_dir: Optional[Vec3] = None,
) -> Tuple[List[bool], List[bool], List[dict]]:
    """
    Полная классификация граней и рёбер.

    Вход:
      vertices — уже после аффинных преобразований (мир/модель);
      faces, edges — топология объекта;
      eye / view_dir — взгляд (см. is_front_face).

    Выход:
      face_front[i]   — True, если грань i лицевая;
      edge_visible[j] — True, если ребро j нужно рисовать сплошной линией;
      face_info       — детали для панели демонстрации на защите.

    Правило для ребра:
      VIS  ⇔  есть хотя бы одна смежная front-грань
      hid  ⇔  все смежные грани back
    """
    # --- шаг 1: грани ---
    face_front: List[bool] = []
    face_info: List[dict] = []
    for fi, face in enumerate(faces):
        front, normal, ndot = is_front_face(
            vertices, face, eye=eye, view_dir=view_dir
        )
        face_front.append(front)
        face_info.append(
            {
                "index": fi,
                "front": front,
                "normal": normal,
                "n_dot_view": ndot,  # то, что видно в правой панели
                "sides": len(face),
            }
        )

    # --- шаг 2: рёбра ---
    edge_to_faces = build_edge_faces(faces)
    edge_visible: List[bool] = []
    for a, b in edges:
        key = (a, b) if a < b else (b, a)
        adj = edge_to_faces.get(key, [])  # индексы смежных граней
        if not adj:
            # ребро не из списка граней — на всякий случай считаем видимым
            visible = True
        else:
            # ключ Робертса для выпуклого тела:
            visible = any(face_front[fi] for fi in adj)
        edge_visible.append(visible)

    return face_front, edge_visible, face_info
