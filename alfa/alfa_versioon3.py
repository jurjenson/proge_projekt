"""
Projekt: Õppekaardid (CustomTkinter pastelne versioon progressbariga)
Autorid: Annabel Jürjenson, Minna Marie Kask
Kirjeldus:
Kasutaja saab valida õppimiseks valmis komplekti õppekaarte või ise komplekt luua.
Valmis komplektina on kasutamiseks kursuse "Kõrgem matemaatika I (alused)" õppekaardid.
"""

import sqlite3 # andmebaas
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import json


# ---------------- VÄRVIPALETT ----------------

PASTEL_TOP = "#ffe7f3"
PASTEL_BOTTOM = "#e3f6ff"
ACCENT_MAIN = "#f6aecb"
ACCENT_MAIN_DARK = "#ec8fb4"
ACCENT_SOFT_BLUE = "#b7d8ff"
TEXT_DARK = "#4b4b5a"
TEXT_SOFT = "#7a7a8a"


# ---------------- GLOBAL STATE ----------------
root = None
tabview = None
uhendus = None

seti_valik = None
seti_valik_var = None
seti_nimi_var = None
sona_var = None
definitsioon_var = None

aktiivsed_kaardid = []
kaardi_indeks = 0
näitab_vastust = False

progress_label = None
progress_bar = None

mode_label = None
card_box = None
flip_button = None

gradient_after_id = None


# ---------------- DB FUNKTSIOONID ----------------

