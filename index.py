import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import os
import sqlite3
import json
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path="project_organizer.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """إنشاء قاعدة البيانات والجداول"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # جدول الهياكل الأساسية
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS structures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                base_path TEXT NOT NULL,
                structure_data TEXT NOT NULL,
                created_date TEXT NOT NULL,
                last_modified TEXT NOT NULL
            )
        ''')

        # جدول العملاء
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                folder_path TEXT UNIQUE NOT NULL,
                structure_id INTEGER,
                created_date TEXT NOT NULL,
                FOREIGN KEY (structure_id) REFERENCES structures (id)
            )
        ''')

        # جدول المشاريع
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                project_number TEXT UNIQUE NOT NULL,
                client_id INTEGER,
                folder_path TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'نشط',
                created_date TEXT NOT NULL,
                last_modified TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        ''')

        # جدول الملفات المولدة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                project_id INTEGER,
                file_type TEXT NOT NULL,
                created_date TEXT NOT NULL,
                file_path TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')

        # جدول الإعدادات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def add_structure(self, name, base_path, structure_data):
        """إضافة هيكل جديد"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO structures (name, base_path, structure_data, created_date, last_modified)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, base_path, json.dumps(structure_data), current_time, current_time))

            structure_id = cursor.lastrowid
            conn.commit()
            return structure_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_structures(self):
        """الحصول على جميع الهياكل"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM structures ORDER BY created_date DESC')
        structures = cursor.fetchall()
        conn.close()

        return structures

    def add_client(self, name, client_type, folder_path, structure_id):
        """إضافة عميل جديد"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO clients (name, type, folder_path, structure_id, created_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, client_type, folder_path, structure_id, current_time))

            client_id = cursor.lastrowid
            conn.commit()
            return client_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_clients(self, structure_id=None):
        """الحصول على العملاء"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if structure_id:
            cursor.execute('SELECT * FROM clients WHERE structure_id = ? ORDER BY created_date DESC', (structure_id,))
        else:
            cursor.execute('SELECT * FROM clients ORDER BY created_date DESC')

        clients = cursor.fetchall()
        conn.close()

        return clients

    def add_project(self, name, project_number, client_id, folder_path, description=""):
        """إضافة مشروع جديد"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO projects (name, project_number, client_id, folder_path, created_date, last_modified, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, project_number, client_id, folder_path, current_time, current_time, description))

            project_id = cursor.lastrowid
            conn.commit()
            return project_id
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_projects(self, client_id=None):
        """الحصول على المشاريع"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if client_id:
            cursor.execute('''
                SELECT p.*, c.name as client_name, c.type as client_type
                FROM projects p
                JOIN clients c ON p.client_id = c.id
                WHERE p.client_id = ?
                ORDER BY p.created_date DESC
            ''', (client_id,))
        else:
            cursor.execute('''
                SELECT p.*, c.name as client_name, c.type as client_type
                FROM projects p
                JOIN clients c ON p.client_id = c.id
                ORDER BY p.created_date DESC
            ''')

        projects = cursor.fetchall()
        conn.close()

        return projects

    def check_project_exists(self, project_number):
        """التحقق من وجود المشروع"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM projects WHERE project_number = ?', (project_number,))
        result = cursor.fetchone()
        conn.close()

        return result is not None

    def check_client_exists(self, name, structure_id):
        """التحقق من وجود العميل"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM clients WHERE name = ? AND structure_id = ?', (name, structure_id))
        result = cursor.fetchone()
        conn.close()

        return result

    def add_generated_file(self, filename, project_id, file_type, file_path=""):
        """إضافة ملف مولد"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        current_time = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO generated_files (filename, project_id, file_type, created_date, file_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (filename, project_id, file_type, current_time, file_path))

        conn.commit()
        conn.close()

class ProjectOrganizer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🗂️ منظم المشاريع الاحترافي - الإصدار الذكي")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')

        # إنشاء مدير قاعدة البيانات
        self.db = DatabaseManager()

        # متغيرات عامة
        self.selected_path = tk.StringVar()
        self.current_structure_id = None

        self.create_main_interface()

    def create_main_interface(self):
        """إنشاء الواجهة الرئيسية"""
        # العنوان الرئيسي
        title_frame = tk.Frame(self.root, bg='#f0f0f0')
        title_frame.pack(pady=20)

        tk.Label(title_frame, text=" منظم المشاريع الاحترافي",
                font=("Arial", 20, "bold"), bg='#f0f0f0').pack()
        tk.Label(title_frame, text="نظام شامل لتنظيم وإدارة المشاريع والملفات",
                font=("Arial", 12), bg='#f0f0f0', fg='#666').pack()

        # إطار الأزرار الرئيسية
        buttons_frame = tk.Frame(self.root, bg='#f0f0f0')
        buttons_frame.pack(pady=30)

        # زر إنشاء الهيكل الكامل
        tk.Button(buttons_frame, text="🏗️ إنشاء الهيكل الكامل للمشاريع",
                 command=self.create_full_structure_window,
                 font=("Arial", 14), bg='#4CAF50', fg='white',
                 width=30, height=2).pack(pady=10)

        # زر إنشاء مشروع جديد
        tk.Button(buttons_frame, text="📁 إنشاء مشروع جديد",
                 command=self.create_new_project_window,
                 font=("Arial", 14), bg='#2196F3', fg='white',
                 width=30, height=2).pack(pady=10)

        # زر توليد أسماء الملفات
        tk.Button(buttons_frame, text="� مولّد أسماء الملفات",
                 command=self.create_filename_generator_window,
                 font=("Arial", 14), bg='#FF9800', fg='white',
                 width=30, height=2).pack(pady=10)

        # زر الخروج
        tk.Button(buttons_frame, text="❌ خروج",
                 command=self.root.quit,
                 font=("Arial", 12), bg='#f44336', fg='white',
                 width=30, height=1).pack(pady=20)

    def create_full_structure_window(self):
        """نافذة إنشاء الهيكل الكامل"""
        structure_window = tk.Toplevel(self.root)
        structure_window.title("🏗️ إنشاء الهيكل الكامل للمشاريع")
        structure_window.geometry("600x400")
        structure_window.configure(bg='#f0f0f0')

        # العنوان
        tk.Label(structure_window, text="🏗️ إنشاء الهيكل الكامل للمشاريع",
                font=("Arial", 16, "bold"), bg='#f0f0f0').pack(pady=20)

        # اختيار المسار
        path_frame = tk.Frame(structure_window, bg='#f0f0f0')
        path_frame.pack(pady=20, padx=20, fill='x')

        tk.Label(path_frame, text="� اختر المسار لإنشاء الهيكل:",
                font=("Arial", 12), bg='#f0f0f0').pack(anchor='w')

        path_entry_frame = tk.Frame(path_frame, bg='#f0f0f0')
        path_entry_frame.pack(fill='x', pady=5)

        path_entry = tk.Entry(path_entry_frame, textvariable=self.selected_path,
                             font=("Arial", 10), width=50)
        path_entry.pack(side='left', fill='x', expand=True)

        tk.Button(path_entry_frame, text="تصفح",
                 command=lambda: self.browse_folder(self.selected_path),
                 bg='#2196F3', fg='white').pack(side='right', padx=(5,0))

        # معلومات الهيكل
        info_frame = tk.Frame(structure_window, bg='#f0f0f0')
        info_frame.pack(pady=20, padx=20, fill='both', expand=True)

        tk.Label(info_frame, text="📋 سيتم إنشاء الهيكل التالي:",
                font=("Arial", 12, "bold"), bg='#f0f0f0').pack(anchor='w')

        # قائمة المجلدات الرئيسية
        structure_text = tk.Text(info_frame, height=10, width=60,
                               font=("Courier", 9), bg='#fff')
        structure_text.pack(pady=10, fill='both', expand=True)

        structure_info = """📁 00_Inbox_صندوق_الوارد/
📁 10_Work_&_Study_العمل_والدراسة/
   📁 11_Clients_العملاء/
   📁 12_University_الجامعة/
📁 20_Knowledge_Base_قاعدة_المعرفة/
   📁 21_Courses_الكورسات/
   📁 22_Tutorials_شروحاتي/
   📁 23_Resources_الموارد/
   📁 24_Portfolio_نماذج_الأعمال/
📁 30_Admin_&_Finance_الإدارة_والمالية/
   📁 31_Invoices_الفواتير/
   📁 32_Proposals_&_Contracts/
   📁 33_Receipts_الإيصالات/
   📁 34_Reports_تقارير_مالية/
📁 40_Personal_شخصي/
📁 99_Archive_الأرشيف/"""

        structure_text.insert('1.0', structure_info)
        structure_text.config(state='disabled')

        # زر الإنشاء
        tk.Button(structure_window, text="� إنشاء الهيكل الكامل",
                 command=lambda: self.create_full_structure(structure_window),
                 font=("Arial", 14), bg='#4CAF50', fg='white',
                 width=25, height=2).pack(pady=20)

    def browse_folder(self, path_var):
        """تصفح واختيار مجلد"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            path_var.set(folder_path)

    def create_full_structure(self, window):
        """إنشاء الهيكل الكامل للمجلدات"""
        if not self.selected_path.get():
            messagebox.showerror("خطأ", "يرجى اختيار مسار لإنشاء الهيكل")
            return

        base_path = self.selected_path.get()

        # هيكل المجلدات الكامل
        folder_structure = {
            "00_Inbox_صندوق_الوارد": [],
            "10_Work_&_Study_العمل_والدراسة": {
                "11_Clients_العملاء": [],
                "12_University_الجامعة": []
            },
            "20_Knowledge_Base_قاعدة_المعرفة": {
                "21_Courses_الكورسات": ["2023", "2024"],
                "22_Tutorials_شروحاتي": ["01_Scripts_&_Notes", "02_Final_Videos"],
                "23_Resources_الموارد": [
                    "Books_&_Articles", "Code_Snippets", "Stock_Media",
                    "Templates_القوالب", "Software_&_Tools"
                ],
                "24_Portfolio_نماذج_الأعمال": ["Web", "Apps", "Graphics"]
            },
            "30_Admin_&_Finance_الإدارة_والمالية": {
                "31_Invoices_الفواتير": ["2023", "2024"],
                "32_Proposals_&_Contracts": [],
                "33_Receipts_الإيصالات": [],
                "34_Reports_تقارير_مالية": []
            },
            "40_Personal_شخصي": [
                "CV_&_CoverLetters", "ID_&_Documents",
                "Goals_&_Planning", "Personal_Projects"
            ],
            "99_Archive_الأرشيف": {
                "Work_Archive": ["2023"],
                "Study_Archive": ["2022"]
            }
        }

        try:
            self._create_folders_recursive(base_path, folder_structure)
            messagebox.showinfo("نجح", f"تم إنشاء الهيكل الكامل بنجاح في:\n{base_path}")
            window.destroy()
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء إنشاء الهيكل:\n{str(e)}")

    def _create_folders_recursive(self, base_path, structure):
        """إنشاء المجلدات بشكل تكراري"""
        for folder_name, subfolders in structure.items():
            folder_path = os.path.join(base_path, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            if isinstance(subfolders, dict):
                self._create_folders_recursive(folder_path, subfolders)
            elif isinstance(subfolders, list):
                for subfolder in subfolders:
                    subfolder_path = os.path.join(folder_path, subfolder)
                    os.makedirs(subfolder_path, exist_ok=True)

    def create_new_project_window(self):
        """نافذة إنشاء مشروع جديد"""
        project_window = tk.Toplevel(self.root)
        project_window.title("📁 إنشاء مشروع جديد")
        project_window.geometry("700x500")
        project_window.configure(bg='#f0f0f0')

        # العنوان
        tk.Label(project_window, text="📁 إنشاء مشروع جديد",
                font=("Arial", 16, "bold"), bg='#f0f0f0').pack(pady=20)

        # إطار المدخلات
        input_frame = tk.Frame(project_window, bg='#f0f0f0')
        input_frame.pack(pady=20, padx=40, fill='both', expand=True)

        # اختيار المسار الأساسي
        tk.Label(input_frame, text="📂 المسار الأساسي للمشاريع:",
                font=("Arial", 12), bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=5)

        base_path_var = tk.StringVar()
        path_frame = tk.Frame(input_frame, bg='#f0f0f0')
        path_frame.grid(row=0, column=1, sticky='ew', pady=5, padx=(10,0))

        tk.Entry(path_frame, textvariable=base_path_var, width=40).pack(side='left', fill='x', expand=True)
        tk.Button(path_frame, text="تصفح", command=lambda: self.browse_folder(base_path_var),
                 bg='#2196F3', fg='white').pack(side='right', padx=(5,0))

        # نوع العميل
        tk.Label(input_frame, text="👤 نوع العميل:",
                font=("Arial", 12), bg='#f0f0f0').grid(row=1, column=0, sticky='w', pady=5)

        client_type_var = tk.StringVar()
        client_type_menu = ttk.Combobox(input_frame, textvariable=client_type_var, width=37)
        client_type_menu['values'] = ("جهة رسمية", "عميل حر", "خدمات طلابية", "مشروع جامعي")
        client_type_menu.grid(row=1, column=1, sticky='ew', pady=5, padx=(10,0))

        # اسم العميل/الجهة
        tk.Label(input_frame, text="🏢 اسم العميل/الجهة:",
                font=("Arial", 12), bg='#f0f0f0').grid(row=2, column=0, sticky='w', pady=5)

        client_name_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=client_name_var, width=40).grid(row=2, column=1, sticky='ew', pady=5, padx=(10,0))

        # اسم المشروع
        tk.Label(input_frame, text="📋 اسم المشروع:",
                font=("Arial", 12), bg='#f0f0f0').grid(row=3, column=0, sticky='w', pady=5)

        project_name_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=project_name_var, width=40).grid(row=3, column=1, sticky='ew', pady=5, padx=(10,0))

        # رقم المشروع
        tk.Label(input_frame, text="🔢 رقم المشروع (مثل: P_2401):",
                font=("Arial", 12), bg='#f0f0f0').grid(row=4, column=0, sticky='w', pady=5)

        project_number_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=project_number_var, width=40).grid(row=4, column=1, sticky='ew', pady=5, padx=(10,0))

        # تكوين الشبكة
        input_frame.columnconfigure(1, weight=1)

        # زر الإنشاء
        tk.Button(project_window, text="🚀 إنشاء المشروع",
                 command=lambda: self.create_new_project(
                     base_path_var.get(), client_type_var.get(),
                     client_name_var.get(), project_name_var.get(),
                     project_number_var.get(), project_window),
                 font=("Arial", 14), bg='#4CAF50', fg='white',
                 width=25, height=2).pack(pady=20)

    def create_new_project(self, base_path, client_type, client_name, project_name, project_number, window):
        """إنشاء مشروع جديد"""
        if not all([base_path, client_type, client_name, project_name, project_number]):
            messagebox.showerror("خطأ", "يرجى ملء جميع الحقول")
            return

        # تحديد المسار حسب نوع العميل
        if client_type == "جهة رسمية":
            client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "11_Clients_العملاء")
        elif client_type == "عميل حر":
            client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "11_Clients_العملاء")
        elif client_type == "خدمات طلابية":
            client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "11_Clients_العملاء")
        elif client_type == "مشروع جامعي":
            client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "12_University_الجامعة")

        # إنشاء مجلد العميل
        client_folder = os.path.join(client_path, client_name.replace(" ", "_"))

        # إنشاء مجلد المشروع
        project_folder_name = f"{project_number}_{project_name.replace(' ', '_')}"
        project_folder = os.path.join(client_folder, project_folder_name)

        # هيكل مجلدات المشروع
        project_structure = [
            "01_Admin",
            "02_Input_&_Refs",
            "03_Working_Files",
            "04_Exports_&_Deliverables"
        ]

        try:
            # إنشاء مجلد العميل
            os.makedirs(client_folder, exist_ok=True)

            # إنشاء مجلد المشروع
            os.makedirs(project_folder, exist_ok=True)

            # إنشاء مجلدات المشروع الفرعية
            for subfolder in project_structure:
                subfolder_path = os.path.join(project_folder, subfolder)
                os.makedirs(subfolder_path, exist_ok=True)

            # إنشاء ملف README للمشروع
            readme_content = f"""# {project_name}

## معلومات المشروع
- **العميل:** {client_name}
- **نوع العميل:** {client_type}
- **رقم المشروع:** {project_number}
- **تاريخ الإنشاء:** {datetime.now().strftime('%Y-%m-%d')}

## هيكل المجلدات
- **01_Admin:** عروض سعر، عقود، فواتير
- **02_Input_&_Refs:** ملفات من العميل، مراجع
- **03_Working_Files:** ملفات العمل المصدرية (PSD, AI, FIG)
- **04_Exports_&_Deliverables:** النسخ النهائية (JPG, PDF, PNG)

## ملاحظات
[أضف ملاحظاتك هنا]
"""

            readme_path = os.path.join(project_folder, "README.md")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

            messagebox.showinfo("نجح", f"تم إنشاء المشروع بنجاح في:\n{project_folder}")
            window.destroy()

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء إنشاء المشروع:\n{str(e)}")

    def create_filename_generator_window(self):
        """نافذة مولد أسماء الملفات"""
        filename_window = tk.Toplevel(self.root)
        filename_window.title("🔖 مولّد أسماء الملفات الاحترافية")
        filename_window.geometry("600x500")
        filename_window.configure(bg='#f0f0f0')

        # العنوان
        tk.Label(filename_window, text="🔖 مولّد أسماء الملفات الاحترافية",
                font=("Arial", 16, "bold"), bg='#f0f0f0').pack(pady=20)

        # إطار المدخلات
        input_frame = tk.Frame(filename_window, bg='#f0f0f0')
        input_frame.pack(pady=20, padx=40, fill='x')

        # التاريخ
        tk.Label(input_frame, text="📅 التاريخ (YYYY-MM-DD):",
                font=("Arial", 12), bg='#f0f0f0').pack(anchor='w')
        date_var = tk.StringVar(value=datetime.today().strftime('%Y-%m-%d'))
        tk.Entry(input_frame, textvariable=date_var, width=50).pack(pady=5, fill='x')

        # النوع
        tk.Label(input_frame, text="📂 النوع:",
                font=("Arial", 12), bg='#f0f0f0').pack(anchor='w', pady=(10,0))
        type_var = tk.StringVar()
        type_menu = ttk.Combobox(input_frame, textvariable=type_var, width=47)
        type_menu['values'] = ("Report", "Invoice", "Proposal", "HW", "Lecture", "Research", "Design", "Tutorial")
        type_menu.pack(pady=5, fill='x')

        # العميل - المشروع
        tk.Label(input_frame, text="👤 العميل - المشروع:",
                font=("Arial", 12), bg='#f0f0f0').pack(anchor='w', pady=(10,0))
        client_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=client_var, width=50).pack(pady=5, fill='x')

        # وصف موجز
        tk.Label(input_frame, text="📝 وصف موجز:",
                font=("Arial", 12), bg='#f0f0f0').pack(anchor='w', pady=(10,0))
        desc_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=desc_var, width=50).pack(pady=5, fill='x')

        # رقم الإصدار
        tk.Label(input_frame, text="🧮 رقم الإصدار (مثل: v01, vFINAL):",
                font=("Arial", 12), bg='#f0f0f0').pack(anchor='w', pady=(10,0))
        version_var = tk.StringVar(value="v01")
        tk.Entry(input_frame, textvariable=version_var, width=50).pack(pady=5, fill='x')

        # الامتداد
        tk.Label(input_frame, text="📁 الامتداد:",
                font=("Arial", 12), bg='#f0f0f0').pack(anchor='w', pady=(10,0))
        ext_var = tk.StringVar(value="pdf")
        ext_menu = ttk.Combobox(input_frame, textvariable=ext_var, width=47)
        ext_menu['values'] = ("pdf", "docx", "zip", "ai", "mp4", "xlsx", "png", "psd", "fig", "jpg", "jpeg")
        ext_menu.pack(pady=5, fill='x')

        # زر التوليد
        tk.Button(filename_window, text="🚀 توليد الاسم",
                 command=lambda: self.generate_filename(
                     date_var, type_var, client_var, desc_var, version_var, ext_var, result_label),
                 font=("Arial", 14), bg='#FF9800', fg='white',
                 width=25, height=2).pack(pady=20)

        # النتيجة
        result_label = tk.Label(filename_window, text="", fg="blue", wraplength=550,
                               font=("Arial", 12), bg='#f0f0f0')
        result_label.pack(pady=10)

        # زر النسخ
        tk.Button(filename_window, text="📋 نسخ إلى الحافظة",
                 command=lambda: self.copy_to_clipboard(result_label, filename_window),
                 font=("Arial", 12), bg='#4CAF50', fg='white',
                 width=25, height=1).pack(pady=5)

    def generate_filename(self, date_var, type_var, client_var, desc_var, version_var, ext_var, result_label):
        """توليد اسم الملف"""
        date = date_var.get() or datetime.today().strftime('%Y-%m-%d')
        file_type = type_var.get()
        client_project = client_var.get().strip().replace(" ", "")
        brief_desc = desc_var.get().strip().replace(" ", "-")
        version = version_var.get()
        extension = ext_var.get()

        if not all([file_type, client_project, brief_desc]):
            result_label.config(text="⚠️ يرجى ملء جميع الحقول المطلوبة", fg="red")
            return

        filename = f"{date}_{file_type}_{client_project}_{brief_desc}_{version}.{extension}"
        result_label.config(text=filename, fg="blue")

    def copy_to_clipboard(self, result_label, window):
        """نسخ النتيجة إلى الحافظة"""
        text = result_label.cget("text")
        if text and not text.startswith("⚠️"):
            window.clipboard_clear()
            window.clipboard_append(text)
            window.update()
            messagebox.showinfo("تم", "تم نسخ اسم الملف إلى الحافظة")
        else:
            messagebox.showwarning("تحذير", "لا يوجد اسم ملف للنسخ")

    def run(self):
        """تشغيل البرنامج"""
        self.root.mainloop()

# تشغيل البرنامج
if __name__ == "__main__":
    app = ProjectOrganizer()
    app.run()
