"""
Projekt: Õppekaardid (CustomTkinter pastelne versioon progressbariga)
Autorid: Annabel Jürjenson, Minna Marie Kask
Kirjeldus:
Kasutaja saab valida õppimiseks valmis komplekti õppekaarte või ise komplekt luua.
Valmis komplektina on kasutamiseks kursuse "Kõrgem matemaatika I (alused)" õppekaardid.
"""

import sqlite3
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk


# -----------------------------
#   VÄRVIPALETT – PASTELNE
# -----------------------------

PASTEL_TOP = "#ffe7f3"       # ülemine gradient – hästi õrn roosa
PASTEL_BOTTOM = "#e3f6ff"    # alumine gradient – hästi õrn sinine
ACCENT_MAIN = "#f6aecb"      # põhi-aktsent (nupud, pealkiri)
ACCENT_MAIN_DARK = "#ec8fb4" # tumedam hover
ACCENT_SOFT_BLUE = "#b7d8ff" # lisa-aktsent
TEXT_DARK = "#4b4b5a"        # tumedam tekst
TEXT_SOFT = "#7a7a8a"        # pehmem tekst


# -----------------------------
#   ANDMEBAASIFUNKTSIOONID
# -----------------------------

def loo_tabelid(uhendus):
    kursor = uhendus.cursor()
    
    kursor.execute('''
        CREATE TABLE IF NOT EXISTS flashcard_sets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL
        )
    ''')

    kursor.execute('''
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            definition TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES flashcard_sets(id)
        )
    ''')

def lisa_set(uhendus, nimi):
    kursor = uhendus.cursor()
    
    kursor.execute('''
        INSERT INTO flashcard_sets (name)
        VALUES (?)
    ''', (nimi,))
    
    seti_id = kursor.lastrowid
    uhendus.commit()
    
    return seti_id

def lisa_kaart(uhendus, seti_id, sona, definitsioon):
    kursor = uhendus.cursor()

    kursor.execute('''
        INSERT INTO flashcards (set_id, word, definition)
        VALUES (?, ?, ?)
    ''', (seti_id, sona, definitsioon))

    kaardi_id = kursor.lastrowid
    uhendus.commit()

    return kaardi_id

def saa_setid(uhendus):
    kursor = uhendus.cursor()

    kursor.execute('''
        SELECT id, name FROM flashcard_sets
    ''')

    read = kursor.fetchall()
    setid = {rida[1]: rida[0] for rida in read }

    return setid

def saa_kaardid(uhendus, seti_id):
    kursor = uhendus.cursor()

    kursor.execute('''  
        SELECT word, definition FROM flashcards
        WHERE set_id = ?
    ''', (seti_id,))

    read = kursor.fetchall()
    kaardid = [(rida[0], rida[1]) for rida in read]
    return kaardid

def kustuta_set(uhendus, seti_id):
    global aktiivsed_kaardid, kaardi_indeks

    kursor = uhendus.cursor()

    kursor.execute('''
        DELETE FROM flashcard_sets
        WHERE id = ?
    ''', (seti_id,))

    uhendus.commit()
    seti_valik_var.set('')
    clear_kaardid()
    taida_seti_valik()

    aktiivsed_kaardid = []
    kaardi_indeks = 0


# -----------------------------
#   LOOGIKA – SETID JA KAARDID
# -----------------------------

def loo_set():
    seti_nimi = seti_nimi_var.get().strip()
    if seti_nimi:
        olemas = saa_setid(uhendus)
        if seti_nimi not in olemas:
            lisa_set(uhendus, seti_nimi)
        taida_seti_valik()
        seti_nimi_var.set('')
        sona_var.set('')
        definitsioon_var.set('')

def lisa_sona():
    seti_nimi = seti_nimi_var.get().strip()
    sona = sona_var.get().strip()
    definitsioon = definitsioon_var.get().strip()

    if not (seti_nimi and sona and definitsioon):
        messagebox.showwarning("Puuduvad andmed", "Palun täida kõik väljad.")
        return

    setid = saa_setid(uhendus)
    if seti_nimi not in setid:
        seti_id = lisa_set(uhendus, seti_nimi)
    else:
        seti_id = setid[seti_nimi]
        
    lisa_kaart(uhendus, seti_id, sona, definitsioon)

    sona_var.set('')
    definitsioon_var.set('')

    taida_seti_valik()

def taida_seti_valik():
    setid = tuple(saa_setid(uhendus).keys())
    seti_valik.configure(values=setid)

