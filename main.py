"""
Projekt: Õppekaardid (CustomTkinter pastelne versioon progressbariga)
Autorid: Annabel Jürjenson, Minna Marie Kask
Kirjeldus:
Kasutaja saab valida õppimiseks valmis komplekti õppekaarte või ise komplekt luua.
Valmis komplektina on kasutamiseks kursuse "Kõrgem matemaatika I (alused)" õppekaardid.
Enne programmi kasutamist tuleb paigaldada vajalikud teegid:
pip install customtkinter
Programm kasutab andmebaasina SQLite'i, mis on Pythoniga kaasas.
Lisaks on võimalik importida kaardid JSON-failist nimega "korgemmata.json".
JSON-faili struktuur peab olema järgmine:
{
    "kaardid": [
        {
            "küsimus": "Küsimuse tekst",
            "vastus": "Vastuse tekst"
        },
        ...
    ]
}
Enne programmi käivitamist veendu, et JSON-fail on samas kataloogis kui main.py.
Veendu ka, et sul on programmi peamine font "Montserrat" paigaldatud, et UI näeks välja nii nagu ette nähtud.

"""

import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import json
import csv
import time
from datetime import datetime


# ---------------- värvipalett ----------------

PASTEL_TOP = "#ffe7f3"
PASTEL_BOTTOM = "#e3f6ff"
ACCENT_MAIN = "#f6aecb"
ACCENT_MAIN_DARK = "#ec8fb4"
ACCENT_SOFT_BLUE = "#b7d8ff"
TEXT_DARK = "#4b4b5a"
TEXT_SOFT = "#7a7a8a"


# ---------------- globaalne olek ----------------

root = None          # peamine aken
tabview = None       # vahelehevaade (tabid)
uhendus = None       # sqlite ühendus

seti_valik = None
seti_valik_var = None
seti_nimi_var = None
sona_var = None
definitsioon_var = None

# aktiivsed kaardid õppimisvaates (lihtsustatud kujul, ainult id/word/definition)

aktiivsed_kaardid = []   # list of dicts: {"id": int|None, "word": str, "definition": str}
kaardi_indeks = 0        # mitmes kaart on parasjagu ees (0-põhine)
näitab_vastust = False   # kas kaart on flipped

progress_label = None    # progressi tekst (nt 3 / 10)
progress_bar = None      # progressi riba

mode_label = None        # silt "küsimus" / "vastus"
card_box = None          # tekstikast, kuhu kuvatakse küsimus/vastus
flip_button = None       # flip nupp (pööra kaart)

gradient_after_id = None # after() id, et gradienti joonistust throttle'ida

# õppimise sessioon (taimer)
session_start_ts = None      # sessiooni alguse timestamp (time.time())
session_timer_label = None   # silt, mis kuvab sessiooni aega
session_after_id = None      # after() id taimeri uuenduseks
shuffle_var = None           # kas segame kaardid enne õppimist

# haldus (manage cards) - kaartide muutmise vaheleht
manage_set_var = None
manage_set_combo = None
manage_search_var = None
manage_listbox = None
manage_cards_cache = []      # vahemälu: db-st loetud kaardid (koos statistika väljadega)
manage_selected_card_id = None

manage_word_var = None
manage_def_var = None

# raport
report_set_var = None
report_set_combo = None


# ---------------- db funktsioonid ----------------

def loo_tabelid(conn):
    # loob põhitabelid, kui neid veel ei eksisteeri
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
    conn.commit()


def db_migreeri_stats(conn):
    """
    lisab flashcards tabelile veerud statistika jaoks, kui neid veel pole.
    see hoiab vana andmebaasi ühilduvana (backward-compatible).
    """
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(flashcards)")
    cols = [row[1] for row in cur.fetchall()]

    # lisa veerud ainult siis, kui puudu
    vaja = {
        "seen_count": "INTEGER NOT NULL DEFAULT 0",
        "correct_count": "INTEGER NOT NULL DEFAULT 0",
        "wrong_count": "INTEGER NOT NULL DEFAULT 0",
        "last_seen": "TEXT",
        "last_result": "TEXT"  # "correct" / "wrong"
    }
    for col, coldef in vaja.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE flashcards ADD COLUMN {col} {coldef}")
    conn.commit()


def lisa_set(conn, nimi):
    # lisab uue seti nimega "nimi" ja tagastab uue seti id
    cur = conn.cursor()
    cur.execute("INSERT INTO flashcard_sets (name) VALUES (?)", (nimi,))
    conn.commit()
    return cur.lastrowid


def leia_seti_id(conn, nimi):
    # leiab seti id seti nime järgi (tagastab None, kui ei leitud)
    cur = conn.cursor()
    cur.execute("SELECT id FROM flashcard_sets WHERE name = ?", (nimi,))
    row = cur.fetchone()
    return row[0] if row else None


def lisa_kaart(conn, seti_id, sona, definitsioon):
    # lisab uue kaardi kindlasse setti
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO flashcards (set_id, word, definition) VALUES (?, ?, ?)",
        (seti_id, sona, definitsioon),
    )
    conn.commit()
    return cur.lastrowid


def uuenda_kaart(conn, card_id, word, definition):
    # uuendab olemasoleva kaardi küsimuse/vastuse (id järgi)
    cur = conn.cursor()
    cur.execute(
        "UPDATE flashcards SET word = ?, definition = ? WHERE id = ?",
        (word, definition, card_id)
    )
    conn.commit()


def kustuta_kaart(conn, card_id):
    # kustutab ühe kaardi id järgi
    cur = conn.cursor()
    cur.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    conn.commit()