def loo_tabelid(conn):   # loob tabelid andmebaasi, kui neid juba pole
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flashcard_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            definition TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES flashcard_sets(id) ON DELETE CASCADE
        )
    """)


def lisa_set(conn, nimi): # lisab uue rea flashcard_sets tabelisse
    cur = conn.cursor()
    cur.execute("INSERT INTO flashcard_sets (name) VALUES (?)", (nimi,))
    conn.commit()
    return cur.lastrowid


def lisa_kaart(conn, seti_id, sona, definitsioon): # lisab uue kaardi flashcards tabelisse
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO flashcards (set_id, word, definition) VALUES (?, ?, ?)",
        (seti_id, sona, definitsioon),
    )
    conn.commit()
    return cur.lastrowid # tagastab lisatud kaardi id


def saa_setid(conn): # tagastab kõik setid sõnastikuna {nimi: id}, kuna see on mugavam
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM flashcard_sets")
    rows = cur.fetchall()
    return {name: _id for (_id, name) in rows}


def saa_kaardid(conn, seti_id): # tagastab kõik kaardid antud seti id järgi
    cur = conn.cursor()
    cur.execute("SELECT word, definition FROM flashcards WHERE set_id = ?", (seti_id,))
    rows = cur.fetchall()
    return [(w, d) for (w, d) in rows]


def kustuta_set(conn, seti_id):
    global aktiivsed_kaardid, kaardi_indeks, näitab_vastust
    cur = conn.cursor()
    try:
        # töötab ka siis, kui CASCADE vanas db-s ei rakendu
        cur.execute("DELETE FROM flashcards WHERE set_id = ?", (seti_id,))
        cur.execute("DELETE FROM flashcard_sets WHERE id = ?", (seti_id,))
        conn.commit()

        if seti_valik_var is not None:
            seti_valik_var.set("")

        aktiivsed_kaardid = []
        kaardi_indeks = 0
        näitab_vastust = False
        clear_kaardid()
        taida_seti_valik()

        messagebox.showinfo("OK", "Set kustutatud.")
    except Exception as e:
        conn.rollback()
        messagebox.showerror("Viga", f"Seti kustutamine ebaõnnestus: {e}")


# ---------------- SETID / KAARDID ----------------

def loo_set():
    nimi = seti_nimi_var.get().strip()
    if not nimi:
        return
    olemas = saa_setid(uhendus)
    if nimi not in olemas:
        lisa_set(uhendus, nimi)

    taida_seti_valik()
    seti_nimi_var.set("")
    sona_var.set("")
    definitsioon_var.set("")


def lisa_sona(): # leiab id jargi seti ning lisab uue kaardi
    seti_nimi = seti_nimi_var.get().strip()
    sona = sona_var.get().strip()
    definitsioon = definitsioon_var.get().strip()

    if not (seti_nimi and sona and definitsioon):
        messagebox.showwarning("Puuduvad andmed", "Palun täida kõik väljad.")
        return

    setid = saa_setid(uhendus)
    seti_id = setid.get(seti_nimi) or lisa_set(uhendus, seti_nimi)
    lisa_kaart(uhendus, seti_id, sona, definitsioon)

    sona_var.set("")
    definitsioon_var.set("")
    taida_seti_valik()


def taida_seti_valik(): # täidab seti valiku comboboxi andmebaasi setidega
    if seti_valik is None:
        return
    setid = tuple(saa_setid(uhendus).keys())
    seti_valik.configure(values=setid)


def kustuta_valitud_set():
    nimi = seti_valik_var.get().strip()
    if not nimi:
        messagebox.showwarning("Viga", "Palun vali set.")
        return

    if not messagebox.askyesno("Kinnitus", f'Kas oled kindel, et soovid seti "{nimi}" kustutada?'):
        return

    setid = saa_setid(uhendus)
    if nimi not in setid:
        messagebox.showerror("Viga", "Valitud setti ei leitud andmebaasist.")
        taida_seti_valik()
        return

    kustuta_set(uhendus, setid[nimi])


def vali_set():
    global aktiivsed_kaardid, kaardi_indeks, näitab_vastust

    nimi = seti_valik_var.get().strip()
    if not nimi:
        aktiivsed_kaardid = []
        kaardi_indeks = 0
        näitab_vastust = False
        clear_kaardid()
        return

    setid = saa_setid(uhendus)
    if nimi not in setid:
        messagebox.showerror("Viga", "Valitud setti ei leitud andmebaasist.")
        taida_seti_valik()
        return

    aktiivsed_kaardid = saa_kaardid(uhendus, setid[nimi])
    kaardi_indeks = 0
    näitab_vastust = False
    naita_kaart()


def clear_kaardid(): # tühjendab kaardi kuva
    _set_card_text("")
    _set_mode("KÜSIMUS")
    uuenda_progress()


def naita_kaart():
    global näitab_vastust
    näitab_vastust = False # alati näita küsimust esialgu

    if aktiivsed_kaardid and 0 <= kaardi_indeks < len(aktiivsed_kaardid):
        küsimus, _ = aktiivsed_kaardid[kaardi_indeks]
        _set_mode("KÜSIMUS")
        _set_card_text(küsimus)
    else:
        _set_mode("KÜSIMUS")
        _set_card_text("")

    uuenda_progress()


def järgmine_kaart():
    global kaardi_indeks
    if not aktiivsed_kaardid:
        return
    kaardi_indeks = min(kaardi_indeks + 1, len(aktiivsed_kaardid) - 1) # ei lähe üle viimase kaardi
    naita_kaart()


def eelmine_kaart():
    global kaardi_indeks
    if not aktiivsed_kaardid:
        return
    kaardi_indeks = max(kaardi_indeks - 1, 0) # sama loogika, ei lase minna all 0
    naita_kaart()


# ---------------- JSON ----------------
def loe_mata_json(path="korgemmata.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [(item["küsimus"], item["vastus"]) for item in data["kaardid"]]


def hakka_oppima():
    global aktiivsed_kaardid, kaardi_indeks, näitab_vastust
    try:
        aktiivsed_kaardid = loe_mata_json("korgemmata.json")
        kaardi_indeks = 0
        näitab_vastust = False
        naita_kaart()
        tabview.set("Õpime")
    except FileNotFoundError:
        messagebox.showerror("Viga", "JSON faili ei leitud: korgemmata.json")
    except Exception as e:
        messagebox.showerror("Viga", f"JSON lugemine ebaõnnestus: {e}")


# ---------------- UI HELPERS ----------------

def _set_mode(text):
    if mode_label is not None:
        mode_label.configure(text=text)


def _set_card_text(text): # seab teksti kuvamise kaardil
    if card_box is None:
        return
    card_box.configure(state="normal")
    card_box.delete("1.0", "end")
    card_box.insert("1.0", text)
    card_box.see("1.0")
    card_box.configure(state="disabled")


def uuenda_progress():
    if progress_bar is None or progress_label is None:
        return
    if aktiivsed_kaardid:
        total = len(aktiivsed_kaardid)
        current = kaardi_indeks + 1
        progress_bar.set(current / total)
        progress_label.configure(text=f"{current} / {total}")
    else:
        progress_bar.set(0)
        progress_label.configure(text="0 / 0")



def pööra_kaart():
    global näitab_vastust
    if not (aktiivsed_kaardid and 0 <= kaardi_indeks < len(aktiivsed_kaardid)):
        return

    küsimus, vastus = aktiivsed_kaardid[kaardi_indeks]
    näitab_vastust = not näitab_vastust

    if näitab_vastust:
        _set_mode("VASTUS")
        _set_card_text(vastus if vastus is not None else "")
    else:
        _set_mode("KÜSIMUS")
        _set_card_text(küsimus)

    uuenda_progress()


def lisa_kursor(btn):
    btn.bind("<Enter>", lambda e, b=btn: b.configure(cursor="hand2"))
    btn.bind("<Leave>", lambda e, b=btn: b.configure(cursor=""))


# ---------------- GRADIENT ----------------
# ---------------- GRADIENT ----------------
def joonista_gradient(canvas, värv1=PASTEL_TOP, värv2=PASTEL_BOTTOM):
    w = max(canvas.winfo_width(), 1)
    h = max(canvas.winfo_height(), 1)

    canvas.delete("gradient")
    r1, g1, b1 = canvas.winfo_rgb(värv1)
    r2, g2, b2 = canvas.winfo_rgb(värv2)
    r1 //= 256; g1 //= 256; b1 //= 256
    r2 //= 256; g2 //= 256; b2 //= 256

    for i in range(h):
        r = int(r1 + (r2 - r1) * i / h)
        g = int(g1 + (g2 - g1) * i / h)
        b = int(b1 + (b2 - b1) * i / h)
        värv = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(0, i, w, i, tags=("gradient",), fill=värv)

    canvas.lower("gradient")


def schedule_gradient_redraw(canvas): # redraw rebounce, teeb UI sujuvamaks, kui akent rezisetakse, voib crashida voi UI palju uuesti joonistada
    global gradient_after_id
    if gradient_after_id is not None:
        try:
            root.after_cancel(gradient_after_id)
        except Exception:
            pass
    gradient_after_id = root.after(60, lambda: joonista_gradient(canvas, PASTEL_TOP, PASTEL_BOTTOM))


# ---------------- MAIN ----------------

if __name__ == "__main__":
    uhendus = sqlite3.connect("flashcards.db")
    uhendus.execute("PRAGMA foreign_keys = ON;")
    loo_tabelid(uhendus)

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Õppekaardid")
    root.geometry("900x650")
    root.minsize(800, 600)

    root.bind("<Return>", lambda e: pööra_kaart())

    # Gradient background
    gradient_canvas = tk.Canvas(root, highlightthickness=0, bd=0)
    gradient_canvas.place(relx=0, rely=0, relwidth=1, relheight=1) # täisekraanina rooti peale
    root.bind("<Configure>", lambda e: schedule_gradient_redraw(gradient_canvas))

    # Fontid
    põhifont = ("Montserrat", 18)
    pealkiri_font = ("Montserrat SemiBold", 30)
    suur_font = ("Montserrat SemiBold", 22)
    tab_font = ("Montserrat SemiBold", 16)

    # Main frame
    main_frame = ctk.CTkFrame(root, corner_radius=28, fg_color="white")
    main_frame.place(relx=0.5, rely=0.5, relwidth=0.9, relheight=0.9, anchor="center")

    ctk.CTkLabel(main_frame, text="Õppekaardid", font=pealkiri_font, text_color=ACCENT_MAIN).pack(pady=(10, 4))
    ctk.CTkLabel(
        main_frame,
        text="Loo oma setid või kasuta valmis komplekte",
        font=põhifont,
        text_color=TEXT_SOFT
    ).pack(pady=(0, 12))

    # Tabview
    tabview = ctk.CTkTabview(main_frame)
    tabview.pack(fill="both", expand=True, padx=20, pady=20)

    tab_looset = tabview.add("Loo set")
    tab_valiset = tabview.add("Vali set")
    tab_õpi = tabview.add("Õpime")
    tab_mata = tabview.add("Kõrgem matemaatika I (alused)")

    tabview._segmented_button.configure(
        font=tab_font,
        fg_color="#ffffff",
        selected_color=ACCENT_MAIN,
        selected_hover_color=ACCENT_MAIN_DARK,
        unselected_color="#ffffff",
        unselected_hover_color="#fdf1f7",
        text_color=TEXT_DARK,
        text_color_disabled=TEXT_SOFT
    )

    # ---------- LOO SET ----------
    seti_nimi_var = ctk.StringVar()
    sona_var = ctk.StringVar()
    definitsioon_var = ctk.StringVar()

    looset_frame = ctk.CTkFrame(tab_looset, fg_color="transparent")
    looset_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(looset_frame, text="Seti nimi:", font=suur_font, text_color=TEXT_DARK).pack(anchor="w", pady=(0, 5))
    ctk.CTkEntry(
        looset_frame, textvariable=seti_nimi_var, font=põhifont,
        fg_color="#ffffff", border_color=ACCENT_MAIN, border_width=1, corner_radius=12
    ).pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(looset_frame, text="Küsimus:", font=suur_font, text_color=TEXT_DARK).pack(anchor="w", pady=(5, 5))
    ctk.CTkEntry(
        looset_frame, textvariable=sona_var, font=põhifont,
        fg_color="#ffffff", border_color=ACCENT_MAIN, border_width=1, corner_radius=12
    ).pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(looset_frame, text="Vastus:", font=suur_font, text_color=TEXT_DARK).pack(anchor="w", pady=(5, 5))
    ctk.CTkEntry(
        looset_frame, textvariable=definitsioon_var, font=põhifont,
        fg_color="#ffffff", border_color=ACCENT_MAIN, border_width=1, corner_radius=12
    ).pack(fill="x", pady=(0, 15))

    nuppude_frame_looset = ctk.CTkFrame(looset_frame, fg_color="transparent")
    nuppude_frame_looset.pack(pady=10)

    btn_lisa = ctk.CTkButton(
        nuppude_frame_looset, text="Lisa küsimus", command=lisa_sona,
        font=suur_font, fg_color=ACCENT_MAIN, hover_color=ACCENT_MAIN_DARK, corner_radius=20
    )
    btn_lisa.pack(side="left", padx=10); lisa_kursor(btn_lisa)

    btn_salvesta = ctk.CTkButton(
        nuppude_frame_looset, text="Salvesta set", command=loo_set,
        font=suur_font, fg_color="#ffffff", text_color=ACCENT_MAIN,
        hover_color="#fdf1f7", border_width=2, border_color=ACCENT_MAIN, corner_radius=20
    )
    btn_salvesta.pack(side="left", padx=10); lisa_kursor(btn_salvesta)

    # ---------- VALI SET ----------
    valiset_frame = ctk.CTkFrame(tab_valiset, fg_color="transparent")
    valiset_frame.pack(fill="both", expand=True, padx=10, pady=10)

    seti_valik_var = ctk.StringVar()
    ctk.CTkLabel(valiset_frame, text="Vali set:", font=suur_font, text_color=TEXT_DARK).pack(anchor="w", pady=(0, 5))

    seti_valik = ctk.CTkComboBox(
        valiset_frame, variable=seti_valik_var, values=[], font=põhifont,
        fg_color="#ffffff", border_color=ACCENT_MAIN,
        button_color=ACCENT_MAIN, button_hover_color=ACCENT_MAIN_DARK, corner_radius=12
    )
    seti_valik.pack(fill="x", pady=(0, 15))

    nuppude_frame_valiset = ctk.CTkFrame(valiset_frame, fg_color="transparent")
    nuppude_frame_valiset.pack(pady=10)

    btn_vali = ctk.CTkButton(
        nuppude_frame_valiset, text="Vali set", command=vali_set,
        font=suur_font, fg_color=ACCENT_MAIN, hover_color=ACCENT_MAIN_DARK, corner_radius=20
    )
    btn_vali.pack(side="left", padx=10); lisa_kursor(btn_vali)

    btn_kustuta = ctk.CTkButton(
        nuppude_frame_valiset, text="Kustuta set", command=kustuta_valitud_set,
        font=suur_font, fg_color="#ffffff", text_color=ACCENT_MAIN,
        hover_color="#fdf1f7", border_width=2, border_color=ACCENT_MAIN, corner_radius=20
    )
    btn_kustuta.pack(side="left", padx=10); lisa_kursor(btn_kustuta)

    # ---------- ÕPIME ----------
    õpi_frame = ctk.CTkFrame(tab_õpi, fg_color="transparent")
    õpi_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # grid konteiner (keskele lukustamiseks)
    õpi_frame.grid_rowconfigure(0, weight=1)
    õpi_frame.grid_columnconfigure(0, weight=1)

    center = ctk.CTkFrame(õpi_frame, fg_color="transparent")
    center.grid(row=0, column=0, sticky="nsew")

    for r in range(4):
        center.grid_rowconfigure(r, weight=0)
    center.grid_rowconfigure(0, weight=1)  # kaart täidab ülejäänud ruumi
    center.grid_columnconfigure(0, weight=1)

    CARD_W, CARD_H = 620, 300

    card_frame = ctk.CTkFrame(
        center,
        width=CARD_W,
        height=CARD_H,
        fg_color="#ffffff",
        corner_radius=26,
        border_width=2,
        border_color="#f3c2d6"
    )
    card_frame.grid(row=0, column=0, pady=(10, 16))
    card_frame.grid_propagate(False)

    card_frame.grid_rowconfigure(1, weight=1)
    card_frame.grid_columnconfigure(0, weight=1)

    mode_label = ctk.CTkLabel(
        card_frame,
        text="KÜSIMUS",
        font=("Montserrat SemiBold", 15),
        text_color=TEXT_SOFT
    )
    mode_label.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))

    card_box = ctk.CTkTextbox(
        card_frame,
        wrap="word",
        font=("Montserrat SemiBold", 20)
    )
    card_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
    card_box.configure(state="disabled")

    progress_label = ctk.CTkLabel(center, text="0 / 0", font=("Montserrat", 16), text_color=TEXT_SOFT)
    progress_label.grid(row=1, column=0, pady=(0, 6))

    progress_bar = ctk.CTkProgressBar(
        center,
        width=480,
        progress_color=ACCENT_MAIN,
        fg_color="#f3f3f7",
        corner_radius=10,
        height=12
    )
    progress_bar.grid(row=2, column=0, pady=(0, 18))
    progress_bar.set(0)

    btn_wrap = ctk.CTkFrame(center, fg_color="transparent")
    btn_wrap.grid(row=3, column=0, pady=(0, 10))

    BTN_W, BTN_H = 155, 46
    BTN_BORDER = 2

    eelmine_btn = ctk.CTkButton(
        btn_wrap,
        text="Eelmine",
        command=eelmine_kaart,
        font=("Montserrat SemiBold", 18),
        width=BTN_W,
        height=BTN_H,
        fg_color="#ffffff",
        text_color=ACCENT_MAIN,
        hover_color="#fdf1f7",
        border_width=BTN_BORDER,
        border_color=ACCENT_MAIN,
        corner_radius=20
    )
    eelmine_btn.pack(side="left", padx=10); lisa_kursor(eelmine_btn)

    flip_button = ctk.CTkButton(
        btn_wrap,
        text="Flip",
        command=pööra_kaart,
        font=("Montserrat SemiBold", 18),
        width=BTN_W,
        height=BTN_H,
        fg_color=ACCENT_MAIN,
        text_color="white",
        hover_color=ACCENT_MAIN_DARK,
        border_width=BTN_BORDER,
        border_color=ACCENT_MAIN,
        corner_radius=20
    )
    flip_button.pack(side="left", padx=10); lisa_kursor(flip_button)

    järgmine_btn = ctk.CTkButton(
        btn_wrap,
        text="Järgmine",
        command=järgmine_kaart,
        font=("Montserrat SemiBold", 18),
        width=BTN_W,
        height=BTN_H,
        fg_color="#ffffff",
        text_color=ACCENT_MAIN,
        hover_color="#fdf1f7",
        border_width=BTN_BORDER,
        border_color=ACCENT_MAIN,
        corner_radius=20
    )
    järgmine_btn.pack(side="left", padx=10); lisa_kursor(järgmine_btn)

    # ---------- MATA ----------
    mata_frame = ctk.CTkFrame(tab_mata, fg_color="transparent")
    mata_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(
        mata_frame,
        text="Teretulemast kõrgema matemaatika alustesse!",
        font=pealkiri_font,
        text_color=ACCENT_MAIN
    ).pack(pady=(20, 8))

    ctk.CTkLabel(
        mata_frame,
        text="KM I õppekaardid on koostatud loengukonspekti põhjal,\net aidata Sul praktikumiks, kontrolltööks \nvõi eksamiks ettevalmistuda.\nEdu!",
        font=põhifont,
        text_color=TEXT_SOFT
    ).pack(pady=(0, 20))

    btn_hakka = ctk.CTkButton(
        mata_frame,
        text="Hakkame õppima",
        font=suur_font,
        fg_color=ACCENT_SOFT_BLUE,
        hover_color="#9ec8ff",
        text_color=TEXT_DARK,
        corner_radius=20,
        command=hakka_oppima
    )
    btn_hakka.pack(pady=10); lisa_kursor(btn_hakka)

    # init
    taida_seti_valik()
    uuenda_progress()
    schedule_gradient_redraw(gradient_canvas)

    root.mainloop()
    uhendus.close()