def kustuta_valitud_set():
    seti_nimi = seti_valik_var.get().strip()

    if seti_nimi:
        tulemus = messagebox.askyesno(
            'Kinnitus', f'Kas oled kindel, et soovid seti "{seti_nimi}" kustutada?'
        )

        if tulemus:
            seti_id = saa_setid(uhendus)[seti_nimi]
            kustuta_set(uhendus, seti_id)
            taida_seti_valik()
            clear_kaardid()

def vali_set():
    global aktiivsed_kaardid, kaardi_indeks

    seti_nimi = seti_valik_var.get().strip()

    if seti_nimi:
        seti_id = saa_setid(uhendus)[seti_nimi]
        kaardid = saa_kaardid(uhendus, seti_id)

        if kaardid:
            kuva_kaardid(kaardid)
        else:
            sona_silt.configure(text='Selles setis pole flashcarde')
            definitsiooni_silt.configure(text='')
            aktiivsed_kaardid = []
            kaardi_indeks = 0
            uuenda_progress()
    else:
        aktiivsed_kaardid = []
        kaardi_indeks = 0
        clear_kaardid()


def kuva_kaardid(kaardid):
    global kaardi_indeks, aktiivsed_kaardid

    kaardi_indeks = 0
    aktiivsed_kaardid = kaardid

    if not kaardid:
        clear_kaardid()
    else:
        naita_kaart()


def clear_kaardid():
    sona_silt.configure(text='')
    definitsiooni_silt.configure(text='')
    uuenda_progress()


def naita_kaart():
    global kaardi_indeks, aktiivsed_kaardid

    if aktiivsed_kaardid and 0 <= kaardi_indeks < len(aktiivsed_kaardid):
        sona, _ = aktiivsed_kaardid[kaardi_indeks]
        sona_silt.configure(text=sona)
        definitsiooni_silt.configure(text='')
    else:
        sona_silt.configure(text='')
        definitsiooni_silt.configure(text='')

    uuenda_progress()


def pööra_kaart():
    global kaardi_indeks, aktiivsed_kaardid

    if aktiivsed_kaardid and 0 <= kaardi_indeks < len(aktiivsed_kaardid):
        _, definitsioon = aktiivsed_kaardid[kaardi_indeks]
        definitsiooni_silt.configure(text=definitsioon)


def järgmine_kaart():
    global kaardi_indeks, aktiivsed_kaardid

    if aktiivsed_kaardid:
        kaardi_indeks = min(kaardi_indeks + 1, len(aktiivsed_kaardid) - 1)
        naita_kaart()


def eelmine_kaart():
    global kaardi_indeks, aktiivsed_kaardid

    if aktiivsed_kaardid:
        kaardi_indeks = max(kaardi_indeks - 1, 0)
        naita_kaart()


# -----------------------------
#   PROGRESS BAR FUNKTSIOON
# -----------------------------

def uuenda_progress():
    """Uuendab progress bari ja tekstilist näitajat (nt 3 / 10)."""
    global aktiivsed_kaardid, kaardi_indeks

    if aktiivsed_kaardid:
        total = len(aktiivsed_kaardid)
        current = kaardi_indeks + 1  # indeks 0 => 1. kaart
        fraction = current / total
        progress_bar.set(fraction)
        progress_label.configure(text=f"{current} / {total}")
    else:
        progress_bar.set(0)
        progress_label.configure(text="0 / 0")


# -----------------------------
#   GRAAFIKA – PASTELNE GRADIENT
# -----------------------------

def joonista_gradient(canvas, värv1=PASTEL_TOP, värv2=PASTEL_BOTTOM):
    """Lihtne vertikaalne gradient Canvasel."""
    canvas.update()
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    if h <= 0:
        h = 600

    canvas.delete("gradient")
    r1, g1, b1 = canvas.winfo_rgb(värv1)
    r2, g2, b2 = canvas.winfo_rgb(värv2)

    r1 //= 256; g1 //= 256; b1 //= 256
    r2 //= 256; g2 //= 256; b2 //= 256

    steps = h
    for i in range(steps):
        r = int(r1 + (r2 - r1) * i / steps)
        g = int(g1 + (g2 - g1) * i / steps)
        b = int(b1 + (b2 - b1) * i / steps)
        värv = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(0, i, w, i, tags=("gradient",), fill=värv)

    canvas.lower("gradient")


# -----------------------------
#   MAIN
# -----------------------------