def saa_setid(conn):
    # tagastab kõik setid kujul: {nimi: id}
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM flashcard_sets ORDER BY name COLLATE NOCASE")
    rows = cur.fetchall()
    return {name: _id for (_id, name) in rows}


def saa_kaardid(conn, seti_id):
    """
    tagastab seti kaardid koos id ja statistikaga (db-s olev täisinfo).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT id, word, definition, seen_count, correct_count, wrong_count, last_seen, last_result
        FROM flashcards
        WHERE set_id = ?
        ORDER BY id ASC
    """, (seti_id,))
    rows = cur.fetchall()

    cards = []
    for (cid, w, d, seen, cor, wr, ls, lr) in rows:
        cards.append({
            "id": cid,
            "word": w,
            "definition": d,
            "seen": seen,
            "correct": cor,
            "wrong": wr,
            "last_seen": ls,
            "last_result": lr
        })
    return cards


def saa_kaardid_otsinguga(conn, seti_id, q):
    # otsib kaarte nii küsimuse kui ka vastuse tekstist (case-insensitive)
    q = (q or "").strip().lower()
    if not q:
        return saa_kaardid(conn, seti_id)

    cur = conn.cursor()
    like = f"%{q}%"
    cur.execute("""
        SELECT id, word, definition, seen_count, correct_count, wrong_count, last_seen, last_result
        FROM flashcards
        WHERE set_id = ?
          AND (LOWER(word) LIKE ? OR LOWER(definition) LIKE ?)
        ORDER BY id ASC
    """, (seti_id, like, like))
    rows = cur.fetchall()

    cards = []
    for (cid, w, d, seen, cor, wr, ls, lr) in rows:
        cards.append({
            "id": cid,
            "word": w,
            "definition": d,
            "seen": seen,
            "correct": cor,
            "wrong": wr,
            "last_seen": ls,
            "last_result": lr
        })
    return cards


def märgi_tulemus(conn, card_id, tulemus):
    """
    salvestab statistika db-sse.
    tulemus: "correct" või "wrong"

    oluline: json-temp kaartidel on id=None, nende puhul ei kirjutata db-sse.
    """
    if card_id is None:
        return  # json-temp kaartidel pole db id-d

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()

    if tulemus == "correct":
        cur.execute("""
            UPDATE flashcards
            SET seen_count = seen_count + 1,
                correct_count = correct_count + 1,
                last_seen = ?,
                last_result = 'correct'
            WHERE id = ?
        """, (now, card_id))
    else:
        cur.execute("""
            UPDATE flashcards
            SET seen_count = seen_count + 1,
                wrong_count = wrong_count + 1,
                last_seen = ?,
                last_result = 'wrong'
            WHERE id = ?
        """, (now, card_id))

    conn.commit()


def kustuta_set(conn, seti_id):
    # kustutab seti ja selle kaardid ning nullib aktiivse õppimise oleku
    global aktiivsed_kaardid, kaardi_indeks, näitab_vastust
    cur = conn.cursor()
    try:
        # töötab ka siis, kui cascade vanas db-s ei rakendu
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
        taida_manage_setid()
        taida_report_setid()

        messagebox.showinfo("OK", "Set kustutatud.")
    except Exception as e:
        conn.rollback()
        messagebox.showerror("Viga", f"Seti kustutamine ebaõnnestus: {e}")


# ---------------- setid / kaardid ----------------
def loo_set():
    # loob seti (kui seda veel ei ole) ja clearib
    nimi = seti_nimi_var.get().strip()
    if not nimi:
        return
    olemas = saa_setid(uhendus)
    if nimi not in olemas:
        lisa_set(uhendus, nimi)

    taida_seti_valik()
    taida_manage_setid()
    taida_report_setid()

    seti_nimi_var.set("")
    sona_var.set("")
    definitsioon_var.set("")


def lisa_sona():
    # lisab ühe kaardi (küsimus+vastus) valitud setti
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
    taida_manage_setid()
    taida_report_setid()


def taida_seti_valik():
    # täidab "vali set" combobox'i väärtused
    if seti_valik is None:
        return
    setid = tuple(saa_setid(uhendus).keys())
    seti_valik.configure(values=setid)


def kustuta_valitud_set():
    # kustutab kasutaja valitud seti (kinnitusega)
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
    # laeb valitud seti kaardid õppimisvaatesse ja alustab sessiooni
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

    cards = saa_kaardid(uhendus, setid[nimi])

    # convertib db kaardid õppimisvaate formaati (stats välju siin ei kasuta)
    aktiivsed_kaardid = [{"id": c["id"], "word": c["word"], "definition": c["definition"]} for c in cards]

    # kui "shuffle" on sees, segame järjestuse
    if shuffle_var is not None and shuffle_var.get():
        import random
        random.shuffle(aktiivsed_kaardid)

    kaardi_indeks = 0
    näitab_vastust = False
    alusta_sessioon()
    naita_kaart()
    tabview.set("Õpime")


# ---------------- õppimine (ui + loogika) ----------------

def clear_kaardid():
    # puhastab kaardi teksti ja paneb režiimi tagasi "küsimus"
    _set_card_text("")
    _set_mode("KÜSIMUS")
    uuenda_progress()


def naita_kaart():
    # kuvab hetkel aktiivse kaardi küsimuse poole (vastus peidetud)
    global näitab_vastust
    näitab_vastust = False

    if aktiivsed_kaardid and 0 <= kaardi_indeks < len(aktiivsed_kaardid):
        küsimus = aktiivsed_kaardid[kaardi_indeks]["word"]
        _set_mode("KÜSIMUS")
        _set_card_text(küsimus)
    else:
        _set_mode("KÜSIMUS")
        _set_card_text("")

    uuenda_progress()


