import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import smtplib
from email.message import EmailMessage

# ---------- EMAIL CONFIG ----------
EMAIL_ADDRESS = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"

def send_email(to, subject, body):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to
        msg.set_content(body)

        with smtpllib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        print("Email error:", e)

# ---------- DATABASE ----------
conn = sqlite3.connect("clinic.db")
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER,
    date TEXT,
    time TEXT,
    FOREIGN KEY(patient_id) REFERENCES patients(id)
)''')
conn.commit()

# ---------- APP ----------
class ClinicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Clinic Appointment System")
        self.root.geometry("450x500")
        self.login_screen()

    def clear(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def login_screen(self):
        self.clear()
        tk.Label(self.root, text="Clinic Login", font=("Arial", 18)).pack(pady=10)

        tk.Label(self.root, text="Email").pack()
        self.email_entry = tk.Entry(self.root)
        self.email_entry.pack()

        tk.Label(self.root, text="Password").pack()
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.pack()

        tk.Button(self.root, text="Login", command=self.login).pack(pady=10)
        tk.Button(self.root, text="Register", command=self.register_screen).pack()

        # Admin login
        tk.Label(self.root, text="(Type 'admin@clinic.com' to login as admin)").pack(pady=10)

    def register_screen(self):
        self.clear()
        tk.Label(self.root, text="Patient Registration", font=("Arial", 18)).pack(pady=10)

        self.reg_name = tk.Entry(self.root)
        self.reg_email = tk.Entry(self.root)
        self.reg_pass = tk.Entry(self.root, show="*")

        for label, entry in [("Name", self.reg_name), ("Email", self.reg_email), ("Password", self.reg_pass)]:
            tk.Label(self.root, text=label).pack()
            entry.pack()

        tk.Button(self.root, text="Register", command=self.register).pack(pady=10)
        tk.Button(self.root, text="Back to Login", command=self.login_screen).pack()

    def register(self):
        name = self.reg_name.get()
        email = self.reg_email.get()
        password = self.reg_pass.get()

        if not (name and email and password):
            messagebox.showerror("Error", "All fields required.")
            return

        try:
            c.execute("INSERT INTO patients (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            messagebox.showinfo("Success", "Registration successful!")
            self.login_screen()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Email already registered.")

    def login(self):
        email = self.email_entry.get()
        password = self.password_entry.get()

        if email == "admin@clinic.com" and password == "admin":
            self.admin_dashboard()
            return

        c.execute("SELECT id, name FROM patients WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        if user:
            self.user_id, self.user_name, self.user_email = user[0], user[1], email
            self.patient_dashboard()
        else:
            messagebox.showerror("Error", "Invalid credentials.")

    def patient_dashboard(self):
        self.clear()
        tk.Label(self.root, text=f"Welcome, {self.user_name}", font=("Arial", 16)).pack(pady=10)

        tk.Label(self.root, text="Available Time Slots").pack()
        self.slot_var = tk.StringVar()
        slots = ["09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "02:00 PM", "03:00 PM"]
        self.slot_box = ttk.Combobox(self.root, textvariable=self.slot_var, values=slots)
        self.slot_box.pack()

        tk.Button(self.root, text="Book Appointment", command=self.book_slot).pack(pady=5)
        tk.Button(self.root, text="Cancel Appointment", command=self.cancel_slot).pack(pady=5)
        tk.Button(self.root, text="Logout", command=self.login_screen).pack(pady=5)

        # Show current appointment
        c.execute("SELECT time FROM appointments WHERE patient_id=? AND date=DATE('now')", (self.user_id,))
        result = c.fetchone()
        if result:
            tk.Label(self.root, text=f"Your appointment today: {result[0]}").pack(pady=10)

    def book_slot(self):
        time = self.slot_var.get()
        if not time:
            messagebox.showerror("Error", "Select a time slot.")
            return

        # Check if slot is taken
        c.execute("SELECT * FROM appointments WHERE date=DATE('now') AND time=?", (time,))
        if c.fetchone():
            messagebox.showerror("Error", "Slot already taken.")
            return

        # Check if user already has appointment
        c.execute("SELECT * FROM appointments WHERE patient_id=? AND date=DATE('now')", (self.user_id,))
        if c.fetchone():
            messagebox.showerror("Error", "You already have an appointment today.")
            return

        c.execute("INSERT INTO appointments (patient_id, date, time) VALUES (?, DATE('now'), ?)", (self.user_id, time))
        conn.commit()

        send_email(self.user_email, "Clinic Appointment", f"Hi {self.user_name}, your appointment is at {time} today.")
        messagebox.showinfo("Booked", "Appointment booked and email sent.")
        self.patient_dashboard()

    def cancel_slot(self):
        c.execute("DELETE FROM appointments WHERE patient_id=? AND date=DATE('now')", (self.user_id,))
        conn.commit()
        messagebox.showinfo("Canceled", "Appointment cancelled.")
        self.patient_dashboard()

    def admin_dashboard(self):
        self.clear()
        tk.Label(self.root, text="Admin Panel", font=("Arial", 18)).pack(pady=10)

        self.tree = ttk.Treeview(self.root, columns=("Name", "Time"), show='headings')
        self.tree.heading("Name", text="Patient Name")
        self.tree.heading("Time", text="Time Slot")
        self.tree.pack()

        c.execute('''SELECT patients.name, appointments.time 
                     FROM appointments JOIN patients ON appointments.patient_id = patients.id 
                     WHERE date=DATE('now') ORDER BY time''')
        for row in c.fetchall():
            self.tree.insert('', 'end', values=row)

        tk.Button(self.root, text="Refresh", command=self.admin_dashboard).pack(pady=5)
        tk.Button(self.root, text="Logout", command=self.login_screen).pack()

# --------- RUN APP ---------
root = tk.Tk()
app = ClinicApp(root)
root.mainloop()