if __name__ == '__main__':
    uhendus = sqlite3.connect('flashcards.db')
    loo_tabelid(uhendus)

    # CustomTkinter seaded
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")  # baas, aga me override'ime värvid nagunii

    root = ctk.CTk()
    root.title("Õppekaardid – pastelne")
    root.geometry("900x650")
    root.minsize(800, 600)

    # Taustaks Canvas + pastelne gradient
    gradient_canvas = tk.Canvas(root, highlightthickness=0, bd=0)
    gradient_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

    def uuenda_gradient(event=None):
        joonista_gradient(gradient_canvas, PASTEL_TOP, PASTEL_BOTTOM)

    root.bind("<Configure>", uuenda_gradient)

    # Fondid  👉 SIIN MUUDAD TEKSTI SUURUSI
    põhifont = ("Segoe UI", 18)          # tavaline tekst
    pealkiri_font = ("Segoe UI Semibold", 30)  # pealkiri
    suur_font = ("Segoe UI Semibold", 22)      # nupud / ala-pealkirjad
    tab_font = ("Segoe UI Semibold", 16)  # Ülariba tabide font


    # Peamine "kaart" keskel – valge, õrn varjund pastel taustal
    main_frame = ctk.CTkFrame(
        root,
        corner_radius=28,
        fg_color="white"
    )
    main_frame.place(relx=0.5, rely=0.5, relwidth=0.9, relheight=0.9, anchor="center")

    # Pealkiri
    title_label = ctk.CTkLabel(
        main_frame,
        text="Õppekaardid",
        font=pealkiri_font,
        text_color=ACCENT_MAIN
    )
    title_label.pack(pady=(10, 4))

    subtitle_label = ctk.CTkLabel(
        main_frame,
        text="Loo oma setid või kasuta valmis komplekte",
        font=põhifont,
        text_color=TEXT_SOFT
    )
    subtitle_label.pack(pady=(0, 12))

    # Tabview
    tabview = ctk.CTkTabview(main_frame,
                             segmented_button_selected_color=ACCENT_MAIN,
                             segmented_button_selected_hover_color=ACCENT_MAIN_DARK)
    tabview.pack(fill="both", expand=True, padx=20, pady=20)

    tab_looset = tabview.add("Loo set")
    tab_valiset = tabview.add("Vali set")
    tab_õpi = tabview.add("Õpime")
    tab_mata = tabview.add("Kõrge matemaatika alused")
    tabview._segmented_button.configure(font=tab_font)


    # ---------------- LOO SET TAB ----------------

    seti_nimi_var = ctk.StringVar()
    sona_var = ctk.StringVar()
    definitsioon_var = ctk.StringVar()

    looset_frame = ctk.CTkFrame(tab_looset, fg_color="transparent")
    looset_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(
        looset_frame,
        text="Seti nimi:",
        font=suur_font,
        text_color=TEXT_DARK
    ).pack(anchor="w", pady=(0, 5))

    ctk.CTkEntry(
        looset_frame,
        textvariable=seti_nimi_var,
        font=põhifont,
        fg_color="#ffffff",
        border_color=ACCENT_MAIN,
        border_width=1,
        corner_radius=12
    ).pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(
        looset_frame,
        text="Küsimus:",
        font=suur_font,
        text_color=TEXT_DARK
    ).pack(anchor="w", pady=(5, 5))

    ctk.CTkEntry(
        looset_frame,
        textvariable=sona_var,
        font=põhifont,
        fg_color="#ffffff",
        border_color=ACCENT_MAIN,
        border_width=1,
        corner_radius=12
    ).pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(
        looset_frame,
        text="Vastus:",
        font=suur_font,
        text_color=TEXT_DARK
    ).pack(anchor="w", pady=(5, 5))

    ctk.CTkEntry(
        looset_frame,
        textvariable=definitsioon_var,
        font=põhifont,
        fg_color="#ffffff",
        border_color=ACCENT_MAIN,
        border_width=1,
        corner_radius=12
    ).pack(fill="x", pady=(0, 15))

    nuppude_frame_looset = ctk.CTkFrame(looset_frame, fg_color="transparent")
    nuppude_frame_looset.pack(pady=10)

    ctk.CTkButton(
        nuppude_frame_looset,
        text="Lisa küsimus",
        command=lisa_sona,
        font=suur_font,
        fg_color=ACCENT_MAIN,
        hover_color=ACCENT_MAIN_DARK,
        corner_radius=20
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        nuppude_frame_looset,
        text="Salvesta set",
        command=loo_set,
        font=suur_font,
        fg_color="#ffffff",
        text_color=ACCENT_MAIN,
        hover_color="#fdf1f7",
        border_width=2,
        border_color=ACCENT_MAIN,
        corner_radius=20
    ).pack(side="left", padx=10)

    # ---------------- VALI SET TAB ----------------

    valiset_frame = ctk.CTkFrame(tab_valiset, fg_color="transparent")
    valiset_frame.pack(fill="both", expand=True, padx=10, pady=10)

    seti_valik_var = ctk.StringVar()

    ctk.CTkLabel(
        valiset_frame,
        text="Vali set:",
        font=suur_font,
        text_color=TEXT_DARK
    ).pack(anchor="w", pady=(0, 5))

    seti_valik = ctk.CTkComboBox(
        valiset_frame,
        variable=seti_valik_var,
        values=[],
        font=põhifont,
        fg_color="#ffffff",
        border_color=ACCENT_MAIN,
        button_color=ACCENT_MAIN,
        button_hover_color=ACCENT_MAIN_DARK,
        corner_radius=12
    )
    seti_valik.pack(fill="x", pady=(0, 15))

    nuppude_frame_valiset = ctk.CTkFrame(valiset_frame, fg_color="transparent")
    nuppude_frame_valiset.pack(pady=10)

    ctk.CTkButton(
        nuppude_frame_valiset,
        text="Vali set",
        command=vali_set,
        font=suur_font,
        fg_color=ACCENT_MAIN,
        hover_color=ACCENT_MAIN_DARK,
        corner_radius=20
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        nuppude_frame_valiset,
        text="Kustuta set",
        command=kustuta_valitud_set,
        font=suur_font,
        fg_color="#ffffff",
        text_color=ACCENT_MAIN,
        hover_color="#fdf1f7",
        border_width=2,
        border_color=ACCENT_MAIN,
        corner_radius=20
    ).pack(side="left", padx=10)

    # ---------------- ÕPIME TAB ----------------

    õpi_frame = ctk.CTkFrame(tab_õpi, fg_color="transparent")
    õpi_frame.pack(fill="both", expand=True, padx=10, pady=10)

    kaardi_indeks = 0
    aktiivsed_kaardid = []

    sona_silt = ctk.CTkLabel(
        õpi_frame,
        text="",
        font=("Segoe UI Semibold", 26),
        text_color=TEXT_DARK
    )
    sona_silt.pack(pady=(30, 15))

    definitsiooni_silt = ctk.CTkLabel(
        õpi_frame,
        text="",
        font=põhifont,
        wraplength=600,
        justify="center",
        text_color=TEXT_SOFT
    )
    definitsiooni_silt.pack(pady=(0, 20))

    # --- PROGRESS LABEL + BAR ---
    progress_label = ctk.CTkLabel(
        õpi_frame,
        text="0 / 0",
        font=põhifont,
        text_color=TEXT_SOFT
    )
    progress_label.pack(pady=(0, 5))

    progress_bar = ctk.CTkProgressBar(
        õpi_frame,
        progress_color=ACCENT_MAIN,
        fg_color="#f3f3f7",
        corner_radius=10,
        height=12
    )
    progress_bar.pack(fill="x", padx=80, pady=(0, 20))
    progress_bar.set(0)

    õpi_nuppude_frame = ctk.CTkFrame(õpi_frame, fg_color="transparent")
    õpi_nuppude_frame.pack(pady=10)

    ctk.CTkButton(
        õpi_nuppude_frame,
        text="Eelmine",
        command=eelmine_kaart,
        font=suur_font,
        fg_color="#ffffff",
        text_color=ACCENT_MAIN,
        hover_color="#fdf1f7",
        border_width=2,
        border_color=ACCENT_MAIN,
        corner_radius=20,
        width=120
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        õpi_nuppude_frame,
        text="Flip",
        command=pööra_kaart,
        font=suur_font,
        fg_color=ACCENT_MAIN,
        hover_color=ACCENT_MAIN_DARK,
        corner_radius=20,
        width=120
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        õpi_nuppude_frame,
        text="Järgmine",
        command=järgmine_kaart,
        font=suur_font,
        fg_color="#ffffff",
        text_color=ACCENT_MAIN,
        hover_color="#fdf1f7",
        border_width=2,
        border_color=ACCENT_MAIN,
        corner_radius=20,
        width=120
    ).pack(side="left", padx=10)

    # ---------------- MATA TAB ----------------

    mata_frame = ctk.CTkFrame(tab_mata, fg_color="transparent")
    mata_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(
        mata_frame,
        text="Tere tulemast kõrge matemaatika alustesse!",
        font=pealkiri_font,
        text_color=ACCENT_MAIN
    ).pack(pady=(20, 8))

    ctk.CTkLabel(
        mata_frame,
        text="Siia saad lisada eraldi info, lingid, ülesanded jne.",
        font=põhifont,
        text_color=TEXT_SOFT
    ).pack(pady=(0, 20))

    ctk.CTkButton(
        mata_frame,
        text="Hakkame õppima",
        font=suur_font,
        fg_color=ACCENT_SOFT_BLUE,
        hover_color="#9ec8ff",
        text_color=TEXT_DARK,
        corner_radius=20
    ).pack(pady=10)

    # Täida seti valik alguses + algne progress
    taida_seti_valik()
    uuenda_progress()

    root.mainloop()