def järgmine_kaart():
    # liigub ühe kaardi võrra edasi 
    global kaardi_indeks
    if not aktiivsed_kaardid:
        return
    kaardi_indeks = min(kaardi_indeks + 1, len(aktiivsed_kaardid) - 1) # piirid
    naita_kaart()


def eelmine_kaart():
    # liigub ühe kaardi võrra tagasi (piiridesse kinni)
    global kaardi_indeks
    if not aktiivsed_kaardid:
        return
    kaardi_indeks = max(kaardi_indeks - 1, 0)
    naita_kaart()


def pööra_kaart():
    # vahetab küsimuse ja vastuse kuvamist (flip)
    global näitab_vastust
    if not (aktiivsed_kaardid and 0 <= kaardi_indeks < len(aktiivsed_kaardid)):
        return

    # väike visuaalne "pulse" flip nupule
    pulse_button(flip_button)

    küsimus = aktiivsed_kaardid[kaardi_indeks]["word"]
    vastus = aktiivsed_kaardid[kaardi_indeks]["definition"]
    näitab_vastust = not näitab_vastust

    if näitab_vastust:
        _set_mode("VASTUS")
        _set_card_text(vastus if vastus is not None else "")
    else:
        _set_mode("KÜSIMUS")
        _set_card_text(küsimus)

    uuenda_progress()


def tean_kaart():
    """
    märgib kaardi õigeks ja liigub edasi.
    """
    global kaardi_indeks
    if not aktiivsed_kaardid:
        return

    card = aktiivsed_kaardid[kaardi_indeks]
    märgi_tulemus(uhendus, card.get("id"), "correct")

    # liigu edasi (kui viimane kaart, jääb sinna)
    if kaardi_indeks < len(aktiivsed_kaardid) - 1:
        kaardi_indeks += 1
    naita_kaart()


def ei_tea_kaart():
    """
    märgib kaardi valeks ja teeb lihtsa spaced repetition'i:
    - saadab kaardi listi lõppu (et ta tuleks uuesti).
    - indeks jääb samasse kohta, et järgmine kaart tuleks ette.
    """
    global kaardi_indeks
    if not aktiivsed_kaardid:
        return

    card = aktiivsed_kaardid[kaardi_indeks]
    märgi_tulemus(uhendus, card.get("id"), "wrong")

    # kui on rohkem kui 1 kaart, liigutame selle lõppu
    if len(aktiivsed_kaardid) > 1:
        item = aktiivsed_kaardid.pop(kaardi_indeks)
        aktiivsed_kaardid.append(item)
        if kaardi_indeks >= len(aktiivsed_kaardid):
            kaardi_indeks = len(aktiivsed_kaardid) - 1

    naita_kaart()


# ---------------- json / csv import / export ----------------

def loe_json_fail(path):
    # loeb json faili ja tagastab (setinimi, [(küsimus, vastus), ...])
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # lubab kahte varianti:
    # a) {"seti_nimi": "...", "kaardid":[{"küsimus":"..","vastus":".."}, ...]}
    # b) {"kaardid":[{"küsimus":"..","vastus":".."}, ...]}  (seti nimi küsitakse failinimest)
    setinimi = data.get("seti_nimi")
    kaardid_raw = data.get("kaardid", [])

    cards = []
    for item in kaardid_raw:
        q = item.get("küsimus", "").strip()
        a = item.get("vastus", "").strip()
        if q and a:
            cards.append((q, a))

    return setinimi, cards


def import_json_db():
    # impordib json failist kaardid db-sse (tekitab seti kui vaja)
    path = filedialog.askopenfilename(
        title="Vali JSON fail",
        filetypes=[("JSON", "*.json"), ("All files", "*.*")]
    )
    if not path:
        return

    try:
        setinimi, cards = loe_json_fail(path)
        if not setinimi:
            # fallback: failinimi ilma laiendita
            import os
            setinimi = os.path.splitext(os.path.basename(path))[0]

        if not cards:
            messagebox.showwarning("Tühi", "JSON-ist ei leitud ühtegi kaarti (küsimus+vastus).")
            return

        # loo set kui vaja
        sid = leia_seti_id(uhendus, setinimi) or lisa_set(uhendus, setinimi)

        # lisa kaardid
        for (q, a) in cards:
            lisa_kaart(uhendus, sid, q, a)

        taida_seti_valik()
        taida_manage_setid()
        taida_report_setid()

        messagebox.showinfo("OK", f"Imporditud: {len(cards)} kaarti setti '{setinimi}'.")
    except Exception as e:
        messagebox.showerror("Viga", f"Import ebaõnnestus: {e}")


def import_csv_db():
    # impordib csv failist kaardid db-sse (veergude nimed: küsimus/vastus või question/answer)
    path = filedialog.askopenfilename(
        title="Vali CSV fail",
        filetypes=[("CSV", "*.csv"), ("All files", "*.*")]
    )
    if not path:
        return

    try:
        import os
        setinimi = os.path.splitext(os.path.basename(path))[0]
        sid = leia_seti_id(uhendus, setinimi) or lisa_set(uhendus, setinimi)

        count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # eeldame veerge: küsimus, vastus (või question, answer)
            for row in reader:
                q = (row.get("küsimus") or row.get("question") or "").strip()
                a = (row.get("vastus") or row.get("answer") or "").strip()
                if q and a:
                    lisa_kaart(uhendus, sid, q, a)
                    count += 1

        taida_seti_valik()
        taida_manage_setid()
        taida_report_setid()

        messagebox.showinfo("OK", f"Imporditud: {count} kaarti setti '{setinimi}'.")
    except Exception as e:
        messagebox.showerror("Viga", f"CSV import ebaõnnestus: {e}")


