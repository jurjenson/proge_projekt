# Õppekaardid (Flashcards App)

## Autorid
- Annabel Jürjenson
- Minna Marie Kask

## Ülevaade
See projekt on **graafiline õppekaartide rakendus**, mis võimaldab kasutajal luua, hallata ja õppida õppekaarte (küsimus–vastus formaadis).  
Rakendus on loodud Pythonis, kasutades **CustomTkinterit** kasutajaliidese jaoks ja **SQLite’i** andmete püsivaks salvestamiseks.

Projekt on mõeldud õppimise toetamiseks ning sisaldab lihtsat **spaced repetition** loogikat, statistika kogumist ja andmete importi/eksporti.

---

## Funktsionaalsus

### Setid ja kaardid
- Seti (komplekti) loomine
- Küsimuste ja vastuste lisamine setti
- Seti kustutamine koos kaartidega
- Kaartide muutmine ja kustututamine eraldi haldusvaates

### Õppimisrežiim
- Kaartide läbivaatamine (küsimus / vastus)
- Nupud: **Tean** / **Ei tea**
- Lihtne spaced repetition:
  - „Ei tea“ → kaart liigub listi lõppu ja tuleb uuesti ette
- Kaartide segamine (shuffle)
- Sessiooni taimer
- Progressiriba (mitmes kaart / mitu kokku)

### Statistika (SQLite)
Iga kaardi kohta salvestatakse:
- mitu korda nähtud
- mitu korda vastatud õigesti
- mitu korda vastatud valesti
- viimase vaatamise aeg
- viimane tulemus (correct / wrong)

### Import / Export
- **JSON import/export**
- **CSV import/export**
- Toetab mitut formaati (nt `küsimus/vastus` ja `question/answer`)
- Seti nimi tuletatakse vajadusel failinimest

### Raport
- HTML-raporti genereerimine
- Sisaldab:
  - kokkuvõtet
  - iga kaardi statistikat tabelina
- Sobib avamiseks brauseris või esitamiseks aruandena

### Lisakomplekt
- Eraldi vaheleht **„Kõrgem matemaatika I“**, kus kaardid laetakse JSON-failist
- Neid kaarte ei salvestata andmebaasi statistikaga (sessioonipõhine õppimine)

---

## Kasutatud tehnoloogiad ja materjalid

- **Python 3**
- **CustomTkinter** – graafiline kasutajaliides
- **Tkinter** – lisakomponendid (Canvas, Listbox)
- **SQLite3** – lokaalne andmebaas
- **JSON / CSV** – andmete import ja eksport
- **HTML / CSS** – raporti genereerimine
- **ChatGPT** - abiline koodi kirjutamisel ja parandamisel
- Samuti on kasutusel ka teistest sarnastest projektidest võetud inspiratsioon

---

## Projekti struktuur 

- **Andmebaasi kiht**
  - tabelite loomine
  - migratsioon (statistikaväljade lisamine)
  - CRUD-operatsioonid kaartide ja settide jaoks

- **Loogika**
  - õppimisrežiim
  - spaced repetition
  - statistika märkimine
  - import/export

- **Kasutajaliides**
  - vahelehed (tabs)
  - õppimisvaade
  - haldusvaade
  - raportivaade
  - visuaalne gradient-taust

---

## Käivitamine

1. Veendu, et Python 3 on paigaldatud
2. Lae endale alla Montserrat ttf. fail.
3. Paigalda vajalikud teegid:
   ```bash
   pip install customtkinter
   ```
4. Käivita programm:
   ```bash
   python main.py
   ```
5. Andmebaas luuakse automaatselt programmi käivitamisel
