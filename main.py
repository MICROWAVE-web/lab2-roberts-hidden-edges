#!/usr/bin/env python3
"""
Лабораторная работа 2.
Удаление невидимых линий и поверхностей.

Вариант 2: простой алгоритм удаления невидимых рёбер у ВЫПУКЛОГО тела
с динамикой (вращение) — алгоритм Робертса.

База: аффинные преобразования и проекции из ЛР1 (math3d.py).
Объект ЛР1 (буква «А») невыпуклый → для Робертса используем выпуклый
многогранник (параллелепипед / пирамида, 5–6 граней).
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import List, Optional, Tuple

from math3d import (
    Mat4,
    identity,
    mat_mul,
    perspective_project,
    rotate_x,
    rotate_y,
    rotate_z,
    scale,
    transform_points,
    translate,
)
from polyhedron import (
    build_convex_box,
    build_convex_house,
    face_names_box,
    face_names_pyramid,
)
from roberts import face_center, roberts_classify

Vec3 = Tuple[float, float, float]
RGB = Tuple[int, int, int]


def hex_rgb(color: str) -> RGB:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


class SoftCanvas:
    """RGB-буфер → PPM → PhotoImage (обход бага Canvas на macOS)."""

    def __init__(self, width: int, height: int, bg: str) -> None:
        self.bg = hex_rgb(bg)
        self.width = 0
        self.height = 0
        self.buf = bytearray()
        self.image: Optional[tk.PhotoImage] = None
        self.resize(width, height)

    def resize(self, width: int, height: int) -> None:
        width = max(160, int(width))
        height = max(120, int(height))
        if width == self.width and height == self.height and self.buf:
            return
        self.width = width
        self.height = height
        self.buf = bytearray(width * height * 3)
        self.clear()

    def clear(self) -> None:
        r, g, b = self.bg
        self.buf[:] = bytes((r, g, b)) * (self.width * self.height)

    def point(self, x: int, y: int, rgb: RGB) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.buf[i : i + 3] = bytes(rgb)

    def line(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        color: str,
        *,
        dashed: bool = False,
        thick: bool = True,
    ) -> None:
        rgb = hex_rgb(color)
        x0i, y0i = int(round(x0)), int(round(y0))
        x1i, y1i = int(round(x1)), int(round(y1))
        dx = abs(x1i - x0i)
        dy = -abs(y1i - y0i)
        sx = 1 if x0i < x1i else -1
        sy = 1 if y0i < y1i else -1
        err = dx + dy
        x, y = x0i, y0i
        step = 0
        while True:
            draw = (not dashed) or ((step // 4) % 2 == 0)
            if draw:
                self.point(x, y, rgb)
                if thick:
                    self.point(x + 1, y, rgb)
                    self.point(x, y + 1, rgb)
            if x == x1i and y == y1i:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
            step += 1

    def flush(self) -> tk.PhotoImage:
        header = f"P6 {self.width} {self.height} 255\n".encode("ascii")
        self.image = tk.PhotoImage(data=header + self.buf)
        return self.image


class RobertsApp:
    BG = "#f4efe6"
    VISIBLE = "#b91c1c"
    HIDDEN = "#94a3b8"
    NORMAL = "#2563eb"
    TEXT = "#111827"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ЛР2 — Алгоритм Робертса | Невидимые рёбра выпуклого тела")
        self.root.geometry("1100x720")
        self.root.minsize(800, 560)
        self.root.configure(bg=self.BG)

        self.width = 720
        self.height = 560

        # --- верхняя строка статуса ---
        self.status = tk.Label(
            root,
            text="Загрузка…",
            anchor="w",
            padx=10,
            pady=6,
            bg="#111827",
            fg="#f9fafb",
            font=("Menlo", 11),
        )
        self.status.pack(side=tk.TOP, fill=tk.X)

        # --- низ: управление ---
        self.help = tk.Label(
            root,
            text=(
                "Пробел — анимация | H — скрытые рёбра | N — нормали | B/P — бокс/пирамида | "
                "1/2 — проекция | ЛКМ — вращение | WASD — перенос | 0 — сброс | Esc — выход"
            ),
            anchor="w",
            padx=10,
            pady=6,
            bg="#e7dfd2",
            fg=self.TEXT,
            font=("TkDefaultFont", 11),
        )
        self.help.pack(side=tk.BOTTOM, fill=tk.X)

        body = tk.Frame(root, bg=self.BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # панель демонстрации алгоритма (важно для защиты)
        self.info = tk.Text(
            body,
            width=36,
            height=20,
            bg="#1e293b",
            fg="#e2e8f0",
            font=("Menlo", 10),
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        self.info.pack(side=tk.RIGHT, fill=tk.Y)
        self.info.configure(state=tk.DISABLED)

        self.frame = tk.Frame(body, bg="#94a3b8", padx=2, pady=2)
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.soft = SoftCanvas(self.width, self.height, self.BG)
        self.soft.flush()
        self.view = tk.Label(self.frame, image=self.soft.image, bg=self.BG, bd=0)
        self.view.pack(fill=tk.BOTH, expand=True)
        self.view.image = self.soft.image

        self.model_kind = "box"  # box | pyramid
        self._load_model()

        self.tx = self.ty = self.tz = 0.0
        self.rx = math.radians(-22.0)
        self.ry = math.radians(35.0)
        self.rz = 0.0
        self.sx = self.sy = self.sz = 1.0

        self.perspective = True
        self.focal = 420.0
        self.animating = True
        self.anim_t = 0.0
        self.show_hidden = True
        self.show_normals = True
        self.frame_id = 0

        self._drag: Optional[Tuple[int, int]] = None
        self._bind()

        self.root.update_idletasks()
        self._sync_size()
        self._draw()
        self.root.after(33, self._tick)
        self.root.lift()
        try:
            self.root.attributes("-topmost", True)
            self.root.after(400, lambda: self.root.attributes("-topmost", False))
        except tk.TclError:
            pass
        self.root.focus_force()

    def _load_model(self) -> None:
        if self.model_kind == "box":
            self.vertices, self.faces, self.edges = build_convex_box()
            self.face_names = face_names_box()
        else:
            self.vertices, self.faces, self.edges = build_convex_house()
            self.face_names = face_names_pyramid()

    def _bind(self) -> None:
        self.root.bind("<Key>", self._on_key)
        self.view.bind("<ButtonPress-1>", self._on_press)
        self.view.bind("<B1-Motion>", self._on_drag)
        self.view.bind("<ButtonRelease-1>", self._on_release)
        self.view.bind("<MouseWheel>", self._on_wheel)
        self.frame.bind("<Configure>", self._on_configure)
        self.view.focus_set()

    def _sync_size(self) -> None:
        w = self.frame.winfo_width() - 8
        h = self.frame.winfo_height() - 8
        if w > 40 and h > 40:
            self.width, self.height = w, h

    def _on_configure(self, _event: tk.Event) -> None:
        prev = (self.soft.width, self.soft.height)
        self._sync_size()
        if (self.width, self.height) != prev:
            self.soft.resize(self.width, self.height)
            self.view.configure(image=self.soft.flush())
            self.view.image = self.soft.image

    def model_matrix(self) -> Mat4:
        m = identity()
        m = mat_mul(scale(self.sx, self.sy, self.sz), m)
        m = mat_mul(rotate_x(self.rx), m)
        m = mat_mul(rotate_y(self.ry), m)
        m = mat_mul(rotate_z(self.rz), m)
        m = mat_mul(translate(self.tx, self.ty, self.tz), m)
        return m

    def animation_matrix(self) -> Mat4:
        if not self.animating:
            return identity()
        return rotate_z(self.anim_t * 0.7)

    def eye_world(self) -> Vec3:
        """
        Положение камеры в мировой СК.
        В ЛР1 камера смотрит вдоль +Y, «глаз» примерно в (0, -focal, 0).
        """
        return (0.0, -self.focal, 0.0)

    def project(self, p: Vec3) -> Tuple[float, float]:
        x, y, z = p
        if self.perspective:
            return perspective_project(
                (x, y, z),
                focal=self.focal,
                screen_w=self.width,
                screen_h=self.height,
            )
        iso_x = x - 0.45 * y
        iso_y = z + 0.35 * y
        return self.width * 0.5 + iso_x, self.height * 0.5 - iso_y

    def _draw(self) -> None:
        if self.soft.width != self.width or self.soft.height != self.height:
            self.soft.resize(self.width, self.height)

        self.soft.clear()
        world = mat_mul(self.animation_matrix(), self.model_matrix())
        pts = transform_points(world, self.vertices)

        # --- Алгоритм Робертса ---
        face_front, edge_visible, face_info = roberts_classify(
            pts, self.faces, self.edges, self.eye_world()
        )

        # нормали (демонстрация)
        if self.show_normals:
            for fi, face in enumerate(self.faces):
                c = face_center(pts, face)
                n = face_info[fi]["normal"]
                tip = (c[0] + n[0] * 40, c[1] + n[1] * 40, c[2] + n[2] * 40)
                color = "#16a34a" if face_front[fi] else "#64748b"
                self.soft.line(*self.project(c), *self.project(tip), color, thick=False)

        # сначала скрытые (пунктир), потом видимые
        projected = [self.project(p) for p in pts]
        for ei, ((a, b), vis) in enumerate(zip(self.edges, edge_visible)):
            x1, y1 = projected[a]
            x2, y2 = projected[b]
            if vis:
                self.soft.line(x1, y1, x2, y2, self.VISIBLE, dashed=False, thick=True)
            elif self.show_hidden:
                self.soft.line(x1, y1, x2, y2, self.HIDDEN, dashed=True, thick=False)

        img = self.soft.flush()
        self.view.configure(image=img)
        self.view.image = img

        n_vis = sum(1 for v in edge_visible if v)
        n_hid = len(edge_visible) - n_vis
        n_front = sum(1 for f in face_front if f)
        mode = "perspective" if self.perspective else "orthogonal"
        self.frame_id += 1
        self.status.configure(
            text=(
                f"frame {self.frame_id} | Roberts | {self.model_kind} | {mode} | "
                f"faces front={n_front}/{len(self.faces)} | "
                f"edges vis={n_vis} hid={n_hid} | "
                f"hidden={'on' if self.show_hidden else 'off'} | anim={'on' if self.animating else 'off'}"
            )
        )
        self._update_info_panel(face_info, edge_visible)

    def _update_info_panel(self, face_info: List[dict], edge_visible: List[bool]) -> None:
        lines = [
            "АЛГОРИТМ РОБЕРТСА",
            "=================",
            "Выпуклое тело →",
            "ребро скрыто, если ОБЕ",
            "смежные грани тыльные.",
            "",
            f"Модель: {self.model_kind}",
            f"Граней: {len(self.faces)}",
            f"Рёбер:  {len(self.edges)}",
            "",
            "ГРАНИ (n·to_eye):",
        ]
        for info in face_info:
            i = info["index"]
            name = self.face_names[i] if i < len(self.face_names) else f"#{i}"
            mark = "FRONT" if info["front"] else "back "
            nd = info["n_dot_view"]
            lines.append(f" {i}:{name[:8]:8s} {mark} {nd:+.2f}")

        lines.append("")
        lines.append("РЁБРА:")
        for ei, ((a, b), vis) in enumerate(zip(self.edges, edge_visible)):
            mark = "VIS" if vis else "hid"
            lines.append(f" {ei:2d}: ({a},{b})  {mark}")

        lines.append("")
        lines.append("H — скрытые рёбра")
        lines.append("N — нормали граней")
        lines.append("B — параллелепипед")
        lines.append("P — пирамида (5 гран.)")

        text = "\n".join(lines)
        self.info.configure(state=tk.NORMAL)
        self.info.delete("1.0", tk.END)
        self.info.insert(tk.END, text)
        self.info.configure(state=tk.DISABLED)

    def _tick(self) -> None:
        try:
            if not self.view.winfo_exists():
                return
            if self.animating:
                self.anim_t += 0.04
            self._draw()
        except tk.TclError:
            return
        except Exception as exc:
            self.status.configure(text=f"Ошибка: {exc}")
            import traceback

            traceback.print_exc()
            return
        self.root.after(33, self._tick)

    def _scale_by(self, factor: float) -> None:
        self.sx = max(0.15, min(5.0, self.sx * factor))
        self.sy = self.sz = self.sx

    def _on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        step = 8.0
        rot = math.radians(5.0)

        if key == "escape":
            self.root.destroy()
            return
        if key == "space":
            self.animating = not self.animating
            return
        if key == "h":
            self.show_hidden = not self.show_hidden
            return
        if key == "n":
            self.show_normals = not self.show_normals
            return
        if key == "b":
            self.model_kind = "box"
            self._load_model()
            return
        if key == "p":
            self.model_kind = "pyramid"
            self._load_model()
            return
        if key == "1":
            self.perspective = False
            return
        if key == "2":
            self.perspective = True
            return
        if key == "0":
            self.tx = self.ty = self.tz = 0.0
            self.rx = math.radians(-22.0)
            self.ry = math.radians(35.0)
            self.rz = 0.0
            self.sx = self.sy = self.sz = 1.0
            self.anim_t = 0.0
            return

        if key in ("left", "a"):
            self.tx -= step
        elif key in ("right", "d"):
            self.tx += step
        elif key in ("up", "w"):
            self.tz += step
        elif key in ("down", "s"):
            self.tz -= step
        elif key == "q":
            self.ty -= step
        elif key == "e":
            self.ty += step
        elif key == "r":
            self.rx += rot
        elif key == "f":
            self.rx -= rot
        elif key == "t":
            self.ry += rot
        elif key == "g":
            self.ry -= rot
        elif key == "y":
            self.rz += rot
        elif key in ("plus", "equal", "kp_add"):
            self._scale_by(1.08)
        elif key in ("minus", "underscore", "kp_subtract"):
            self._scale_by(1 / 1.08)

    def _on_press(self, event: tk.Event) -> None:
        self._drag = (event.x, event.y)
        self.view.focus_set()

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        dx = event.x - self._drag[0]
        dy = event.y - self._drag[1]
        self._drag = (event.x, event.y)
        self.ry += dx * 0.01
        self.rx += dy * 0.01

    def _on_release(self, _event: tk.Event) -> None:
        self._drag = None

    def _on_wheel(self, event: tk.Event) -> None:
        delta = event.delta
        if abs(delta) >= 120:
            delta /= 120
        self._scale_by(1.08 if delta > 0 else 1 / 1.08)


def main() -> None:
    root = tk.Tk()
    RobertsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