def export_valitud_set_json():
    # ekspordib valitud seti json faili
    nimi = (seti_valik_var.get() or "").strip()
    if not nimi:
        messagebox.showwarning("Viga", "Vali set, mida eksportida.")
        return

    setid = saa_setid(uhendus)
    sid = setid.get(nimi)
    if not sid:
        messagebox.showerror("Viga", "Setti ei leitud DB-st.")
        return

    path = filedialog.asksaveasfilename(
        title="Salvesta JSON",
        defaultextension=".json",
        filetypes=[("JSON", "*.json")]
    )
    if not path:
        return

    cards = saa_kaardid(uhendus, sid)
    payload = {
        "seti_nimi": nimi,
        "kaardid": [{"küsimus": c["word"], "vastus": c["definition"]} for c in cards]
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("OK", "JSON eksporditud.")
    except Exception as e:
        messagebox.showerror("Viga", f"Ekspordi viga: {e}")


def export_valitud_set_csv():
    # ekspordib valitud seti csv faili (veergudega: küsimus, vastus)
    nimi = (seti_valik_var.get() or "").strip()
    if not nimi:
        messagebox.showwarning("Viga", "Vali set, mida eksportida.")
        return

    setid = saa_setid(uhendus)
    sid = setid.get(nimi)
    if not sid:
        messagebox.showerror("Viga", "Setti ei leitud DB-st.")
        return

    path = filedialog.asksaveasfilename(
        title="Salvesta CSV",
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv")]
    )
    if not path:
        return

    cards = saa_kaardid(uhendus, sid)
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["küsimus", "vastus"])
            writer.writeheader()
            for c in cards:
                writer.writerow({"küsimus": c["word"], "vastus": c["definition"]})
        messagebox.showinfo("OK", "CSV eksporditud.")
    except Exception as e:
        messagebox.showerror("Viga", f"Ekspordi viga: {e}")


# ---------------- html raport ----------------

def taida_report_setid():
    # täidab raporti comboboxi seti nimedega
    if report_set_combo is None:
        return
    report_set_combo.configure(values=tuple(saa_setid(uhendus).keys()))


