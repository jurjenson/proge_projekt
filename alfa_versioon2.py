import sqlite3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from ttkbootstrap import Style

def loo_tabelid(uhendus):
    kursor = uhendus.cursor()
    
    kursor.execute('''
        CREATE TABLE IF NOT EXISTS flashcard_sets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL
        )
    ''')

    # Flashcard tabel loomine
    
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


# Funktsioon et lisada kaart database

def lisa_kaart(uhendus, seti_id, sona, definitsioon):
    kursor = uhendus.cursor()

    kursor.execute('''
        INSERT INTO flashcards (set_id, word, definition)
        VALUES (?, ?, ?)
    ''', (seti_id, sona, definitsioon))

    kaardi_id = kursor.lastrowid
    uhendus.commit()

    return kaardi_id

# Funktsioon kaartide saamiseks datast 

def saa_setid(uhendus):
    kursor = uhendus.cursor()

    kursor.execute('''
        SELECT id, name FROM flashcard_sets
    ''')

    read = kursor.fetchall()
    setid = {rida[1]: rida[0] for rida in read }   # Setide dictionary phmt

    return setid


# Funktsioon et saada kaardid spets setist

def saa_kaardid(uhendus, seti_id):
    kursor = uhendus.cursor()

    kursor.execute('''  
        SELECT word, definition FROM flashcards
        WHERE set_id = ?
    ''', (seti_id,))

    read = kursor.fetchall()
    kaardid = [(rida[0], rida[1]) for rida in read] # Tee kaartidest loetelu
    return kaardid

def kustuta_set(uhendus, seti_id):
    kursor = uhendus.cursor()

    kursor.execute('''
        DELETE FROM flashcard_sets
        WHERE id = ?
    ''', (seti_id,))

    uhendus.commit()
    seti_valik.set('')
    clear_kaardid()
    taida_seti_valik()

    global aktiivsed_kaardid, kaardi_indeks
    aktiivsed_kaardid = []
    kaardi_indeks = 0


# Funktsioon setide loomiseks
def loo_set():
    seti_nimi = seti_nimi_var.get()
    if seti_nimi:
        if seti_nimi not in saa_setid(uhendus):
            seti_id = lisa_set(uhendus, seti_nimi)
            taida_seti_valik()
            seti_nimi_var.set('')

            seti_nimi_var.set('')
            sona_var.set('')
            definitsioon_var.set('')

def lisa_sona():
    seti_nimi = seti_nimi_var.get()
    sona = sona_var.get()
    definitsioon = definitsioon_var.get()

    if seti_nimi and sona and definitsioon:
        if seti_nimi not in saa_setid(uhendus):
            seti_id = lisa_set(uhendus, seti_nimi)
        else:
            seti_id = saa_setid(uhendus)[seti_nimi]
        
        lisa_kaart(uhendus, seti_id, sona, definitsioon)

        sona_var.set('')
        definitsioon_var.set('')

        taida_seti_valik()


# Funktsioon setide comboboxi täitmiseks

def taida_seti_valik():
    seti_valik['values'] = tuple(saa_setid(uhendus).keys())

# Funktsioon kustutamiseks seti

def kustuta_valitud_set():
    seti_nimi = seti_valik.get()

    if seti_nimi:
        tulemus = messagebox.askyesno(
            'Kinnitus', f'Kas oled kindel, et soovid valitud seti {seti_nimi} kustutada?'
        )

        if tulemus == tk.YES:
            seti_id = saa_setid(uhendus)[seti_nimi]
            kustuta_set(uhendus, seti_id)
            taida_seti_valik()
            clear_kaardid()       

def vali_set():
    seti_nimi = seti_valik.get()

    if seti_nimi:
        seti_id = saa_setid(uhendus)[seti_nimi]
        kaardid = saa_kaardid(uhendus, seti_id)

        if kaardid:
            kuva_kaardid(kaardid)
        else:
            sona_silt.config(text='Selles setis pole flashcarde')
            definitsiooni_silt.config(text='')
    else:
        global aktiivsed_kaardid, kaardi_indeks
        aktiivsed_kaardid = []
        kaardi_indeks = 0
        clear_kaardid()


def kuva_kaardid(kaardid):
    global kaardi_indeks
    global aktiivsed_kaardid

    kaardi_indeks = 0
    aktiivsed_kaardid = kaardid

    if not kaardid:
        clear_kaardid()
    else:
        naita_kaart

    naita_kaart()

def clear_kaardid():
    sona_silt.config(text='')
    definitsiooni_silt.config(text='')

def naita_kaart():
    global kaardi_indeks
    global aktiivsed_kaardid

    if aktiivsed_kaardid:
        if 0 <= kaardi_indeks < len(aktiivsed_kaardid):
            sona, _ = aktiivsed_kaardid[kaardi_indeks]
            sona_silt.config(text=sona)
            definitsiooni_silt.config(text='')
        else:
            clear_kaardid()

    else:
        clear_kaardid()

# Funktsioon kaardi flippimiseks

