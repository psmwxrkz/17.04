import os
import time
import tkinter as tk
import ctypes

from PIL import Image, ImageTk

from config import APP_TITLE
from ui.main_window import SistemaCadastrosApp, configurar_icone_janela, resource_path


ERROR_ALREADY_EXISTS = 183
MUTEX_NOME = "Global\\ControleDiversosAppMutex"
_mutex_handle = None


def criar_mutex_unico():
    global _mutex_handle

    try:
        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NOME)
        ultimo_erro = ctypes.windll.kernel32.GetLastError()

        if ultimo_erro == ERROR_ALREADY_EXISTS:
            return False

        return True
    except Exception as e:
        print("Erro ao criar mutex de instância única:", e)
        return True

def ativar_janela_existente():
    try:
        user32 = ctypes.windll.user32

        hwnd = user32.FindWindowW(None, APP_TITLE)

        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
    except Exception as e:
        print("Erro ao ativar janela existente:", e)


class SplashScreen:
    def __init__(self, root):
        self.root = root
        self.bg = "#0b1220"
        self.fg_titulo = "#f8fafc"
        self.fg_subtitulo = "#94a3b8"

        self.top = tk.Toplevel(root)
        self.top.overrideredirect(True)
        self.top.configure(bg=self.bg)
        self.top.attributes("-topmost", True)
        self.top.attributes("-alpha", 0)

        largura = 620
        altura = 360

        screen_w = self.top.winfo_screenwidth()
        screen_h = self.top.winfo_screenheight()
        x = (screen_w // 2) - (largura // 2)
        y = (screen_h // 2) - (altura // 2)

        self.top.geometry(f"{largura}x{altura}+{x}+{y}")

        self.container = tk.Frame(
            self.top,
            bg=self.bg,
            highlightthickness=1,
            highlightbackground="#1f2937",
            bd=0,
        )
        self.container.place(relx=0.5, rely=0.5, anchor="center", width=620, height=360)

        self.logo_label = tk.Label(self.container, bg=self.bg, bd=0)
        self.logo_label.place(relx=0.5, y=190, anchor="center")

        self.titulo = tk.Label(
            self.container,
            text="BALGATE",
            bg=self.bg,
            fg=self.fg_titulo,
            font=("Segoe UI", 24, "bold"),
        )
        self.titulo.place(relx=0.5, y=255, anchor="center")

        self.subtitulo = tk.Label(
            self.container,
            text="Iniciando sistema de cadastros...",
            bg=self.bg,
            fg=self.fg_subtitulo,
            font=("Segoe UI", 10),
        )
        self.subtitulo.place(relx=0.5, y=290, anchor="center")

        self.logo_original = None
        self.logo_tk = None
        self._carregar_logo()

        self.top.update_idletasks()

    def fade_in(self, duracao=400, passos=25):
        intervalo = duracao / passos / 1000

        for i in range(passos + 1):
            alpha = i / passos
            try:
                self.top.attributes("-alpha", alpha)
            except Exception:
                pass

            self.top.update_idletasks()
            self.top.update()
            time.sleep(intervalo)

    def fade_out(self, duracao=220, passos=18):
        intervalo = duracao / passos / 1000

        for i in range(passos + 1):
            alpha = 1 - (i / passos)
            try:
                self.top.attributes("-alpha", alpha)
            except Exception:
                pass

            self.top.update_idletasks()
            self.top.update()
            time.sleep(intervalo)

    def _carregar_logo(self):
        caminhos = [
            resource_path(os.path.join("assets", "teg_teag.png")),
            resource_path(os.path.join("assets", "app.png")),
        ]

        for caminho in caminhos:
            if os.path.exists(caminho):
                try:
                    self.logo_original = Image.open(caminho).convert("RGBA")
                    return
                except Exception as e:
                    print("Erro ao carregar imagem da splash:", e)

        self.logo_original = None

    def animar_intro(self):
        if self.logo_original is None:
            self.top.update_idletasks()
            self.top.update()
            time.sleep(0.6)
            return

        frames = 55
        escala_inicial = 0.45
        escala_final = 1.0
        y_inicial = 205
        y_final = 160
        largura_base = 260

        for i in range(frames):
            progresso = i / (frames - 1)
            eased = 1 - (1 - progresso) ** 3

            escala = escala_inicial + ((escala_final - escala_inicial) * eased)
            y_atual = y_inicial - ((y_inicial - y_final) * eased)

            largura = max(1, int(largura_base * escala))
            proporcao = self.logo_original.height / self.logo_original.width
            altura = max(1, int(largura * proporcao))

            frame_img = self.logo_original.resize((largura, altura), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(frame_img)

            self.logo_label.configure(image=self.logo_tk)
            self.logo_label.place(relx=0.5, y=y_atual, anchor="center")

            self.top.update_idletasks()
            self.top.update()
            time.sleep(0.018)

        time.sleep(0.30)
        self.top.update_idletasks()
        self.top.update()

    def fechar(self):
        try:
            self.top.destroy()
        except Exception:
            pass


def fade_in_root(root, duracao=180, passos=12):
    intervalo = duracao / passos / 1000

    for i in range(passos + 1):
        alpha = i / passos
        try:
            root.attributes("-alpha", alpha)
        except Exception:
            pass

        root.update_idletasks()
        root.update()
        time.sleep(intervalo)

def main():
    if not criar_mutex_unico():
        ativar_janela_existente()
        return

    root = tk.Tk()
    root.configure(bg="#0b1220")
    root.withdraw()

    try:
        root.attributes("-alpha", 0)
    except Exception:
        pass

    configurar_icone_janela(root)
    root.update_idletasks()

    splash = SplashScreen(root)

    try:
        splash.fade_in()

        app = SistemaCadastrosApp(root, iniciar_sync_automatico=False)

        splash.animar_intro()

        root.update_idletasks()
        root.deiconify()
        root.lift()

        try:
            root.state("zoomed")
        except Exception:
            pass

        root.update_idletasks()
        root.update()

        splash.fade_out()
        splash.fechar()

        fade_in_root(root)

        app.iniciar_inicializacao_assincrona()

    except Exception:
        splash.fechar()
        raise

    root.mainloop()
    
if __name__ == "__main__":
    main()