def export_report_html():
    # genereerib valitud seti statistikaga html raporti
    nimi = (report_set_var.get() or "").strip()
    if not nimi:
        messagebox.showwarning("Viga", "Vali set raporti jaoks.")
        return

    setid = saa_setid(uhendus)
    sid = setid.get(nimi)
    if not sid:
        messagebox.showerror("Viga", "Setti ei leitud DB-st.")
        return

    path = filedialog.asksaveasfilename(
        title="Salvesta raport (HTML)",
        defaultextension=".html",
        filetypes=[("HTML", "*.html")]
    )
    if not path:
        return

    cards = saa_kaardid(uhendus, sid)
    total = len(cards)
    seen_sum = sum(c["seen"] for c in cards)
    cor_sum = sum(c["correct"] for c in cards)
    wr_sum = sum(c["wrong"] for c in cards)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows_html = []
    for c in cards:
        rows_html.append(
            "<tr>"
            f"<td>{escape_html(c['word'])}</td>"
            f"<td>{escape_html(c['definition'])}</td>"
            f"<td style='text-align:center'>{c['seen']}</td>"
            f"<td style='text-align:center'>{c['correct']}</td>"
            f"<td style='text-align:center'>{c['wrong']}</td>"
            f"<td>{escape_html(c['last_seen'] or '')}</td>"
            f"<td>{escape_html(c['last_result'] or '')}</td>"
            "</tr>"
        )

    html = f"""<!doctype html>
<html lang="et">
<head>
<meta charset="utf-8">
<title>Õppekaartide raport - {escape_html(nimi)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
h1 {{ margin-bottom: 6px; }}
.small {{ color: #666; margin-top: 0; }}
.card {{ border: 1px solid #ddd; border-radius: 10px; padding: 16px; margin: 16px 0; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
th {{ background: #f5f5f5; }}
</style>
</head>
<body>
<h1>Õppekaartide raport</h1>
<p class="small">Set: <b>{escape_html(nimi)}</b> · Genereeritud: {escape_html(now)}</p>

<div class="card">
<b>Kokkuvõte</b><br>
Kaartide arv: {total}<br>
Nähtud kokku: {seen_sum}<br>
Õiged kokku: {cor_sum}<br>
Valed kokku: {wr_sum}<br>
</div>

<div class="card">
<b>Kaartide statistika</b>
<table>
<thead>
<tr>
<th>Küsimus</th><th>Vastus</th><th>Nähtud</th><th>Õige</th><th>Vale</th><th>Viimati nähtud</th><th>Viimane tulemus</th>
</tr>
</thead>
<tbody>
{''.join(rows_html)}
</tbody>
</table>
</div>

</body>
</html>
"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        messagebox.showinfo("OK", "Raport salvestatud (HTML).")
    except Exception as e:
        messagebox.showerror("Viga", f"Raporti salvestamine ebaõnnestus: {e}")


def escape_html(s):
    # lihtne html-escape, et raportis ei "lõhuks" erimärgid kujundust
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ---------------- ui helpers ----------------

def _set_mode(text):
    # uuendab režiimisildi ("küsimus"/"vastus") teksti
    if mode_label is not None:
        mode_label.configure(text=text)


def _set_card_text(text):
    # kirjutab kaardi tekstikasti sisu (disabled -> normal -> disabled, et user ei muudaks)
    if card_box is None:
        return
    card_box.configure(state="normal")
    card_box.delete("1.0", "end")
    card_box.insert("1.0", text)
    card_box.see("1.0")
    card_box.configure(state="disabled")


def uuenda_progress():
    # uuendab progressi riba ja teksti vastavalt aktiivsete kaartide arvule ja indeksile
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


def pulse_button(btn):
    # väike visuaalne efekt nupule (lühike värvivahetus)
    if btn is None:
        return
    try:
        orig = btn.cget("fg_color")
        btn.configure(fg_color=ACCENT_MAIN_DARK)
        root.after(120, lambda: btn.configure(fg_color=orig))
    except Exception:
        pass


# ---------------- gradient ----------------
def joonista_gradient(canvas, värv1=PASTEL_TOP, värv2=PASTEL_BOTTOM):
    # joonistab vertikaalse gradiendi canvas'ele rida-realt
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


def schedule_gradient_redraw(canvas):
    # throttle'ib gradienti uuestijoonistuse, et akna resize ei teeks liiga tihedalt
    global gradient_after_id
    if gradient_after_id is not None:
        try:
            root.after_cancel(gradient_after_id)
        except Exception:
            pass
    gradient_after_id = root.after(60, lambda: joonista_gradient(canvas, PASTEL_TOP, PASTEL_BOTTOM))


# ---------------- sessiooni taimer ----------------

def alusta_sessioon():
    # käivitab (või restartib) sessiooni taimeri
    global session_start_ts
    session_start_ts = time.time()
    uuenda_taimer()


def uuenda_taimer():
    # uuendab taimeri silti ja planeerib järgmise uuenduse
    global session_after_id
    if session_timer_label is None:
        return

    if session_start_ts is None:
        session_timer_label.configure(text="Sessioon: 00:00")
        return

    elapsed = int(time.time() - session_start_ts)
    mm = elapsed // 60
    ss = elapsed % 60
    session_timer_label.configure(text=f"Sessioon: {mm:02d}:{ss:02d}")

    # schedule next update
    if root is not None:
        session_after_id = root.after(500, uuenda_taimer)


# ---------------- haldus (manage cards) ----------------

def taida_manage_setid():
    # täidab halduse comboboxi seti nimedega
    if manage_set_combo is None:
        return
    manage_set_combo.configure(values=tuple(saa_setid(uhendus).keys()))


def manage_laadi_kaardid():
    # laeb valitud seti kaardid (võimaliku otsinguga) halduse listi
    global manage_cards_cache, manage_selected_card_id
    manage_selected_card_id = None
    manage_word_var.set("")
    manage_def_var.set("")

    setinimi = (manage_set_var.get() or "").strip()
    if not setinimi:
        manage_cards_cache = []
        manage_refresh_list()
        return

    setid = saa_setid(uhendus)
    sid = setid.get(setinimi)
    if not sid:
        manage_cards_cache = []
        manage_refresh_list()
        return

    q = (manage_search_var.get() or "").strip()
    manage_cards_cache = saa_kaardid_otsinguga(uhendus, sid, q)
    manage_refresh_list()


def manage_refresh_list():
    # uuendab listboxi sisu manage_cards_cache põhjal
    if manage_listbox is None:
        return

    manage_listbox.delete(0, "end")
    for c in manage_cards_cache:
        # lühike kuvamine
        title = c["word"]
        if len(title) > 60:
            title = title[:57] + "..."
        manage_listbox.insert("end", f"[{c['id']}] {title}")


def manage_vali_listist(event=None):
    # kui kasutaja valib listist kaardi, täidame parempoolsed väljad
    global manage_selected_card_id
    if manage_listbox is None:
        return
    sel = manage_listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    if idx < 0 or idx >= len(manage_cards_cache):
        return

    c = manage_cards_cache[idx]
    manage_selected_card_id = c["id"]
    manage_word_var.set(c["word"])
    manage_def_var.set(c["definition"])


def manage_salvesta_muudatus():
    # salvestab valitud kaardi muudatused db-sse
    global manage_selected_card_id
    if manage_selected_card_id is None:
        messagebox.showwarning("Viga", "Vali enne kaart listist.")
        return

    w = (manage_word_var.get() or "").strip()
    d = (manage_def_var.get() or "").strip()
    if not w or not d:
        messagebox.showwarning("Viga", "Küsimus ja vastus ei tohi olla tühjad.")
        return

    try:
        uuenda_kaart(uhendus, manage_selected_card_id, w, d)
        manage_laadi_kaardid()
        taida_seti_valik()
        messagebox.showinfo("OK", "Kaart uuendatud.")
    except Exception as e:
        messagebox.showerror("Viga", f"Uuendamine ebaõnnestus: {e}")


def manage_kustuta_valitud():
    # kustutab valitud kaardi db-st (kinnitusega)
    global manage_selected_card_id
    if manage_selected_card_id is None:
        messagebox.showwarning("Viga", "Vali enne kaart listist.")
        return

    if not messagebox.askyesno("Kinnitus", "Kas kustutame valitud kaardi?"):
        return

    try:
        kustuta_kaart(uhendus, manage_selected_card_id)
        manage_selected_card_id = None
        manage_word_var.set("")
        manage_def_var.set("")
        manage_laadi_kaardid()
        messagebox.showinfo("OK", "Kaart kustutatud.")
    except Exception as e:
        messagebox.showerror("Viga", f"Kustutamine ebaõnnestus: {e}")


# ---------------- klaviatuuri otseteed ----------------

def bind_hotkeys():
    # flip
    root.bind("<Return>", lambda e: pööra_kaart())
    root.bind("<space>", lambda e: pööra_kaart())

    # jargmine / eelmine
    root.bind("<Right>", lambda e: järgmine_kaart())
    root.bind("<Left>", lambda e: eelmine_kaart())

    # tean / ei tea
    root.bind("1", lambda e: ei_tea_kaart())
    root.bind("2", lambda e: tean_kaart())


def loe_mata_json(path="korgemmata.json"):
    # loeb kõrgema mata json faili ja tagastab (küsimus, vastus) paarid
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [(item["küsimus"], item["vastus"]) for item in data["kaardid"]]


def hakka_oppima_mata():
    """
    laeb korgemmata.json kaardid aktiivseks ja läheb õpime tab'i.
    need kaardid on sessioonis olemas, aga statistikat db-sse ei kirjutata,
    sest neil pole card_id-d (id=None).
    """
    global aktiivsed_kaardid, kaardi_indeks, näitab_vastust

    try:
        pairs = loe_mata_json("korgemmata.json")
        aktiivsed_kaardid = [{"id": None, "word": q, "definition": a} for (q, a) in pairs]

        if shuffle_var is not None and shuffle_var.get():
            import random
            random.shuffle(aktiivsed_kaardid)

        kaardi_indeks = 0
        näitab_vastust = False
        alusta_sessioon()
        naita_kaart()
        tabview.set("Õpime")

    except FileNotFoundError:
        messagebox.showerror("Viga", "JSON faili ei leitud: korgemmata.json")
    except Exception as e:
        messagebox.showerror("Viga", f"JSON lugemine ebaõnnestus: {e}")


# ---------------- main ----------------

if __name__ == "__main__":
    # db ühendus + tabelite kontroll/migratsioon
    uhendus = sqlite3.connect("flashcards.db")
    uhendus.execute("PRAGMA foreign_keys = ON;")
    loo_tabelid(uhendus)
    db_migreeri_stats(uhendus)

    # customtkinter teema
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    # root
    root = ctk.CTk()
    root.title("Õppekaardid")
    root.geometry("980x700")
    root.minsize(880, 620)

    # klaviatuuri otseteed
    bind_hotkeys()

    # gradient taust
    gradient_canvas = tk.Canvas(root, highlightthickness=0, bd=0)
    gradient_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    root.bind("<Configure>", lambda e: schedule_gradient_redraw(gradient_canvas))

    # fondid
    põhifont = ("Montserrat", 18)
    pealkiri_font = ("Montserrat SemiBold", 30)
    suur_font = ("Montserrat SemiBold", 22)
    tab_font = ("Montserrat SemiBold", 16)

    # peamine aken
    main_frame = ctk.CTkFrame(root, corner_radius=28, fg_color="white")
    main_frame.place(relx=0.5, rely=0.5, relwidth=0.92, relheight=0.92, anchor="center")

    ctk.CTkLabel(main_frame, text="Õppekaardid", font=pealkiri_font, text_color=ACCENT_MAIN).pack(pady=(10, 4))
    ctk.CTkLabel(
        main_frame,
        text="Loo oma setid või kasuta valmis komplekte",
        font=põhifont,
        text_color=TEXT_SOFT
    ).pack(pady=(0, 12))

    # tabview (vahelehed)
    tabview = ctk.CTkTabview(main_frame)
    tabview.pack(fill="both", expand=True, padx=20, pady=20)

    tab_looset = tabview.add("Loo set")
    tab_valiset = tabview.add("Vali set")
    tab_õpi = tabview.add("Õpime")
    tab_halda = tabview.add("Halda kaarte")
    tab_raport = tabview.add("Raport")
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

    # ---------- loo set ----------
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
    btn_lisa.pack(side="left", padx=10)

    btn_salvesta = ctk.CTkButton(
        nuppude_frame_looset, text="Salvesta set", command=loo_set,
        font=suur_font, fg_color="#ffffff", text_color=ACCENT_MAIN,
        hover_color="#fdf1f7", border_width=2, border_color=ACCENT_MAIN, corner_radius=20
    )
    btn_salvesta.pack(side="left", padx=10)

    # ---------- vali set ----------
    valiset_frame = ctk.CTkFrame(tab_valiset, fg_color="transparent")
    valiset_frame.pack(fill="both", expand=True, padx=10, pady=10)

    seti_valik_var = ctk.StringVar()
    shuffle_var = ctk.BooleanVar(value=False)

    ctk.CTkLabel(valiset_frame, text="Vali set:", font=suur_font, text_color=TEXT_DARK).pack(anchor="w", pady=(0, 5))

    seti_valik = ctk.CTkComboBox(
        valiset_frame, variable=seti_valik_var, values=[], font=põhifont,
        fg_color="#ffffff", border_color=ACCENT_MAIN,
        button_color=ACCENT_MAIN, button_hover_color=ACCENT_MAIN_DARK, corner_radius=12
    )
    seti_valik.pack(fill="x", pady=(0, 10))

    chk = ctk.CTkCheckBox(
        valiset_frame, text="Sega kaardid (shuffle)", variable=shuffle_var,
        font=("Montserrat", 16), text_color=TEXT_DARK
    )
    chk.pack(anchor="w", pady=(0, 10))

    nuppude_frame_valiset = ctk.CTkFrame(valiset_frame, fg_color="transparent")
    nuppude_frame_valiset.pack(pady=10)

    btn_vali = ctk.CTkButton(
        nuppude_frame_valiset, text="Alusta õppimist", command=vali_set,
        font=suur_font, fg_color=ACCENT_MAIN, hover_color=ACCENT_MAIN_DARK, corner_radius=20
    )
    btn_vali.pack(side="left", padx=10)

    btn_kustuta = ctk.CTkButton(
        nuppude_frame_valiset, text="Kustuta set", command=kustuta_valitud_set,
        font=suur_font, fg_color="#ffffff", text_color=ACCENT_MAIN,
        hover_color="#fdf1f7", border_width=2, border_color=ACCENT_MAIN, corner_radius=20
    )
    btn_kustuta.pack(side="left", padx=10)

    # import/export rida
    io_frame = ctk.CTkFrame(valiset_frame, fg_color="transparent")
    io_frame.pack(pady=(20, 0), fill="x")

    ctk.CTkLabel(io_frame, text="Import / Export:", font=("Montserrat SemiBold", 18), text_color=TEXT_DARK).pack(anchor="w")

    io_btns = ctk.CTkFrame(io_frame, fg_color="transparent")
    io_btns.pack(anchor="w", pady=(8, 0))

    ctk.CTkButton(io_btns, text="Import JSON", command=import_json_db,
                  font=("Montserrat SemiBold", 16), fg_color=ACCENT_SOFT_BLUE,
                  hover_color="#9ec8ff", text_color=TEXT_DARK, corner_radius=18).pack(side="left", padx=6)

    ctk.CTkButton(io_btns, text="Import CSV", command=import_csv_db,
                  font=("Montserrat SemiBold", 16), fg_color=ACCENT_SOFT_BLUE,
                  hover_color="#9ec8ff", text_color=TEXT_DARK, corner_radius=18).pack(side="left", padx=6)

    ctk.CTkButton(io_btns, text="Export JSON", command=export_valitud_set_json,
                  font=("Montserrat SemiBold", 16), fg_color="#ffffff", text_color=ACCENT_MAIN,
                  hover_color="#fdf1f7", border_width=2, border_color=ACCENT_MAIN, corner_radius=18).pack(side="left", padx=6)

    ctk.CTkButton(io_btns, text="Export CSV", command=export_valitud_set_csv,
                  font=("Montserrat SemiBold", 16), fg_color="#ffffff", text_color=ACCENT_MAIN,
                  hover_color="#fdf1f7", border_width=2, border_color=ACCENT_MAIN, corner_radius=18).pack(side="left", padx=6)

    # ---------- õpime ----------
    
    õpi_frame = ctk.CTkFrame(tab_õpi, fg_color="transparent")
    õpi_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # grid konteiner (keskele lukustamiseks)

    õpi_frame.grid_rowconfigure(0, weight=1)
    õpi_frame.grid_columnconfigure(0, weight=1)

    center = ctk.CTkFrame(õpi_frame, fg_color="transparent")
    center.grid(row=0, column=0, sticky="nsew")

    for r in range(6):
        center.grid_rowconfigure(r, weight=0)
    center.grid_rowconfigure(0, weight=1)
    center.grid_columnconfigure(0, weight=1)

    CARD_W, CARD_H = 680, 320

    card_frame = ctk.CTkFrame(
        center,
        width=CARD_W,
        height=CARD_H,
        fg_color="#ffffff",
        corner_radius=26,
        border_width=2,
        border_color="#f3c2d6"
    )
    card_frame.grid(row=0, column=0, pady=(10, 10))
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

    # sessiooni taimer

    session_timer_label = ctk.CTkLabel(center, text="Sessioon: 00:00", font=("Montserrat", 16), text_color=TEXT_SOFT)
    session_timer_label.grid(row=1, column=0, pady=(0, 4))

    progress_label = ctk.CTkLabel(center, text="0 / 0", font=("Montserrat", 16), text_color=TEXT_SOFT)
    progress_label.grid(row=2, column=0, pady=(0, 6))

    progress_bar = ctk.CTkProgressBar(
        center,
        width=520,
        progress_color=ACCENT_MAIN,
        fg_color="#f3f3f7",
        corner_radius=10,
        height=12
    )
    progress_bar.grid(row=3, column=0, pady=(0, 18))
    progress_bar.set(0)

    btn_wrap = ctk.CTkFrame(center, fg_color="transparent")
    btn_wrap.grid(row=4, column=0, pady=(0, 6))

    BTN_W, BTN_H = 150, 46
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
    eelmine_btn.pack(side="left", padx=8)

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
    flip_button.pack(side="left", padx=8)

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
    järgmine_btn.pack(side="left", padx=8)

    btn_wrap2 = ctk.CTkFrame(center, fg_color="transparent")
    btn_wrap2.grid(row=5, column=0, pady=(0, 10))

    ctk.CTkButton(
        btn_wrap2,
        text="1 · Ei tea",
        command=ei_tea_kaart,
        font=("Montserrat SemiBold", 18),
        width=BTN_W,
        height=BTN_H,
        fg_color="#ffffff",
        text_color=ACCENT_MAIN,
        hover_color="#fdf1f7",
        border_width=BTN_BORDER,
        border_color=ACCENT_MAIN,
        corner_radius=20
    ).pack(side="left", padx=8)

    ctk.CTkButton(
        btn_wrap2,
        text="2 · Tean",
        command=tean_kaart,
        font=("Montserrat SemiBold", 18),
        width=BTN_W,
        height=BTN_H,
        fg_color=ACCENT_SOFT_BLUE,
        text_color=TEXT_DARK,
        hover_color="#9ec8ff",
        corner_radius=20
    ).pack(side="left", padx=8)

    # ---------- halda kaarte ----------
    manage_set_var = ctk.StringVar()
    manage_search_var = ctk.StringVar()
    manage_word_var = ctk.StringVar()
    manage_def_var = ctk.StringVar()

    halda_frame = ctk.CTkFrame(tab_halda, fg_color="transparent")
    halda_frame.pack(fill="both", expand=True, padx=10, pady=10)

    top_row = ctk.CTkFrame(halda_frame, fg_color="transparent")
    top_row.pack(fill="x", pady=(0, 10))

    ctk.CTkLabel(top_row, text="Set:", font=("Montserrat SemiBold", 18), text_color=TEXT_DARK).pack(side="left", padx=(0, 8))
    manage_set_combo = ctk.CTkComboBox(
        top_row, variable=manage_set_var, values=[], font=("Montserrat", 16),
        fg_color="#ffffff", border_color=ACCENT_MAIN,
        button_color=ACCENT_MAIN, button_hover_color=ACCENT_MAIN_DARK, corner_radius=12,
        command=lambda _=None: manage_laadi_kaardid()
    )
    manage_set_combo.pack(side="left", padx=(0, 16))

    ctk.CTkLabel(top_row, text="Otsi:", font=("Montserrat SemiBold", 18), text_color=TEXT_DARK).pack(side="left", padx=(0, 8))
    manage_search_entry = ctk.CTkEntry(
        top_row, textvariable=manage_search_var, font=("Montserrat", 16),
        fg_color="#ffffff", border_color=ACCENT_MAIN, border_width=1, corner_radius=12,
        width=260
    )
    manage_search_entry.pack(side="left")
    ctk.CTkButton(
        top_row, text="Otsi", command=manage_laadi_kaardid,
        font=("Montserrat SemiBold", 16), fg_color=ACCENT_MAIN, hover_color=ACCENT_MAIN_DARK, corner_radius=18
    ).pack(side="left", padx=10)

    mid = ctk.CTkFrame(halda_frame, fg_color="transparent")
    mid.pack(fill="both", expand=True)

    # vasak: list
    left = ctk.CTkFrame(mid, fg_color="transparent")
    left.pack(side="left", fill="both", expand=True, padx=(0, 10))

    ctk.CTkLabel(left, text="Kaardid:", font=("Montserrat SemiBold", 18), text_color=TEXT_DARK).pack(anchor="w")

    manage_listbox = tk.Listbox(left, height=16)
    manage_listbox.pack(fill="both", expand=True, pady=(6, 0))
    manage_listbox.bind("<<ListboxSelect>>", manage_vali_listist)

    # parem: edit
    right = ctk.CTkFrame(mid, fg_color="transparent")
    right.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(right, text="Muuda valitud kaarti:", font=("Montserrat SemiBold", 18), text_color=TEXT_DARK).pack(anchor="w")

    ctk.CTkLabel(right, text="Küsimus:", font=("Montserrat SemiBold", 16), text_color=TEXT_DARK).pack(anchor="w", pady=(10, 4))
    ctk.CTkEntry(
        right, textvariable=manage_word_var, font=("Montserrat", 16),
        fg_color="#ffffff", border_color=ACCENT_MAIN, border_width=1, corner_radius=12
    ).pack(fill="x")

    ctk.CTkLabel(right, text="Vastus:", font=("Montserrat SemiBold", 16), text_color=TEXT_DARK).pack(anchor="w", pady=(10, 4))
    ctk.CTkEntry(
        right, textvariable=manage_def_var, font=("Montserrat", 16),
        fg_color="#ffffff", border_color=ACCENT_MAIN, border_width=1, corner_radius=12
    ).pack(fill="x")

    manage_btns = ctk.CTkFrame(right, fg_color="transparent")
    manage_btns.pack(anchor="w", pady=(14, 0))

    ctk.CTkButton(
        manage_btns, text="Salvesta muudatus",
        command=manage_salvesta_muudatus,
        font=("Montserrat SemiBold", 16), fg_color=ACCENT_MAIN, hover_color=ACCENT_MAIN_DARK, corner_radius=18
    ).pack(side="left", padx=(0, 10))

    ctk.CTkButton(
        manage_btns, text="Kustuta kaart",
        command=manage_kustuta_valitud,
        font=("Montserrat SemiBold", 16), fg_color="#ffffff", text_color=ACCENT_MAIN,
        hover_color="#fdf1f7", border_width=2, border_color=ACCENT_MAIN, corner_radius=18
    ).pack(side="left")

    # ---------- raport ----------
    report_set_var = ctk.StringVar()

    report_frame = ctk.CTkFrame(tab_raport, fg_color="transparent")
    report_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(report_frame, text="Raport (HTML):", font=pealkiri_font, text_color=ACCENT_MAIN).pack(pady=(10, 6))
    ctk.CTkLabel(report_frame, text="Genereeri statistikaga raport ja salvesta failina.",
                 font=põhifont, text_color=TEXT_SOFT).pack(pady=(0, 20))

    report_set_combo = ctk.CTkComboBox(
        report_frame, variable=report_set_var, values=[], font=põhifont,
        fg_color="#ffffff", border_color=ACCENT_MAIN,
        button_color=ACCENT_MAIN, button_hover_color=ACCENT_MAIN_DARK, corner_radius=12,
        width=500
    )
    report_set_combo.pack(pady=(0, 16))

    ctk.CTkButton(
        report_frame, text="Salvesta raport (HTML)", command=export_report_html,
        font=suur_font, fg_color=ACCENT_SOFT_BLUE, hover_color="#9ec8ff",
        text_color=TEXT_DARK, corner_radius=20
    ).pack(pady=10)

    # ---------- mata ----------
    mata_frame = ctk.CTkFrame(tab_mata, fg_color="transparent")
    mata_frame.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(
        mata_frame,
        text="Kõrgem matemaatika I (alused)",
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
        command=hakka_oppima_mata
    )
    btn_hakka.pack(pady=10)

    # init
    taida_seti_valik()
    taida_manage_setid()
    taida_report_setid()
    uuenda_progress()
    schedule_gradient_redraw(gradient_canvas)

    root.mainloop()
    uhendus.close()
    # lõpp