def pööra_kaart():
    global kaardi_indeks
    global aktiivsed_kaardid

    if aktiivsed_kaardid:
        _, definitsioon = aktiivsed_kaardid[kaardi_indeks]
        definitsiooni_silt.config(text=definitsioon)

# Funktsioon kaardi liigutamiseks edasi

def järgmine_kaart():
    global kaardi_indeks
    global aktiivsed_kaardid

    if aktiivsed_kaardid:
        kaardi_indeks = min(kaardi_indeks + 1, len(aktiivsed_kaardid) -1)
        naita_kaart()


def eelmine_kaart():
    global kaardi_indeks
    global aktiivsed_kaardid

    if aktiivsed_kaardid:
        kaardi_indeks = max(kaardi_indeks - 1, 0)
        naita_kaart()

if __name__ == '__main__':
    
    uhendus = sqlite3.connect('flashcards.db')
    loo_tabelid(uhendus)
    
    # Main
    root = tk.Tk()
    root.title('Kaardid')
    root.geometry('800x600')
    
    #Stiili elemendid

    stiil = Style(theme='journal')
    stiil.configure('TLabel', font=('TkDefaultFont',20 ))
    stiil.configure('TButton', font=('TkDefaultFont',18 ))

    seti_nimi_var = tk.StringVar()
    sona_var = tk.StringVar()
    definitsioon_var = tk.StringVar()
    
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)
    
    loo_set_raam = ttk.Frame(notebook)
    notebook.add(loo_set_raam, text="Loo set")

    # Kõrge matemaatika alused tab 
    mata_tab = ttk.Frame(notebook)  
    notebook.add(mata_tab, text="Kõrge matemaatika alused")

    # Siin saad lisada sisu, näiteks labelid või nupud
    ttk.Label(mata_tab, text="Tere tulemast kõrge matemaatika alustesse!", font=('TkDefaultFont', 18)).pack(padx=10, pady=20)

    # Näide nuppudest või interaktiivsetest elementidest
    ttk.Button(mata_tab, text="Hakkame õppima").pack(padx=10, pady=10)

    
    #Widgetid seti nime, küsimuse ja vastuseks
    
    ttk.Label(loo_set_raam, text='Loo nimi:').pack(padx=5, pady=5)
    ttk.Entry(loo_set_raam, textvariable=seti_nimi_var, width=30).pack(padx=5, pady=5)
    
    ttk.Label(loo_set_raam, text='Küsimus:').pack(padx=5, pady=5)
    ttk.Entry(loo_set_raam, textvariable=sona_var, width=30).pack(padx=5, pady=5)

    ttk.Label(loo_set_raam, text='Vastus:').pack(padx=5, pady=5)
    ttk.Entry(loo_set_raam, textvariable=definitsioon_var, width=30).pack(padx=5, pady=5)
    
    # Nupp lisamiseks
    
    ttk.Button(loo_set_raam, text="Lisa küsimus", command=lisa_sona).pack(padx=5, pady=10)
    
    # Nupp salvestamiseks
    
    ttk.Button(loo_set_raam, text="Salvesta set", command=loo_set).pack(padx=5, pady=10)
    
    vali_set_raam = ttk.Frame(notebook)
    notebook.add(vali_set_raam, text='Vali set')
    
    # Combobox widget, et valida flashcard sete
    
    seti_valik = ttk.Combobox(vali_set_raam, state='readonly')
    seti_valik.pack(padx=5, pady=40)
    
    # Nupp, et valida set
    
    ttk.Button(vali_set_raam, text='Vali set', command=vali_set).pack(padx=5, pady=5)
    
    # Nupp, et kustutada set
    
    ttk.Button(vali_set_raam, text='Kustuta', command=kustuta_valitud_set).pack(padx=5, pady=5)

    # Õppimise tab
    
    õpi_raam = ttk.Frame(notebook)
    notebook.add(õpi_raam, text='Õpime')
    
    # Progress tracking
    
    kaardi_indeks = 0
    vahekaardid  = []
    
    # word display kaartidel
    sona_silt = ttk.Label(õpi_raam, text='', font=('TkDefaultFont', 24))
    sona_silt.pack(padx=5, pady=40)
    
    # definiton display kaartidel
    
    definitsiooni_silt = ttk.Label(õpi_raam, text='')
    definitsiooni_silt.pack(padx=5, pady=5)
    
    # Nupp, et vahetada kaardi pooli
    
    ttk.Button(õpi_raam, text='Flip', command=pööra_kaart).pack(side='left', padx=5, pady=5)

    # Nupp, et vaadata järgmist kaarti
    
    ttk.Button(õpi_raam, text='Järgmine', command=järgmine_kaart).pack(side ='right', padx=5, pady=5)

    # Nupp, et vaadata eelmist kaarti
    
    ttk.Button(õpi_raam, text='Eelmine', command=eelmine_kaart).pack(side ='right', padx=5, pady=5)
    
    
    taida_seti_valik()
    
    root.mainloop()
