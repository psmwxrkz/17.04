import tkinter as tk
from tkinter import ttk


import tkinter as tk
from tkinter import ttk


def aplicar_estilos(root=None):
    style = ttk.Style(root)

    # Usa um tema compatível com customização
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # ===============================
    # Scrollbar vertical escura
    # ===============================
    style.layout(
        "Dark.Vertical.TScrollbar",
        [
            (
                "Vertical.Scrollbar.trough",
                {
                    "sticky": "ns",
                    "children": [
                        (
                            "Vertical.Scrollbar.thumb",
                            {"expand": "1", "sticky": "nswe"}
                        )
                    ],
                },
            )
        ],
    )

    style.configure(
        "Dark.Vertical.TScrollbar",
        troughcolor="#020617",
        background="#0f172a",
        darkcolor="#0f172a",
        lightcolor="#0f172a",
        bordercolor="#020617",
        arrowcolor="#93c5fd",
        relief="flat",
        borderwidth=0,
        arrowsize=12,
        gripcount=0,
    )

    style.map(
        "Dark.Vertical.TScrollbar",
        background=[
            ("active", "#1e293b"),
            ("pressed", "#334155"),
        ],
        darkcolor=[
            ("active", "#1e293b"),
            ("pressed", "#334155"),
        ],
        lightcolor=[
            ("active", "#1e293b"),
            ("pressed", "#334155"),
        ],
    )

    # ===============================
    # Scrollbar horizontal escura
    # ===============================
    style.layout(
        "Dark.Horizontal.TScrollbar",
        [
            (
                "Horizontal.Scrollbar.trough",
                {
                    "sticky": "we",
                    "children": [
                        (
                            "Horizontal.Scrollbar.thumb",
                            {"expand": "1", "sticky": "nswe"}
                        )
                    ],
                },
            )
        ],
    )

    style.configure(
        "Dark.Horizontal.TScrollbar",
        troughcolor="#020617",
        background="#0f172a",
        darkcolor="#0f172a",
        lightcolor="#0f172a",
        bordercolor="#020617",
        arrowcolor="#93c5fd",
        relief="flat",
        borderwidth=0,
        arrowsize=12,
        gripcount=0,
    )

    style.map(
        "Dark.Horizontal.TScrollbar",
        background=[
            ("active", "#1e293b"),
            ("pressed", "#334155"),
        ],
        darkcolor=[
            ("active", "#1e293b"),
            ("pressed", "#334155"),
        ],
        lightcolor=[
            ("active", "#1e293b"),
            ("pressed", "#334155"),
        ],
    )

    # ===============================
    # Frames e Labels
    # ===============================
    style.configure("TFrame", background="#0b1220")

    style.configure(
        "TLabel",
        background="#0b1220",
        foreground="#f8fafc",
        font=("Segoe UI", 10),
    )

    style.configure(
        "Titulo.TLabel",
        background="#0b1220",
        foreground="#f8fafc",
        font=("Segoe UI", 21, "bold"),
    )

    style.configure(
        "Subtitulo.TLabel",
        background="#0b1220",
        foreground="#94a3b8",
        font=("Segoe UI", 10),
    )

    style.configure(
        "Secao.TLabel",
        background="#111827",
        foreground="#f8fafc",
        font=("Segoe UI", 12, "bold"),
        padding=6,
    )

    # ===============================
    # Botões
    # ===============================
    style.configure(
        "TButton",
        font=("Segoe UI", 10, "bold"),
        padding=8,
        relief="flat",
        borderwidth=0,
    )

    style.map(
        "TButton",
        background=[
            ("active", "#1f2937"),
            ("pressed", "#111827"),
        ],
        foreground=[("!disabled", "#f8fafc")],
    )

    style.configure(
        "Primary.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=9,
    )

    style.map(
        "Primary.TButton",
        background=[
            ("!disabled", "#3b82f6"),
            ("active", "#2563eb"),
            ("pressed", "#1d4ed8"),
        ],
        foreground=[("!disabled", "white")],
    )

    style.configure(
        "Success.TButton",
        font=("Segoe UI", 10, "bold"),
        padding=9,
    )

    style.map(
        "Success.TButton",
        background=[
            ("!disabled", "#16a34a"),
            ("active", "#15803d"),
        ],
        foreground=[("!disabled", "white")],
    )

    # ===============================
    # Separator
    # ===============================
    style.configure(
        "TSeparator",
        background="#1f2937",
    )
    

# ===============================
# Exemplo de uso
# ===============================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Tema Escuro ttk")
    root.geometry("600x400")
    root.configure(bg="#0b1220")

    aplicar_estilos()

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Título Principal", style="Titulo.TLabel").pack(anchor="w")
    ttk.Label(frame, text="Subtítulo de exemplo", style="Subtitulo.TLabel").pack(anchor="w", pady=(0, 20))

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

    ttk.Label(frame, text="Seção", style="Secao.TLabel").pack(fill="x", pady=(10, 10))

    ttk.Button(frame, text="Botão padrão").pack(pady=5)
    ttk.Button(frame, text="Botão primário", style="Primary.TButton").pack(pady=5)
    ttk.Button(frame, text="Botão sucesso", style="Success.TButton").pack(pady=5)

    root.mainloop()
