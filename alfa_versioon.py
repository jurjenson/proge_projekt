import sqlite3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from ttkbootstrap import Style

def create_tables(conn):
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flashcards_sets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL
        
        )
    ''')


    # Flashcard tabel loomine
    
    cursor.execute('''s
        CREATE TABLE IF NOT EXISTS flashcards_sets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  set_id INTEGER NOT NULL,
                  word TEXT NOT NULL,
                  definition NOT NULL,
                  FOREIGN KEY (set_id) REFERENCES flashcard_sets(id)
        
        )
    ''')

def add_set(conn, name):
    cursor = conn.sursor()
    
    cursor.execute('''
        INSERT INTO flashcards_sets (name)
        VALUES (?)
        
    ''', (name, ))
    
    set_id = cursor.lastrowid
    conn.commit()
    
    return set_id


# Funktsioon et lisada kaart database

def add_card(conn, set_id, word, definition):
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO flashcards (set_id, word, definition)
        VALUES (?, ?, ?)
    ''', (set_id, word, definition))

    card_id = cursor.lastrowid
    conn.commit()

    return card_id

# Funktsioon kaartide saamiseks datast 

def get_sets(conn):
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, name FROM flashcard_sets
    ''')

    rows = cursor.fetchall()
    sets = {row[1]: row[0] for row in rows }   # Setide dictionary phmt

    return sets


# Funktsioon et saada kaardid spets setist

def get_cards(conn, set_id):
    cursor = conn.cursor

    cursor.execute('''
                   
        SELECT word, definition FROM flashcards
        WHERE set_id = ?
    ''', (set_id,))

    rows = cursor.fetchall()
    cards = [(row[0], row[1]) for row in rows] # Tee kaartidest loetelu

def delete_cards(conn, set_id):
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM flashcards_sets
        WHERE id = ?
    ''', (set_id))

    conn.commit()
    sets_combobox.set('')
    clear_flashcard_display()
    populate_sets_combobox()

    global current_cards, card_index
    current_cards = []
    card_index = 0


# Funktsioon setide loomiseks
def create_set():
    set_name = set_name_var
    if set_name:
        if set_name not in get_sets(conn):
            set_id = add_set(conn, set_name)
            populate_sets_combobox()
            set_name_var.set()


            set_name_var.set('')
            word_var.set('')
            definition_var('')

def add_word():
    set_name = set_name_var.get()
    word = word_var.get()
    definition = definition_var.get()

    if set_name and word and definition:
        if set_name not in get_sets(conn):
            set_id = add_set(conn. set_name)
        else:
            set_id = get_sets(conn)[set_name]

        populate_sets_combobox()







def populate_sets_combobox():
    sets_combobox['values'] = tuple(get_sets(conn).keys())

# Funktsioon kustutamiseks seti

def delete_selected_set():
    set_name = sets_combobox.get()

    if set_name:
        result = messagebox.askyesno(
            'Kinnitus', f'Kas oled kindel, et soovid valitud seti {set_name} kustutada?'
        )

        if result == tk.YES:
            set_id = get_sets(conn)[set_name]
            delete_set(conn, set_id)
            populate_sets_combobox()
            clear_flashcard_display()       

def select_set():
    set_name = sets_combobox.get()

    if set_name:
        set_id = get_sets(conn)[set_name]
        cards = get_cards(conn, set_id)

        if cards:
            display_flashcards(cards)
        else:
            word_label.config(text='Selles setis pole flashcarde')
            definiton_label.config(text='')
    else:
        global current_cards, card_index
        current_cards = []
        card_index = 0
        clear_flashcard_display()


def display_flashcards(cards):
    global card_index
    global current_cards

    card_index = 0
    current_cards = cards

    if not cards:
        clear_flashcard_display()
    else:
        show_card

    show_card()

def clear_flashcard_display():
    word_label.config(text='')
    definiton_label.config(text='')




def show_card():
    global card_index
    global current_cards

    if current_cards:
        if 0 <= card_index < len(current_cards):
            word, _ = current_cards[card_index]
            word_label.config(text='')
            definiton_label.config(text='')
        else:
            clear_flashcard_display()

    else:
        clear_flashcard_display()

