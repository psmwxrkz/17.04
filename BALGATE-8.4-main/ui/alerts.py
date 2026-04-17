import tkinter as tk


# ------------------------------------------------------------------
# ALERTA VISUAL (BARRA SUPERIOR)
# ------------------------------------------------------------------
def ativar_alerta_visual(label_alerta, app, mensagem="Novo alerta"):
    app.alerta_piscando = True
    app.mensagem_alerta_atual = mensagem

    if hasattr(app, "alerta_after_id") and app.alerta_after_id:
        try:
            label_alerta.after_cancel(app.alerta_after_id)
        except Exception:
            pass
        app.alerta_after_id = None

    def piscar():
        if not getattr(app, "alerta_piscando", False):
            app.alerta_after_id = None
            return

        try:
            total_pendentes = len(getattr(app.service, "cadastros_pendentes", []))
        except Exception:
            total_pendentes = 0

        if total_pendentes <= 0:
            parar_alerta(label_alerta, app)
            return

        cor_atual = label_alerta.cget("bg")
        nova_cor = "#ef4444" if cor_atual != "#ef4444" else "#f59e0b"

        try:
            label_alerta.config(
                text=getattr(app, "mensagem_alerta_atual", mensagem),
                bg=nova_cor,
                fg="white",
            )
            app.alerta_after_id = label_alerta.after(500, piscar)
        except Exception:
            app.alerta_after_id = None

    piscar()


def parar_alerta(label_alerta, app):
    app.alerta_piscando = False

    if hasattr(app, "alerta_after_id") and app.alerta_after_id:
        try:
            label_alerta.after_cancel(app.alerta_after_id)
        except Exception:
            pass
        app.alerta_after_id = None

    total = len(getattr(app.service, "cadastros_pendentes", []))

    try:
        label_alerta.config(
            text="Sem novos alertas" if total == 0 else f"{total} pendência(s) no sistema",
            bg="#22c55e" if total == 0 else "#f59e0b",
            fg="white",
        )
    except Exception:
        pass


# ------------------------------------------------------------------
# ALERTA POPUP (CANTO DA TELA)
# ------------------------------------------------------------------
def mostrar_alerta_canto(root, mensagem, on_click=None):
    alerta = tk.Toplevel(root)
    alerta.overrideredirect(True)
    alerta.attributes("-topmost", True)
    alerta.configure(bg="#000000")

    largura = 360
    altura = 120

    root.update_idletasks()
    x = root.winfo_screenwidth() - largura - 18
    y = root.winfo_screenheight() - altura - 70

    alerta.geometry(f"{largura}x{altura}+{x}+{y}")

    try:
        alerta.withdraw()
        alerta.update_idletasks()
        alerta.deiconify()
        alerta.lift()
    except Exception:
        pass

    # container
    sombra = tk.Frame(
        alerta,
        bg="#020617",
        highlightthickness=1,
        highlightbackground="#1e293b",
        bd=0,
    )
    sombra.pack(fill="both", expand=True)

    # faixa lateral
    faixa = tk.Frame(sombra, bg="#3b82f6", width=6)
    faixa.pack(side="left", fill="y")

    # corpo
    corpo = tk.Frame(
        sombra,
        bg="#0f172a",
        padx=12,
        pady=10,
    )
    corpo.pack(side="left", fill="both", expand=True)

    # topo
    topo = tk.Frame(corpo, bg="#0f172a")
    topo.pack(fill="x")

    bloco_titulo = tk.Frame(topo, bg="#0f172a")
    bloco_titulo.pack(side="left", fill="x", expand=True)

    icone = tk.Label(
        bloco_titulo,
        text="🔔",
        bg="#0f172a",
        fg="white",
        font=("Segoe UI Emoji", 12),
        cursor="hand2" if on_click else "arrow",
    )
    icone.pack(side="left")

    titulo = tk.Label(
        bloco_titulo,
        text="Novo cadastro pendente",
        bg="#0f172a",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        anchor="w",
        cursor="hand2" if on_click else "arrow",
    )
    titulo.pack(side="left", padx=(8, 0))

    # ---------------------------------------------------------------
    # BOTÃO X (FECHAR)
    # ---------------------------------------------------------------
    def fechar_popup(event=None):
        try:
            if alerta.winfo_exists():
                alerta.destroy()
        except Exception:
            pass

    btn_fechar = tk.Label(
        topo,
        text="✕",
        bg="#0f172a",
        fg="#cbd5e1",
        font=("Segoe UI", 10, "bold"),
        padx=6,
        cursor="hand2",
    )
    btn_fechar.pack(side="right")

    btn_fechar.bind("<Button-1>", fechar_popup)
    btn_fechar.bind("<Enter>", lambda e: btn_fechar.config(fg="white"))
    btn_fechar.bind("<Leave>", lambda e: btn_fechar.config(fg="#cbd5e1"))

    # conteúdo
    subtitulo = tk.Label(
        corpo,
        text=mensagem,
        bg="#0f172a",
        fg="#cbd5e1",
        font=("Segoe UI", 9),
        justify="left",
        anchor="w",
        wraplength=300,
        cursor="hand2" if on_click else "arrow",
    )
    subtitulo.pack(fill="x", pady=(8, 0))

    dica = tk.Label(
        corpo,
        text="Clique para abrir o sistema",
        bg="#0f172a",
        fg="#60a5fa",
        font=("Segoe UI", 8, "bold"),
        anchor="w",
        cursor="hand2" if on_click else "arrow",
    )
    dica.pack(fill="x", pady=(8, 0))

    # ---------------------------------------------------------------
    # CLICK (ABRIR SISTEMA)
    # ---------------------------------------------------------------
    def ao_clicar(event=None):
        # se clicou no X, não dispara ação
        if event and event.widget == btn_fechar:
            return

        try:
            if on_click:
                on_click()
        finally:
            fechar_popup()

    if on_click:
        for widget in (sombra, faixa, corpo, bloco_titulo, icone, titulo, subtitulo, dica):
            widget.bind("<Button-1>", ao_clicar)

    # ---------------------------------------------------------------
    # ANIMAÇÃO DE ENTRADA
    # ---------------------------------------------------------------
    destino_y = y
    y_inicial = y + 18
    alerta.geometry(f"{largura}x{altura}+{x}+{y_inicial}")

    def animar(yy):
        try:
            if not alerta.winfo_exists():
                return
        except Exception:
            return

        if yy <= destino_y:
            try:
                alerta.geometry(f"{largura}x{altura}+{x}+{destino_y}")
            except Exception:
                pass
            return

        try:
            alerta.geometry(f"{largura}x{altura}+{x}+{yy}")
            alerta.after(12, lambda: animar(yy - 3))
        except Exception:
            pass

    animar(y_inicial)

    # ---------------------------------------------------------------
    # FECHAMENTO AUTOMÁTICO
    # ---------------------------------------------------------------
    alerta.after(6000, fechar_popup)