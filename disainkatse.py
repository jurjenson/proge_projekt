from tkinter import *

root = Tk()
root.title("KM I alused")
root.config(bg="thistle3")

label = Label(root, text='KM I alused kordamine', font=("Times New Roman", 18))
label.config(bg="thistle3")
label.pack()

#uus frame
frame = Frame(root, width=800, height=500)
frame.config(bg="thistle")
frame.pack(fill="both", expand=True, padx=10, pady=10)
frame.pack_propagate(False)

frame_label = Label(frame, text = "Siia ilmuvad ülesanded blablabla", font=("Times New Roman", 12), bg="thistle")
frame_label.pack(side="top", pady=10)


root.mainloop()