# Funktsioon kaardi flippimiseks

def flip_card():
    global card_index
    global current_cards

    if current_cards:
        _, definition = current_cards[card_index]
        definiton_label.config(text=definition)

# Funktsioon kaardi liigutamiseks edasi

def next_card():
    global card_index
    global current_cards

    if current_cards:
        card_index = min(card_index + 1, len(current_cards) -1)
        show_card()


def prev_card():
    global card_index
    global current_cards

    if current_cards:
        card_index = max(card_index - 1, 0)
        show_card()

if __name__ == '__main__':
    
    conn = sqlite3.connect('flashcards.db')
    create_tables(conn)
    
    # Main
    root = tk.Tk()
    root.title('Flashcards app')
    root.geometry('500x400')
    
    #Stiili elemendid

    style = Style(theme='journal')
    style.configure('TLabel', font=('TkDefaultFont',18 ))
    style.configure('TButton', font=('TkDefaultFont',16 ))

    set_name_var = tk.StringVar()
    word_var = tk.StringVar()
    definition_var = tk.StringVar()
    
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)
    
    create_set_frame = ttk.Frame(notebook)
    notebook.add(create_set_frame, text="Loo set")
    
    #Widgetid seti nime, küsimuse ja vastuseks
    
    ttk.Label(create_set_frame, text='Loo nimi:').pack(padx=5, pady=5)
    ttk.Entry(create_set_frame, textvariable=set_name_var, width=30).pack(padx=5, pady=5)
    
    ttk.Label(create_set_frame, text='Küsimus:').pack(padx=5, pady=5)
    ttk.Entry(create_set_frame, textvariable=word_var, width=30).pack(padx=5, pady=5)

    ttk.Label(create_set_frame, text='Vastus:').pack(padx=5, pady=5)
    ttk.Entry(create_set_frame, textvariable=definition_var, width=30).pack(padx=5, pady=5)
    
    # Nupp lisamiseks
    
    ttk.Button(create_set_frame, text="Lisa küsimus", command=add_word).pack(padx=5, pady=10)
    
    # Nupp salvestamiseks
    
    ttk.Button(create_set_frame, text="Salvesta set", command=create_set).pack(padx=5, pady=10)
    
    select_set_frame = ttk.Frame(notebook)
    notebook.add(select_set_frame, text='Vali set')
    
    # Combobox widget, et valida flashcard sete
    
    sets_combobox = ttk.Combobox(select_set_frame, state='readonly')
    sets_combobox.pack(padx=5, pady=40)
    
    # Nupp, et valida set
    
    ttk.Button(select_set_frame, text='Vali set', command=select_set).pack(padx=5, pady=5)
    
    # Nupp, et kustutada set
    
    ttk.Button(select_set_frame, text='Kustuta', command=delete_selected_set).pack(padx=5, pady=5)

    # Õppimise tab
    
    flashcards_frame = ttk.Frame(notebook)
    notebook.add(flashcards_frame, text='Õpime')
    
    # Progress tracking
    
    card_index = 0
    tabs  = []
    
    # word display kaartidel
    word_label = ttk.Label(flashcards_frame, text='', font=('TkDefaultFont', 24))
    word_label.pack(padx=5, pady=40)
    
    # definiton display kaartidel
    
    definiton_label = ttk.Label(flashcards_frame, text='')
    definiton_label.pack(padx=5, pady=5)
    
    # Nupp, et vahetada kaardi pooli
    
    ttk.Button(flashcards_frame, text='Flip', command=flip_card).pack(side='left', padx=5, pady=5)

    # Nupp, et vaadata järgmist kaarti
    
    ttk.Button(flashcards_frame, text='Järgmine', command=next_card).pack(side ='right', padx=5, pady=5)


    # Nupp, et vaadata eelmist kaarti
    
    ttk.Button(flashcards_frame, text='Eelmine', command=prev_card).pack(side ='right', padx=5, pady=5)
    
    
    populate_sets_combobox()
    
    root.mainloop()