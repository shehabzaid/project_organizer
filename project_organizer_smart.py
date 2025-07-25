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

    def generate_next_project_number(self):
        """توليد رقم المشروع التالي تلقائياً"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # الحصول على السنة والشهر الحالي
        current_date = datetime.now()
        year = current_date.strftime('%y')  # السنة بصيغة مختصرة (24 بدلاً من 2024)
        month = current_date.strftime('%m')  # الشهر بصيغة رقمية (01-12)

        # البحث عن آخر رقم مشروع في نفس السنة والشهر
        pattern = f"P_{year}{month}%"
        cursor.execute('''
            SELECT project_number FROM projects
            WHERE project_number LIKE ?
            ORDER BY project_number DESC
            LIMIT 1
        ''', (pattern,))

        result = cursor.fetchone()
        conn.close()

        if result:
            # استخراج الرقم التسلسلي من آخر مشروع
            last_number = result[0]
            try:
                # استخراج الجزء الرقمي الأخير (مثل: P_2401_003 -> 003)
                sequence_part = last_number.split('_')[-1]
                next_sequence = int(sequence_part) + 1
            except (ValueError, IndexError):
                next_sequence = 1
        else:
            # أول مشروع في هذا الشهر
            next_sequence = 1

        # تكوين رقم المشروع الجديد
        project_number = f"P_{year}{month}_{next_sequence:03d}"

        return project_number
    
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
        self.root.geometry("1000x750")
        self.root.configure(bg='#f8f9fa')

        # تحسين مظهر النافذة
        self.root.resizable(True, True)
        self.root.minsize(800, 600)

        # إعداد الخطوط
        self.fonts = {
            'title': ('Times New Roman', 20, 'bold'),
            'subtitle': ('Times New Roman', 14, 'normal'),
            'heading': ('Times New Roman', 16, 'bold'),
            'button': ('Times New Roman', 12, 'bold'),
            'text': ('Times New Roman', 11, 'normal'),
            'small': ('Times New Roman', 10, 'normal')
        }

        # إعداد الألوان
        self.colors = {
            'bg_main': '#f8f9fa',
            'bg_secondary': '#ffffff',
            'primary': '#2c3e50',
            'success': '#27ae60',
            'info': '#3498db',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'purple': '#8e44ad',
            'dark': '#34495e',
            'text_primary': '#2c3e50',
            'text_secondary': '#7f8c8d'
        }

        # إنشاء مدير قاعدة البيانات
        self.db = DatabaseManager()

        # متغيرات عامة
        self.selected_path = tk.StringVar()
        self.current_structure_id = None

        self.create_main_interface()
    
    def create_main_interface(self):
        """إنشاء الواجهة الرئيسية مع إمكانية التمرير محسنة"""
        # إنشاء إطار رئيسي للتحكم في التخطيط
        main_container = tk.Frame(self.root, bg=self.colors['bg_main'])
        main_container.pack(fill="both", expand=True)

        # إنشاء Canvas وScrollbar للتمرير
        canvas = tk.Canvas(main_container, bg=self.colors['bg_main'], highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_main'])

        # تكوين التمرير مع ضبط العرض
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # ضبط عرض الإطار القابل للتمرير ليملأ Canvas
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)

        scrollable_frame.bind("<Configure>", configure_scroll_region)

        # إنشاء النافذة داخل Canvas مع ضبط العرض
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # ضبط عرض Canvas عند تغيير حجم النافذة
        def configure_canvas(event):
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        canvas.bind('<Configure>', configure_canvas)

        # تعبئة Canvas والScrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ربط عجلة الماوس بالتمرير
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # الآن نضع المحتوى في scrollable_frame بدلاً من main_container

        # إطار العنوان الرئيسي مع خلفية مميزة
        title_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_secondary'], relief='raised', bd=2)
        title_frame.pack(pady=20, padx=20, fill='x')

        # العنوان الرئيسي
        tk.Label(title_frame, text="🗂️ منظم المشاريع الاحترافي",
                font=self.fonts['title'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=(15, 5))

        tk.Label(title_frame, text="الإصدار الذكي مع قاعدة البيانات",
                font=self.fonts['subtitle'], bg=self.colors['bg_secondary'],
                fg=self.colors['text_secondary']).pack()

        tk.Label(title_frame, text="نظام متطور لتنظيم وإدارة المشاريع والملفات بذكاء",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['text_secondary']).pack(pady=(0, 15))

        # إطار الإحصائيات مع تصميم محسن
        stats_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        stats_frame.pack(pady=15, padx=20, fill='x')

        self.update_stats_display(stats_frame)

        # إطار الأزرار الرئيسية مع تحسينات
        buttons_container = tk.Frame(scrollable_frame, bg=self.colors['bg_main'])
        buttons_container.pack(pady=20, padx=20, fill='x')

        # عنوان قسم الأزرار
        tk.Label(buttons_container, text="🎛️ لوحة التحكم الرئيسية",
                font=self.fonts['heading'], bg=self.colors['bg_main'],
                fg=self.colors['primary']).pack(pady=(0, 20))

        # إطار الأزرار مع شبكة منظمة
        buttons_grid = tk.Frame(buttons_container, bg=self.colors['bg_main'])
        buttons_grid.pack()

        # الصف الأول من الأزرار
        row1_frame = tk.Frame(buttons_grid, bg=self.colors['bg_main'])
        row1_frame.pack(pady=8)

        self.create_styled_button(row1_frame, "🏗️ إنشاء هيكل جديد",
                                 self.create_full_structure_window, self.colors['success'])

        self.create_styled_button(row1_frame, "📊 إدارة الهياكل الموجودة",
                                 self.manage_structures_window, self.colors['purple'])

        # الصف الثاني من الأزرار
        row2_frame = tk.Frame(buttons_grid, bg=self.colors['bg_main'])
        row2_frame.pack(pady=8)

        self.create_styled_button(row2_frame, "📁 إنشاء مشروع جديد",
                                 self.create_new_project_window, self.colors['info'])

        self.create_styled_button(row2_frame, "👥 إدارة العملاء والمشاريع",
                                 self.manage_projects_window, self.colors['danger'])

        # الصف الثالث من الأزرار
        row3_frame = tk.Frame(buttons_grid, bg=self.colors['bg_main'])
        row3_frame.pack(pady=8)

        self.create_styled_button(row3_frame, "🔖 مولّد أسماء الملفات",
                                 self.create_filename_generator_window, self.colors['warning'])

        self.create_styled_button(row3_frame, "📈 تقارير وإحصائيات",
                                 self.show_reports_window, self.colors['dark'])

        # الصف الرابع من الأزرار - أدوات إضافية
        row4_frame = tk.Frame(buttons_grid, bg=self.colors['bg_main'])
        row4_frame.pack(pady=8)

        self.create_styled_button(row4_frame, "💡 أمثلة قواعد التسمية",
                                 self.show_filename_examples_window, '#6c5ce7')

        # إطار زر الخروج
        exit_frame = tk.Frame(buttons_container, bg=self.colors['bg_main'])
        exit_frame.pack(pady=25)

        exit_btn = tk.Button(exit_frame, text="❌ خروج من البرنامج",
                           command=self.root.quit,
                           font=self.fonts['button'], bg=self.colors['danger'], fg='white',
                           width=30, height=2, relief='raised', bd=3,
                           activebackground='#c0392b', activeforeground='white')
        exit_btn.pack()

        # إضافة تأثير hover للزر
        exit_btn.bind("<Enter>", lambda e: exit_btn.config(bg='#c0392b'))
        exit_btn.bind("<Leave>", lambda e: exit_btn.config(bg=self.colors['danger']))

        # إطار معلومات المطور في الأسفل
        developer_frame = tk.Frame(scrollable_frame, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        developer_frame.pack(pady=20, padx=20, fill='x')

        # معلومات المطور
        self.create_developer_info(developer_frame)

        # إضافة مساحة إضافية في الأسفل
        tk.Label(scrollable_frame, text="", bg=self.colors['bg_main'], height=2).pack()

        # حفظ مرجع للـ canvas للاستخدام في التحديثات
        self.main_canvas = canvas
        self.scrollable_frame = scrollable_frame
        self.stats_frame_ref = stats_frame  # حفظ مرجع لإطار الإحصائيات

    def refresh_main_interface(self):
        """تحديث الإحصائيات في الواجهة الرئيسية"""
        if hasattr(self, 'stats_frame_ref'):
            self.update_stats_display(self.stats_frame_ref)

    def generate_and_set_project_number(self, project_number_var):
        """توليد وتعيين رقم المشروع التلقائي"""
        new_number = self.db.generate_next_project_number()
        project_number_var.set(new_number)

    def toggle_client_fields(self, choice, existing_frame, new_frame):
        """التبديل بين حقول العميل الجديد والموجود"""
        if choice == "موجود":
            existing_frame.grid()
            new_frame.grid_remove()
        else:
            existing_frame.grid_remove()
            new_frame.grid()

    def create_styled_button(self, parent, text, command, color):
        """إنشاء زر بتصميم محسن"""
        btn = tk.Button(parent, text=text, command=command,
                       font=self.fonts['button'], bg=color, fg='white',
                       width=28, height=3, relief='raised', bd=3,
                       activebackground=self.darken_color(color), activeforeground='white')
        btn.pack(side='left', padx=10)

        # إضافة تأثير hover
        btn.bind("<Enter>", lambda e: btn.config(bg=self.darken_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))

        return btn

    def darken_color(self, color):
        """تغميق اللون للتأثير hover"""
        color_map = {
            self.colors['success']: '#229954',
            self.colors['purple']: '#7d3c98',
            self.colors['info']: '#2e86c1',
            self.colors['danger']: '#c0392b',
            self.colors['warning']: '#d68910',
            self.colors['dark']: '#2c3e50',
            '#6c5ce7': '#5b4cdb'  # للون البنفسجي الجديد
        }
        return color_map.get(color, color)

    def create_developer_info(self, parent_frame):
        """إنشاء قسم معلومات المطور مضغوط ومنظم"""
        # إطار رئيسي للمعلومات مع padding أقل
        info_container = tk.Frame(parent_frame, bg=self.colors['bg_secondary'])
        info_container.pack(fill='x', pady=8)

        # صف واحد يحتوي على جميع المعلومات
        main_row = tk.Frame(info_container, bg=self.colors['bg_secondary'])
        main_row.pack(fill='x', pady=5)

        # الجزء الأيسر - معلومات المطور
        left_section = tk.Frame(main_row, bg=self.colors['bg_secondary'])
        left_section.pack(side='left', fill='x', expand=True)

        # أيقونة ومعلومات المطور
        tk.Label(left_section, text="👨‍💻", font=('Times New Roman', 14),
                bg=self.colors['bg_secondary']).pack(side='left', padx=(15, 5))

        tk.Label(left_section, text="تصميم وبرمجة:",
                font=('Times New Roman', 10, 'bold'),
                bg=self.colors['bg_secondary'], fg=self.colors['text_primary']).pack(side='left', padx=3)

        # اسم المطور
        dev_name_label = tk.Label(left_section, text="المهندس شهاب زيد",
                                 font=('Times New Roman', 11, 'bold'),
                                 bg=self.colors['bg_secondary'], fg=self.colors['info'],
                                 cursor='hand2')
        dev_name_label.pack(side='left', padx=5)

        # الجزء الأوسط - معلومات التواصل
        center_section = tk.Frame(main_row, bg=self.colors['bg_secondary'])
        center_section.pack(side='left', padx=20)

        tk.Label(center_section, text="📱", font=('Times New Roman', 12),
                bg=self.colors['bg_secondary']).pack(side='left', padx=3)

        # رقم الهاتف
        phone_label = tk.Label(center_section, text="772919946",
                              font=('Times New Roman', 11, 'bold'),
                              bg=self.colors['bg_secondary'], fg=self.colors['success'],
                              cursor='hand2')
        phone_label.pack(side='left', padx=5)

        # زر نسخ رقم الهاتف
        copy_phone_btn = tk.Button(center_section, text="📋",
                                  command=lambda: self.copy_phone_number(phone_label.cget("text"), copy_phone_btn),
                                  font=('Times New Roman', 8), bg=self.colors['info'], fg='white',
                                  width=2, height=1, relief='raised', bd=1)
        copy_phone_btn.pack(side='left', padx=5)

        # الجزء الأيمن - معلومات الإصدار
        right_section = tk.Frame(main_row, bg=self.colors['bg_secondary'])
        right_section.pack(side='right', padx=(20, 15))

        tk.Label(right_section, text="🔖", font=('Times New Roman', 12),
                bg=self.colors['bg_secondary']).pack(side='left', padx=3)

        # معلومات الإصدار مختصرة
        version_text = f"v2.0 | {datetime.now().strftime('%Y')}"
        tk.Label(right_section, text=version_text,
                font=('Times New Roman', 9),
                bg=self.colors['bg_secondary'], fg=self.colors['text_secondary']).pack(side='left', padx=3)

        # إضافة تأثيرات hover للعناصر التفاعلية
        def on_enter_dev(e):
            dev_name_label.config(fg=self.colors['primary'])

        def on_leave_dev(e):
            dev_name_label.config(fg=self.colors['info'])

        def on_enter_phone(e):
            phone_label.config(fg=self.colors['primary'])

        def on_leave_phone(e):
            phone_label.config(fg=self.colors['success'])

        # ربط الأحداث
        dev_name_label.bind("<Enter>", on_enter_dev)
        dev_name_label.bind("<Leave>", on_leave_dev)
        phone_label.bind("<Enter>", on_enter_phone)
        phone_label.bind("<Leave>", on_leave_phone)

        # إضافة وظيفة النقر على الاسم
        def show_developer_info(e):
            self.show_developer_details_window()

        dev_name_label.bind("<Button-1>", show_developer_info)

        # إضافة وظيفة النقر على رقم الهاتف
        def copy_phone_on_click(e):
            self.copy_phone_number(phone_label.cget("text"), copy_phone_btn)

        phone_label.bind("<Button-1>", copy_phone_on_click)

    def copy_phone_number(self, phone_number, copy_btn):
        """نسخ رقم الهاتف إلى الحافظة"""
        original_text = copy_btn.cget("text")
        original_bg = copy_btn.cget("bg")

        # تأثير بصري
        copy_btn.config(text="✓", bg='#2ecc71')
        copy_btn.update()

        # نسخ الرقم
        self.root.clipboard_clear()
        self.root.clipboard_append(phone_number)
        self.root.update()

        # رسالة تأكيد
        messagebox.showinfo("تم النسخ", f"تم نسخ رقم الهاتف: {phone_number}")

        # إعادة الزر لحالته الأصلية
        def reset_copy_btn():
            copy_btn.config(text=original_text, bg=original_bg)

        self.root.after(1500, reset_copy_btn)

    def show_developer_details_window(self):
        """نافذة تفاصيل المطور"""
        dev_window = tk.Toplevel(self.root)
        dev_window.title("👨‍💻 معلومات المطور")
        dev_window.geometry("600x500")
        dev_window.configure(bg=self.colors['bg_main'])
        dev_window.resizable(False, False)

        # توسيط النافذة
        dev_window.transient(self.root)
        dev_window.grab_set()

        # إطار العنوان
        title_frame = tk.Frame(dev_window, bg=self.colors['bg_secondary'], relief='raised', bd=2)
        title_frame.pack(pady=20, padx=20, fill='x')

        tk.Label(title_frame, text="👨‍💻 معلومات المطور",
                font=self.fonts['heading'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=15)

        # إطار المعلومات
        info_frame = tk.Frame(dev_window, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        info_frame.pack(pady=20, padx=20, fill='both', expand=True)

        # المعلومات التفصيلية
        details_text = """
🎓 المهندس شهاب زيد
💼 مطور برمجيات ومهندس أنظمة

📱 معلومات التواصل:
   • الهاتف: 772919946
   • التخصص: هندسة البرمجيات وتطوير الأنظمة

🛠️ التقنيات المستخدمة في هذا المشروع:
   • Python 3.12+ مع مكتبة Tkinter للواجهات
   • SQLite لقاعدة البيانات المحلية
   • نظام إدارة الملفات والمجلدات
   • تصميم واجهات مستخدم متقدمة

✨ ميزات البرنامج:
   • نظام ذكي لتنظيم المشاريع
   • قاعدة بيانات متكاملة
   • مولد أسماء ملفات احترافي
   • واجهة مستخدم عصرية وسهلة الاستخدام

📅 تاريخ التطوير: 2024
🔖 الإصدار: v2.0 - الإصدار الذكي

💡 تم تطوير هذا البرنامج لمساعدة المحترفين والطلاب
   في تنظيم مشاريعهم وملفاتهم بطريقة احترافية ومنهجية.
        """

        details_label = tk.Label(info_frame, text=details_text,
                               font=('Times New Roman', 11), bg=self.colors['bg_secondary'],
                               fg=self.colors['text_primary'], justify='right')
        details_label.pack(pady=20, padx=20)

        # زر إغلاق
        tk.Button(dev_window, text="👍 شكراً",
                 command=dev_window.destroy,
                 font=self.fonts['button'], bg=self.colors['success'], fg='white',
                 width=15, height=2).pack(pady=20)
    
    def update_stats_display(self, parent_frame):
        """تحديث عرض الإحصائيات بتصميم محسن"""
        # مسح الإحصائيات السابقة
        for widget in parent_frame.winfo_children():
            widget.destroy()

        # الحصول على الإحصائيات
        structures = self.db.get_structures()
        clients = self.db.get_clients()
        projects = self.db.get_projects()

        # عنوان الإحصائيات
        tk.Label(parent_frame, text="📊 إحصائيات سريعة",
                font=self.fonts['heading'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=(10, 15))

        # إطار الإحصائيات في صف واحد
        stats_row = tk.Frame(parent_frame, bg=self.colors['bg_secondary'])
        stats_row.pack(pady=(0, 15))

        # إحصائية الهياكل
        self.create_stat_card(stats_row, "🏗️", "الهياكل", len(structures), self.colors['success'])

        # إحصائية العملاء
        self.create_stat_card(stats_row, "👥", "العملاء", len(clients), self.colors['info'])

        # إحصائية المشاريع
        self.create_stat_card(stats_row, "📁", "المشاريع", len(projects), self.colors['warning'])

        # إحصائية المتوسط
        avg_projects = len(projects)/len(clients) if clients else 0
        self.create_stat_card(stats_row, "📈", "متوسط المشاريع", f"{avg_projects:.1f}", self.colors['purple'])

    def create_stat_card(self, parent, icon, title, value, color):
        """إنشاء بطاقة إحصائية"""
        card_frame = tk.Frame(parent, bg=color, relief='raised', bd=2)
        card_frame.pack(side='left', padx=8, pady=5)

        # الأيقونة
        tk.Label(card_frame, text=icon, font=('Times New Roman', 18),
                bg=color, fg='white').pack(pady=(8, 2))

        # القيمة
        tk.Label(card_frame, text=str(value), font=('Times New Roman', 16, 'bold'),
                bg=color, fg='white').pack()

        # العنوان
        tk.Label(card_frame, text=title, font=('Times New Roman', 10),
                bg=color, fg='white').pack(pady=(2, 8))

        # تحديد عرض البطاقة
        card_frame.config(width=100, height=80)

    def browse_folder(self, path_var):
        """تصفح واختيار مجلد"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            path_var.set(folder_path)

    def create_full_structure_window(self):
        """نافذة إنشاء الهيكل الكامل بتصميم محسن"""
        structure_window = tk.Toplevel(self.root)
        structure_window.title("🏗️ إنشاء هيكل مشاريع جديد")
        structure_window.geometry("800x700")
        structure_window.configure(bg=self.colors['bg_main'])
        structure_window.resizable(True, True)

        # إطار العنوان
        title_frame = tk.Frame(structure_window, bg=self.colors['bg_secondary'], relief='raised', bd=2)
        title_frame.pack(pady=20, padx=20, fill='x')

        tk.Label(title_frame, text="🏗️ إنشاء هيكل مشاريع جديد",
                font=self.fonts['heading'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=15)

        # إطار المدخلات مع تصميم محسن
        input_frame = tk.Frame(structure_window, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        input_frame.pack(pady=20, padx=20, fill='x')

        # عنوان قسم المدخلات
        tk.Label(input_frame, text="📝 معلومات الهيكل الجديد",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=(15, 10))

        # اسم الهيكل
        name_frame = tk.Frame(input_frame, bg=self.colors['bg_secondary'])
        name_frame.pack(pady=10, padx=20, fill='x')

        tk.Label(name_frame, text="📝 اسم الهيكل:",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['text_primary']).pack(anchor='w')

        structure_name_var = tk.StringVar()
        name_entry = tk.Entry(name_frame, textvariable=structure_name_var,
                             font=self.fonts['text'], width=50, relief='solid', bd=1)
        name_entry.pack(pady=5, fill='x')

        # اختيار المسار
        path_frame = tk.Frame(input_frame, bg=self.colors['bg_secondary'])
        path_frame.pack(pady=10, padx=20, fill='x')

        tk.Label(path_frame, text="📂 اختر المسار لإنشاء الهيكل:",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['text_primary']).pack(anchor='w')

        path_entry_frame = tk.Frame(path_frame, bg=self.colors['bg_secondary'])
        path_entry_frame.pack(fill='x', pady=5)

        path_entry = tk.Entry(path_entry_frame, textvariable=self.selected_path,
                             font=self.fonts['text'], relief='solid', bd=1)
        path_entry.pack(side='left', fill='x', expand=True)

        browse_btn = tk.Button(path_entry_frame, text="📁 تصفح",
                              command=lambda: self.browse_folder(self.selected_path),
                              font=self.fonts['button'], bg=self.colors['info'], fg='white',
                              relief='raised', bd=2)
        browse_btn.pack(side='right', padx=(10,0))

        # إضافة مساحة
        tk.Label(input_frame, text="", bg=self.colors['bg_secondary']).pack(pady=5)

        # معلومات الهيكل
        info_frame = tk.Frame(structure_window, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        info_frame.pack(pady=20, padx=20, fill='both', expand=True)

        tk.Label(info_frame, text="📋 هيكل المجلدات الذي سيتم إنشاؤه:",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(anchor='w', pady=(15, 10), padx=15)

        # إطار النص مع شريط تمرير
        text_frame = tk.Frame(info_frame, bg=self.colors['bg_secondary'])
        text_frame.pack(pady=10, padx=15, fill='both', expand=True)

        # شريط التمرير
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')

        # قائمة المجلدات الرئيسية
        structure_text = tk.Text(text_frame, height=15, width=70,
                               font=('Times New Roman', 10), bg='#ffffff',
                               relief='solid', bd=1, yscrollcommand=scrollbar.set)
        structure_text.pack(side='left', fill='both', expand=True)

        scrollbar.config(command=structure_text.yview)

        structure_info = """📁 00_Inbox_صندوق_الوارد/
📁 10_Work_&_Study_العمل_والدراسة/
   📁 11_Clients_العملاء/
   📁 12_University_الجامعة/
📁 20_Knowledge_Base_قاعدة_المعرفة/
   📁 21_Courses_الكورسات/
      📁 2023/
      📁 2024/
   📁 22_Tutorials_شروحاتي/
      📁 01_Scripts_&_Notes/
      📁 02_Final_Videos/
   📁 23_Resources_الموارد/
      📁 Books_&_Articles/
      📁 Code_Snippets/
      📁 Stock_Media/
      📁 Templates_القوالب/
      📁 Software_&_Tools/
   📁 24_Portfolio_نماذج_الأعمال/
      📁 Web/
      📁 Apps/
      📁 Graphics/
📁 30_Admin_&_Finance_الإدارة_والمالية/
   📁 31_Invoices_الفواتير/
      📁 2023/
      📁 2024/
   📁 32_Proposals_&_Contracts/
   📁 33_Receipts_الإيصالات/
   📁 34_Reports_تقارير_مالية/
📁 40_Personal_شخصي/
   📁 CV_&_CoverLetters/
   📁 ID_&_Documents/
   📁 Goals_&_Planning/
   📁 Personal_Projects/
📁 99_Archive_الأرشيف/
   📁 Work_Archive/
      📁 2023/
   📁 Study_Archive/
      📁 2022/"""

        structure_text.insert('1.0', structure_info)
        structure_text.config(state='disabled')

        # إطار الأزرار
        buttons_frame = tk.Frame(structure_window, bg=self.colors['bg_main'])
        buttons_frame.pack(pady=20)

        # زر الإنشاء
        create_btn = tk.Button(buttons_frame, text="🚀 إنشاء الهيكل الكامل",
                              command=lambda: self.create_full_structure(structure_window, structure_name_var.get()),
                              font=self.fonts['button'], bg=self.colors['success'], fg='white',
                              width=25, height=2, relief='raised', bd=3)
        create_btn.pack(side='left', padx=10)

        # زر الإلغاء
        cancel_btn = tk.Button(buttons_frame, text="❌ إلغاء",
                              command=structure_window.destroy,
                              font=self.fonts['button'], bg=self.colors['danger'], fg='white',
                              width=15, height=2, relief='raised', bd=3)
        cancel_btn.pack(side='left', padx=10)

    def create_full_structure(self, window, structure_name):
        """إنشاء الهيكل الكامل للمجلدات"""
        if not self.selected_path.get():
            messagebox.showerror("خطأ", "يرجى اختيار مسار لإنشاء الهيكل")
            return

        if not structure_name:
            messagebox.showerror("خطأ", "يرجى إدخال اسم للهيكل")
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
            # إنشاء المجلدات
            self._create_folders_recursive(base_path, folder_structure)

            # حفظ الهيكل في قاعدة البيانات
            structure_id = self.db.add_structure(structure_name, base_path, folder_structure)

            if structure_id:
                self.current_structure_id = structure_id
                messagebox.showinfo("نجح", f"تم إنشاء الهيكل '{structure_name}' بنجاح في:\n{base_path}\n\nتم حفظ الهيكل في قاعدة البيانات.")
                window.destroy()
                self.refresh_main_interface()  # تحديث الإحصائيات
            else:
                messagebox.showerror("خطأ", "فشل في حفظ الهيكل في قاعدة البيانات. قد يكون الاسم مكرر.")

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

    def manage_structures_window(self):
        """نافذة إدارة الهياكل الموجودة"""
        manage_window = tk.Toplevel(self.root)
        manage_window.title("📊 إدارة الهياكل الموجودة")
        manage_window.geometry("800x600")
        manage_window.configure(bg='#f0f0f0')

        # العنوان
        tk.Label(manage_window, text="📊 إدارة الهياكل الموجودة",
                font=("Arial", 16, "bold"), bg='#f0f0f0').pack(pady=20)

        # إطار القائمة
        list_frame = tk.Frame(manage_window, bg='#f0f0f0')
        list_frame.pack(pady=20, padx=20, fill='both', expand=True)

        # قائمة الهياكل
        columns = ('ID', 'الاسم', 'المسار', 'تاريخ الإنشاء')
        tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # تعريف الأعمدة
        tree.heading('ID', text='ID')
        tree.heading('الاسم', text='الاسم')
        tree.heading('المسار', text='المسار')
        tree.heading('تاريخ الإنشاء', text='تاريخ الإنشاء')

        tree.column('ID', width=50)
        tree.column('الاسم', width=200)
        tree.column('المسار', width=300)
        tree.column('تاريخ الإنشاء', width=150)

        # إضافة البيانات
        structures = self.db.get_structures()
        for structure in structures:
            tree.insert('', 'end', values=(
                structure[0],  # ID
                structure[1],  # Name
                structure[2],  # Base Path
                structure[4][:10]  # Created Date (first 10 chars)
            ))

        tree.pack(fill='both', expand=True)

        # إطار الأزرار
        buttons_frame = tk.Frame(manage_window, bg='#f0f0f0')
        buttons_frame.pack(pady=10)

        tk.Button(buttons_frame, text="🎯 اختيار كهيكل نشط",
                 command=lambda: self.select_active_structure(tree),
                 font=("Arial", 12), bg='#4CAF50', fg='white').pack(side='left', padx=5)

        tk.Button(buttons_frame, text="👁️ عرض التفاصيل",
                 command=lambda: self.show_structure_details(tree),
                 font=("Arial", 12), bg='#2196F3', fg='white').pack(side='left', padx=5)

        tk.Button(buttons_frame, text="🗑️ حذف",
                 command=lambda: self.delete_structure(tree),
                 font=("Arial", 12), bg='#f44336', fg='white').pack(side='left', padx=5)

    def select_active_structure(self, tree):
        """اختيار هيكل كهيكل نشط"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("تحذير", "يرجى اختيار هيكل من القائمة")
            return

        item = tree.item(selection[0])
        structure_id = item['values'][0]
        structure_name = item['values'][1]

        self.current_structure_id = structure_id
        messagebox.showinfo("تم", f"تم اختيار '{structure_name}' كهيكل نشط")

    def show_structure_details(self, tree):
        """عرض تفاصيل الهيكل"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("تحذير", "يرجى اختيار هيكل من القائمة")
            return

        item = tree.item(selection[0])
        structure_id = item['values'][0]

        # الحصول على تفاصيل الهيكل
        structures = self.db.get_structures()
        structure = next((s for s in structures if s[0] == structure_id), None)

        if structure:
            details_window = tk.Toplevel(self.root)
            details_window.title(f"تفاصيل الهيكل: {structure[1]}")
            details_window.geometry("600x400")
            details_window.configure(bg='#f0f0f0')

            # عرض التفاصيل
            details_text = tk.Text(details_window, wrap='word', font=("Arial", 10))
            details_text.pack(pady=20, padx=20, fill='both', expand=True)

            details_content = f"""اسم الهيكل: {structure[1]}
المسار الأساسي: {structure[2]}
تاريخ الإنشاء: {structure[4]}
آخر تعديل: {structure[5]}

هيكل المجلدات:
{json.dumps(json.loads(structure[3]), indent=2, ensure_ascii=False)}"""

            details_text.insert('1.0', details_content)
            details_text.config(state='disabled')

    def delete_structure(self, tree):
        """حذف هيكل"""
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("تحذير", "يرجى اختيار هيكل من القائمة")
            return

        item = tree.item(selection[0])
        structure_name = item['values'][1]

        if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف الهيكل '{structure_name}'؟\nسيتم حذف جميع البيانات المرتبطة به."):
            # TODO: إضافة منطق الحذف من قاعدة البيانات
            messagebox.showinfo("تم", "تم حذف الهيكل بنجاح")
            tree.delete(selection[0])

    def create_new_project_window(self):
        """نافذة إنشاء مشروع جديد"""
        if not self.current_structure_id:
            messagebox.showwarning("تحذير", "يرجى اختيار هيكل نشط أولاً من إدارة الهياكل")
            return

        project_window = tk.Toplevel(self.root)
        project_window.title("📁 إنشاء مشروع جديد")
        project_window.geometry("700x600")
        project_window.configure(bg='#f0f0f0')

        # العنوان
        tk.Label(project_window, text="📁 إنشاء مشروع جديد",
                font=("Arial", 16, "bold"), bg='#f0f0f0').pack(pady=20)

        # إطار المدخلات
        input_frame = tk.Frame(project_window, bg='#f0f0f0')
        input_frame.pack(pady=20, padx=40, fill='x')

        # اختيار العميل (جديد أو موجود)
        tk.Label(input_frame, text="👤 اختيار العميل:",
                font=("Arial", 12, "bold"), bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=5)

        # إطار اختيار نوع العميل
        client_choice_frame = tk.Frame(input_frame, bg='#f0f0f0')
        client_choice_frame.grid(row=0, column=1, sticky='ew', pady=5, padx=(10,0))

        client_choice_var = tk.StringVar(value="جديد")
        tk.Radiobutton(client_choice_frame, text="عميل جديد", variable=client_choice_var,
                      value="جديد", font=("Arial", 10), bg='#f0f0f0',
                      command=lambda: self.toggle_client_fields(client_choice_var.get(),
                                                               existing_client_frame, new_client_frame)).pack(side='left', padx=(0,20))

        tk.Radiobutton(client_choice_frame, text="عميل موجود", variable=client_choice_var,
                      value="موجود", font=("Arial", 10), bg='#f0f0f0',
                      command=lambda: self.toggle_client_fields(client_choice_var.get(),
                                                               existing_client_frame, new_client_frame)).pack(side='left')

        # إطار العميل الموجود
        existing_client_frame = tk.Frame(input_frame, bg='#f0f0f0')
        existing_client_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5, padx=10)

        tk.Label(existing_client_frame, text="🏢 اختر العميل الموجود:",
                font=("Arial", 11), bg='#f0f0f0').pack(anchor='w')

        existing_client_var = tk.StringVar()
        existing_client_menu = ttk.Combobox(existing_client_frame, textvariable=existing_client_var,
                                          font=("Arial", 10), width=50, state='readonly')

        # تحميل العملاء الموجودين
        clients = self.db.get_clients(self.current_structure_id)
        client_options = [f"{client[1]} ({client[2]})" for client in clients]
        existing_client_menu['values'] = client_options
        existing_client_menu.pack(fill='x', pady=5)

        # إطار العميل الجديد
        new_client_frame = tk.Frame(input_frame, bg='#f0f0f0')
        new_client_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5, padx=10)

        # نوع العميل الجديد
        tk.Label(new_client_frame, text="👤 نوع العميل:",
                font=("Arial", 11), bg='#f0f0f0').pack(anchor='w')

        client_type_var = tk.StringVar()
        client_type_menu = ttk.Combobox(new_client_frame, textvariable=client_type_var,
                                       font=("Arial", 10), width=47)
        client_type_menu['values'] = ("جهة رسمية", "عميل حر", "خدمات طلابية", "مشروع جامعي")
        client_type_menu.pack(fill='x', pady=5)

        # اسم العميل الجديد
        tk.Label(new_client_frame, text="🏢 اسم العميل/الجهة:",
                font=("Arial", 11), bg='#f0f0f0').pack(anchor='w', pady=(10,0))

        client_name_var = tk.StringVar()
        tk.Entry(new_client_frame, textvariable=client_name_var,
                font=("Arial", 10), width=50).pack(fill='x', pady=5)

        # إخفاء إطار العميل الموجود في البداية
        existing_client_frame.grid_remove()

        # اسم المشروع
        tk.Label(input_frame, text="📋 اسم المشروع:",
                font=("Arial", 12), bg='#f0f0f0').grid(row=2, column=0, sticky='w', pady=5)

        project_name_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=project_name_var, width=40).grid(row=2, column=1, sticky='ew', pady=5, padx=(10,0))

        # رقم المشروع مع التوليد التلقائي
        tk.Label(input_frame, text="🔢 رقم المشروع (تلقائي):",
                font=("Arial", 12), bg='#f0f0f0').grid(row=3, column=0, sticky='w', pady=5)

        # إطار رقم المشروع مع زر التوليد
        project_number_frame = tk.Frame(input_frame, bg='#f0f0f0')
        project_number_frame.grid(row=3, column=1, sticky='ew', pady=5, padx=(10,0))
        project_number_frame.columnconfigure(0, weight=1)

        project_number_var = tk.StringVar()
        project_number_entry = tk.Entry(project_number_frame, textvariable=project_number_var,
                                       font=("Arial", 11), relief='solid', bd=1)
        project_number_entry.grid(row=0, column=0, sticky='ew', padx=(0,5))

        # زر توليد رقم جديد
        generate_btn = tk.Button(project_number_frame, text="🔄 توليد",
                               command=lambda: self.generate_and_set_project_number(project_number_var),
                               font=('Arial', 9), bg='#2196F3', fg='white',
                               width=8, height=1, relief='raised', bd=1)
        generate_btn.grid(row=0, column=1)

        # توليد رقم تلقائي عند فتح النافذة
        self.generate_and_set_project_number(project_number_var)

        # معلومات توضيحية عن نظام الترقيم
        info_label = tk.Label(input_frame, text="💡 نظام الترقيم: P_YYMM_XXX (السنة+الشهر+رقم تسلسلي)",
                             font=("Arial", 9), bg='#f0f0f0', fg='#666')
        info_label.grid(row=3, column=1, sticky='w', pady=(25, 0), padx=(10,0))

        # وصف المشروع
        tk.Label(input_frame, text="📝 وصف المشروع:",
                font=("Arial", 12), bg='#f0f0f0').grid(row=4, column=0, sticky='w', pady=5)

        description_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=description_var, width=40).grid(row=4, column=1, sticky='ew', pady=5, padx=(10,0))

        # تكوين الشبكة
        input_frame.columnconfigure(1, weight=1)

        # إطار التحقق الذكي
        check_frame = tk.Frame(project_window, bg='#f0f0f0')
        check_frame.pack(pady=20, padx=40, fill='x')

        check_label = tk.Label(check_frame, text="", font=("Arial", 10), bg='#f0f0f0')
        check_label.pack()

        # دالة التحقق الذكي
        def smart_check(*args):
            if project_number_var.get():
                if self.db.check_project_exists(project_number_var.get()):
                    check_label.config(text="⚠️ رقم المشروع موجود مسبقاً!", fg="red")
                else:
                    check_label.config(text="✅ رقم المشروع متاح", fg="green")
            else:
                check_label.config(text="")

        project_number_var.trace('w', smart_check)

        # زر الإنشاء
        tk.Button(project_window, text="🚀 إنشاء المشروع",
                 command=lambda: self.create_new_project_smart_v2(
                     client_choice_var.get(), client_type_var.get(), client_name_var.get(),
                     existing_client_var.get(), project_name_var.get(), project_number_var.get(),
                     description_var.get(), project_window),
                 font=("Arial", 14), bg='#4CAF50', fg='white',
                 width=25, height=2).pack(pady=20)

    def create_new_project_smart(self, client_type, client_name, project_name, project_number, description, window):
        """إنشاء مشروع جديد بذكاء"""
        if not all([client_type, client_name, project_name, project_number]):
            messagebox.showerror("خطأ", "يرجى ملء جميع الحقول المطلوبة")
            return

        # التحقق من وجود المشروع
        if self.db.check_project_exists(project_number):
            messagebox.showerror("خطأ", "رقم المشروع موجود مسبقاً!")
            return

        # الحصول على الهيكل النشط
        structures = self.db.get_structures()
        current_structure = next((s for s in structures if s[0] == self.current_structure_id), None)

        if not current_structure:
            messagebox.showerror("خطأ", "لم يتم العثور على الهيكل النشط")
            return

        base_path = current_structure[2]

        # تحديد المسار حسب نوع العميل
        if client_type in ["جهة رسمية", "عميل حر", "خدمات طلابية"]:
            client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "11_Clients_العملاء")
        elif client_type == "مشروع جامعي":
            client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "12_University_الجامعة")

        # التحقق من وجود العميل أو إنشاؤه
        existing_client = self.db.check_client_exists(client_name, self.current_structure_id)

        if existing_client:
            client_id = existing_client[0]
            client_folder = existing_client[0]  # سنحصل على المسار من قاعدة البيانات
        else:
            # إنشاء مجلد العميل
            client_folder = os.path.join(client_path, client_name.replace(" ", "_"))
            os.makedirs(client_folder, exist_ok=True)

            # إضافة العميل لقاعدة البيانات
            client_id = self.db.add_client(client_name, client_type, client_folder, self.current_structure_id)

            if not client_id:
                messagebox.showerror("خطأ", "فشل في إضافة العميل لقاعدة البيانات")
                return

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
- **الوصف:** {description}

## هيكل المجلدات
- **01_Admin:** عروض سعر، عقود، فواتير
- **02_Input_&_Refs:** ملفات من العميل، مراجع
- **03_Working_Files:** ملفات العمل المصدرية (PSD, AI, FIG)
- **04_Exports_&_Deliverables:** النسخ النهائية (JPG, PDF, PNG)

## ملاحظات
{description if description else '[أضف ملاحظاتك هنا]'}
"""

            readme_path = os.path.join(project_folder, "README.md")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

            # إضافة المشروع لقاعدة البيانات
            project_id = self.db.add_project(project_name, project_number, client_id, project_folder, description)

            if project_id:
                messagebox.showinfo("نجح", f"تم إنشاء المشروع '{project_name}' بنجاح!\n\nالمسار: {project_folder}\n\nتم حفظ جميع البيانات في قاعدة البيانات.")
                window.destroy()
                self.refresh_main_interface()  # تحديث الإحصائيات
            else:
                messagebox.showerror("خطأ", "فشل في حفظ المشروع في قاعدة البيانات")

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء إنشاء المشروع:\n{str(e)}")

    def create_new_project_smart_v2(self, client_choice, client_type, client_name, existing_client,
                                   project_name, project_number, description, window):
        """إنشاء مشروع جديد مع دعم العميل الجديد أو الموجود"""
        if not all([project_name, project_number]):
            messagebox.showerror("خطأ", "يرجى ملء اسم المشروع ورقم المشروع")
            return

        # التحقق من وجود المشروع
        if self.db.check_project_exists(project_number):
            messagebox.showerror("خطأ", "رقم المشروع موجود مسبقاً!")
            return

        # الحصول على الهيكل النشط
        structures = self.db.get_structures()
        current_structure = next((s for s in structures if s[0] == self.current_structure_id), None)

        if not current_structure:
            messagebox.showerror("خطأ", "لم يتم العثور على الهيكل النشط")
            return

        base_path = current_structure[2]

        try:
            if client_choice == "موجود":
                # استخدام عميل موجود
                if not existing_client:
                    messagebox.showerror("خطأ", "يرجى اختيار عميل من القائمة")
                    return

                # استخراج اسم العميل من النص المختار
                actual_client_name = existing_client.split(" (")[0]

                # البحث عن العميل في قاعدة البيانات
                clients = self.db.get_clients(self.current_structure_id)
                selected_client = next((c for c in clients if c[1] == actual_client_name), None)

                if not selected_client:
                    messagebox.showerror("خطأ", "لم يتم العثور على العميل المختار")
                    return

                client_id = selected_client[0]
                client_folder = selected_client[3]  # مسار مجلد العميل
                actual_client_type = selected_client[2]

            else:
                # إنشاء عميل جديد
                if not all([client_type, client_name]):
                    messagebox.showerror("خطأ", "يرجى ملء نوع العميل واسم العميل")
                    return

                # تحديد المسار حسب نوع العميل
                if client_type in ["جهة رسمية", "عميل حر", "خدمات طلابية"]:
                    client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "11_Clients_العملاء")
                elif client_type == "مشروع جامعي":
                    client_path = os.path.join(base_path, "10_Work_&_Study_العمل_والدراسة", "12_University_الجامعة")

                # إنشاء مجلد العميل
                client_folder = os.path.join(client_path, client_name.replace(" ", "_"))
                os.makedirs(client_folder, exist_ok=True)

                # إضافة العميل لقاعدة البيانات
                client_id = self.db.add_client(client_name, client_type, client_folder, self.current_structure_id)

                if not client_id:
                    messagebox.showerror("خطأ", "فشل في إضافة العميل لقاعدة البيانات")
                    return

                actual_client_name = client_name
                actual_client_type = client_type

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

            # إنشاء مجلد المشروع
            os.makedirs(project_folder, exist_ok=True)

            # إنشاء مجلدات المشروع الفرعية
            for subfolder in project_structure:
                subfolder_path = os.path.join(project_folder, subfolder)
                os.makedirs(subfolder_path, exist_ok=True)

            # إنشاء ملف README للمشروع
            readme_content = f"""# {project_name}

## معلومات المشروع
- **العميل:** {actual_client_name}
- **نوع العميل:** {actual_client_type}
- **رقم المشروع:** {project_number}
- **تاريخ الإنشاء:** {datetime.now().strftime('%Y-%m-%d')}
- **الوصف:** {description}

## هيكل المجلدات
- **01_Admin:** عروض سعر، عقود، فواتير
- **02_Input_&_Refs:** ملفات من العميل، مراجع
- **03_Working_Files:** ملفات العمل المصدرية (PSD, AI, FIG)
- **04_Exports_&_Deliverables:** النسخ النهائية (JPG, PDF, PNG)

## ملاحظات
{description if description else '[أضف ملاحظاتك هنا]'}
"""

            readme_path = os.path.join(project_folder, "README.md")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

            # إضافة المشروع لقاعدة البيانات
            project_id = self.db.add_project(project_name, project_number, client_id, project_folder, description)

            if project_id:
                success_msg = f"""تم إنشاء المشروع '{project_name}' بنجاح!

📁 العميل: {actual_client_name} ({actual_client_type})
🔢 رقم المشروع: {project_number}
📂 المسار: {project_folder}

تم حفظ جميع البيانات في قاعدة البيانات."""

                messagebox.showinfo("نجح", success_msg)
                window.destroy()
                self.refresh_main_interface()  # تحديث الإحصائيات
            else:
                messagebox.showerror("خطأ", "فشل في حفظ المشروع في قاعدة البيانات")

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء إنشاء المشروع:\n{str(e)}")

    def manage_projects_window(self):
        """نافذة إدارة العملاء والمشاريع"""
        manage_window = tk.Toplevel(self.root)
        manage_window.title("👥 إدارة العملاء والمشاريع")
        manage_window.geometry("1000x700")
        manage_window.configure(bg='#f0f0f0')

        # العنوان
        tk.Label(manage_window, text="👥 إدارة العملاء والمشاريع",
                font=("Arial", 16, "bold"), bg='#f0f0f0').pack(pady=20)

        # إطار التبويبات
        notebook = ttk.Notebook(manage_window)
        notebook.pack(pady=20, padx=20, fill='both', expand=True)

        # تبويب العملاء
        clients_frame = ttk.Frame(notebook)
        notebook.add(clients_frame, text="العملاء")

        # قائمة العملاء
        clients_columns = ('ID', 'الاسم', 'النوع', 'تاريخ الإنشاء')
        clients_tree = ttk.Treeview(clients_frame, columns=clients_columns, show='headings', height=15)

        for col in clients_columns:
            clients_tree.heading(col, text=col)
            clients_tree.column(col, width=150)

        clients = self.db.get_clients()
        for client in clients:
            clients_tree.insert('', 'end', values=(
                client[0], client[1], client[2], client[5][:10]
            ))

        clients_tree.pack(fill='both', expand=True, padx=10, pady=10)

        # تبويب المشاريع
        projects_frame = ttk.Frame(notebook)
        notebook.add(projects_frame, text="المشاريع")

        # قائمة المشاريع
        projects_columns = ('ID', 'اسم المشروع', 'رقم المشروع', 'العميل', 'الحالة', 'تاريخ الإنشاء')
        projects_tree = ttk.Treeview(projects_frame, columns=projects_columns, show='headings', height=15)

        for col in projects_columns:
            projects_tree.heading(col, text=col)
            projects_tree.column(col, width=120)

        projects = self.db.get_projects()
        for project in projects:
            projects_tree.insert('', 'end', values=(
                project[0], project[1], project[2], project[9], project[5], project[6][:10]
            ))

        projects_tree.pack(fill='both', expand=True, padx=10, pady=10)

    def create_filename_generator_window(self):
        """نافذة مولد أسماء الملفات الذكي والمتطور"""
        filename_window = tk.Toplevel(self.root)
        filename_window.title("🔖 مولّد أسماء الملفات الاحترافي")
        filename_window.geometry("900x800")
        filename_window.configure(bg=self.colors['bg_main'])
        filename_window.resizable(True, True)

        # إطار العنوان
        title_frame = tk.Frame(filename_window, bg=self.colors['bg_secondary'], relief='raised', bd=2)
        title_frame.pack(pady=20, padx=20, fill='x')

        tk.Label(title_frame, text="🔖 مولّد أسماء الملفات الاحترافي",
                font=self.fonts['heading'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=10)

        tk.Label(title_frame, text="نظام ذكي لتوليد أسماء ملفات احترافية ومنظمة",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['text_secondary']).pack(pady=(0, 10))

        # إطار اختيار المشروع
        project_frame = tk.Frame(filename_window, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        project_frame.pack(pady=15, padx=20, fill='x')

        tk.Label(project_frame, text="📁 ربط بمشروع موجود (اختياري)",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=(10, 5))

        project_var = tk.StringVar()
        project_menu = ttk.Combobox(project_frame, textvariable=project_var,
                                   font=self.fonts['text'], width=70, state='readonly')

        # تحميل المشاريع
        projects = self.db.get_projects()
        project_values = ["بدون مشروع"] + [f"{p[2]} - {p[1]} ({p[9]})" for p in projects]
        project_menu['values'] = project_values
        project_menu.set("بدون مشروع")
        project_menu.pack(pady=10, padx=20)

        # إطار المدخلات الرئيسية
        main_input_frame = tk.Frame(filename_window, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        main_input_frame.pack(pady=15, padx=20, fill='both', expand=True)

        tk.Label(main_input_frame, text="📝 معلومات الملف",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=(15, 10))

        # إطار الشبكة للمدخلات
        grid_frame = tk.Frame(main_input_frame, bg=self.colors['bg_secondary'])
        grid_frame.pack(pady=10, padx=20, fill='x')

        # التاريخ
        tk.Label(grid_frame, text="📅 التاريخ (YYYY-MM-DD):",
                font=self.fonts['text'], bg=self.colors['bg_secondary']).grid(row=0, column=0, sticky='w', pady=8)

        date_var = tk.StringVar(value=datetime.today().strftime('%Y-%m-%d'))
        date_entry = tk.Entry(grid_frame, textvariable=date_var, font=self.fonts['text'],
                             width=20, relief='solid', bd=1)
        date_entry.grid(row=0, column=1, sticky='ew', pady=8, padx=(10, 0))

        # النوع
        tk.Label(grid_frame, text="📂 نوع الملف:",
                font=self.fonts['text'], bg=self.colors['bg_secondary']).grid(row=1, column=0, sticky='w', pady=8)

        type_var = tk.StringVar()
        type_menu = ttk.Combobox(grid_frame, textvariable=type_var, font=self.fonts['text'],
                                width=18, state='readonly')
        type_menu['values'] = ("Report", "Invoice", "Proposal", "HW", "Lecture", "Research",
                              "Design", "Tutorial", "Presentation", "Contract", "Analysis")
        type_menu.grid(row=1, column=1, sticky='ew', pady=8, padx=(10, 0))

        # العميل - المشروع
        tk.Label(grid_frame, text="👤 العميل/المشروع:",
                font=self.fonts['text'], bg=self.colors['bg_secondary']).grid(row=2, column=0, sticky='w', pady=8)

        client_var = tk.StringVar()
        client_entry = tk.Entry(grid_frame, textvariable=client_var, font=self.fonts['text'],
                               width=20, relief='solid', bd=1)
        client_entry.grid(row=2, column=1, sticky='ew', pady=8, padx=(10, 0))

        # وصف موجز
        tk.Label(grid_frame, text="📝 وصف موجز:",
                font=self.fonts['text'], bg=self.colors['bg_secondary']).grid(row=3, column=0, sticky='w', pady=8)

        desc_var = tk.StringVar()
        desc_entry = tk.Entry(grid_frame, textvariable=desc_var, font=self.fonts['text'],
                             width=20, relief='solid', bd=1)
        desc_entry.grid(row=3, column=1, sticky='ew', pady=8, padx=(10, 0))

        # رقم الإصدار
        tk.Label(grid_frame, text="🧮 رقم الإصدار:",
                font=self.fonts['text'], bg=self.colors['bg_secondary']).grid(row=4, column=0, sticky='w', pady=8)

        version_var = tk.StringVar(value="v01")
        version_menu = ttk.Combobox(grid_frame, textvariable=version_var, font=self.fonts['text'],
                                   width=18, values=("v01", "v02", "v03", "v04", "v05", "vFINAL", "vDRAFT"))
        version_menu.grid(row=4, column=1, sticky='ew', pady=8, padx=(10, 0))

        # الامتداد
        tk.Label(grid_frame, text="📁 امتداد الملف:",
                font=self.fonts['text'], bg=self.colors['bg_secondary']).grid(row=5, column=0, sticky='w', pady=8)

        ext_var = tk.StringVar(value="pdf")
        ext_menu = ttk.Combobox(grid_frame, textvariable=ext_var, font=self.fonts['text'],
                               width=18, state='readonly')
        ext_menu['values'] = ("pdf", "docx", "xlsx", "pptx", "zip", "ai", "psd", "fig",
                             "mp4", "png", "jpg", "jpeg", "svg", "txt", "md")
        ext_menu.grid(row=5, column=1, sticky='ew', pady=8, padx=(10, 0))

        # تكوين الشبكة
        grid_frame.columnconfigure(1, weight=1)

        # إطار المعاينة والنتيجة
        preview_frame = tk.Frame(filename_window, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        preview_frame.pack(pady=15, padx=20, fill='x')

        tk.Label(preview_frame, text="👁️ معاينة اسم الملف",
                font=self.fonts['text'], bg=self.colors['bg_secondary'],
                fg=self.colors['primary']).pack(pady=(15, 10))

        # النتيجة مع زر نسخ سريع
        result_frame = tk.Frame(preview_frame, bg='white', relief='solid', bd=1)
        result_frame.pack(pady=10, padx=20, fill='x')

        # إطار النتيجة والزر
        result_content_frame = tk.Frame(result_frame, bg='white')
        result_content_frame.pack(fill='x', pady=10)

        result_label = tk.Label(result_content_frame, text="", font=('Times New Roman', 12, 'bold'),
                               bg='white', fg=self.colors['info'], wraplength=650, justify='center')
        result_label.pack(side='left', fill='x', expand=True, padx=(10, 5))

        # زر نسخ سريع صغير
        quick_copy_btn = tk.Button(result_content_frame, text="📋",
                                  command=lambda: self.quick_copy_filename(result_label, quick_copy_btn),
                                  font=('Times New Roman', 10), bg=self.colors['info'], fg='white',
                                  width=3, height=1, relief='raised', bd=1)
        quick_copy_btn.pack(side='right', padx=(5, 10))

        # تلميح للزر السريع
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text="نسخ سريع", font=('Times New Roman', 9),
                           bg='black', fg='white', relief='solid', bd=1)
            label.pack()
            quick_copy_btn.tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(quick_copy_btn, 'tooltip'):
                quick_copy_btn.tooltip.destroy()

        quick_copy_btn.bind("<Enter>", show_tooltip)
        quick_copy_btn.bind("<Leave>", hide_tooltip)

        # إطار الأمثلة
        examples_frame = tk.Frame(preview_frame, bg=self.colors['bg_secondary'])
        examples_frame.pack(pady=10, padx=20, fill='x')

        tk.Label(examples_frame, text="💡 أمثلة على التسمية:",
                font=self.fonts['small'], bg=self.colors['bg_secondary'],
                fg=self.colors['text_secondary']).pack()

        examples_text = """2024-11-15_Report_SanaaUni_Admission-Analysis_v02.pdf
2024-10-28_Design_NahdaCo_Logo-Concepts_v03.ai
2025-01-20_Research_ScienceUni_Eco-Impact-Study_vFINAL.docx"""

        tk.Label(examples_frame, text=examples_text, font=('Courier New', 9),
                bg=self.colors['bg_secondary'], fg=self.colors['text_secondary']).pack(pady=5)

        # دالة التحديث التلقائي
        def update_filename(*args):
            self.generate_filename_smart(date_var, type_var, client_var, desc_var,
                                       version_var, ext_var, result_label)

        # ربط التحديث التلقائي
        for var in [date_var, type_var, client_var, desc_var, version_var, ext_var]:
            var.trace_add('write', update_filename)

        # دالة ملء البيانات من المشروع
        def fill_from_project(*args):
            selected = project_var.get()
            if selected != "بدون مشروع":
                # استخراج رقم المشروع واسم العميل
                project_number = selected.split(" - ")[0]
                project_data = next((p for p in projects if p[2] == project_number), None)
                if project_data:
                    client_var.set(project_data[9].replace(" ", ""))  # اسم العميل

        project_var.trace_add('write', fill_from_project)

        # إطار الأزرار
        buttons_frame = tk.Frame(filename_window, bg=self.colors['bg_main'])
        buttons_frame.pack(pady=20)

        # زر التوليد اليدوي
        generate_btn = tk.Button(buttons_frame, text="🚀 توليد الاسم",
                                command=lambda: update_filename(),
                                font=self.fonts['button'], bg=self.colors['warning'], fg='white',
                                width=20, height=2, relief='raised', bd=3)
        generate_btn.pack(side='left', padx=10)

        # زر النسخ المحسن
        copy_btn = tk.Button(buttons_frame, text="📋 نسخ إلى الحافظة",
                            command=lambda: self.copy_filename_to_clipboard_enhanced(result_label, filename_window, copy_btn),
                            font=self.fonts['button'], bg=self.colors['success'], fg='white',
                            width=20, height=2, relief='raised', bd=3,
                            activebackground='#229954', activeforeground='white')
        copy_btn.pack(side='left', padx=10)

        # إضافة تأثير hover للزر
        copy_btn.bind("<Enter>", lambda e: copy_btn.config(bg='#229954'))
        copy_btn.bind("<Leave>", lambda e: copy_btn.config(bg=self.colors['success']))

        # زر الحفظ في قاعدة البيانات
        save_btn = tk.Button(buttons_frame, text="💾 حفظ في قاعدة البيانات",
                            command=lambda: self.save_generated_filename(result_label, project_var, type_var),
                            font=self.fonts['button'], bg=self.colors['info'], fg='white',
                            width=25, height=2, relief='raised', bd=3)
        save_btn.pack(side='left', padx=10)

        # زر إغلاق
        close_btn = tk.Button(buttons_frame, text="❌ إغلاق",
                             command=filename_window.destroy,
                             font=self.fonts['button'], bg=self.colors['danger'], fg='white',
                             width=15, height=2, relief='raised', bd=3)
        close_btn.pack(side='left', padx=10)

        # توليد اسم أولي
        update_filename()

    def generate_filename_smart(self, date_var, type_var, client_var, desc_var, version_var, ext_var, result_label):
        """توليد اسم الملف الذكي حسب القواعد الاحترافية"""
        try:
            # الحصول على القيم
            date = date_var.get() or datetime.today().strftime('%Y-%m-%d')
            file_type = type_var.get()
            client_project = client_var.get().strip().replace(" ", "")
            brief_desc = desc_var.get().strip().replace(" ", "-")
            version = version_var.get()
            extension = ext_var.get()

            # التحقق من الحقول المطلوبة
            if not file_type:
                result_label.config(text="⚠️ يرجى اختيار نوع الملف", fg="red")
                return

            if not client_project:
                result_label.config(text="⚠️ يرجى إدخال اسم العميل/المشروع", fg="red")
                return

            if not brief_desc:
                result_label.config(text="⚠️ يرجى إدخال وصف موجز", fg="red")
                return

            # تطبيق قواعد التسمية الخاصة
            if file_type == "Lecture":
                # للمحاضرات: Lec[رقم]_[المادة]_[الموضوع].[امتداد]
                if brief_desc.startswith("Lec") or brief_desc.startswith("lec"):
                    filename = f"{brief_desc}_{client_project}.{extension}"
                else:
                    filename = f"Lec01_{client_project}_{brief_desc}.{extension}"
            elif file_type == "Tutorial":
                # للشروحات: Tutorial_[الموضوع]_[التفاصيل]_[الإصدار].[امتداد]
                filename = f"Tutorial_{client_project}_{brief_desc}_{version}.{extension}"
            else:
                # القاعدة العامة: YYYY-MM-DD_[النوع]_[العميل-المشروع]_[وصف_موجز]_vXX.[الامتداد]
                filename = f"{date}_{file_type}_{client_project}_{brief_desc}_{version}.{extension}"

            # عرض النتيجة
            result_label.config(text=filename, fg=self.colors['info'])

        except Exception as e:
            result_label.config(text=f"❌ خطأ: {str(e)}", fg="red")

    def copy_filename_to_clipboard(self, result_label, window):
        """نسخ اسم الملف إلى الحافظة"""
        text = result_label.cget("text")
        if text and not text.startswith("⚠️") and not text.startswith("❌"):
            window.clipboard_clear()
            window.clipboard_append(text)
            window.update()
            messagebox.showinfo("تم النسخ", f"تم نسخ اسم الملف إلى الحافظة:\n\n{text}")
        else:
            messagebox.showwarning("تحذير", "لا يوجد اسم ملف صحيح للنسخ")

    def copy_filename_to_clipboard_enhanced(self, result_label, window, copy_btn):
        """نسخ اسم الملف إلى الحافظة مع تأثيرات بصرية محسنة"""
        text = result_label.cget("text")
        if text and not text.startswith("⚠️") and not text.startswith("❌"):
            # تأثير بصري للزر
            original_text = copy_btn.cget("text")
            original_bg = copy_btn.cget("bg")

            # تغيير مؤقت للزر
            copy_btn.config(text="✅ تم النسخ!", bg='#2ecc71')
            window.update()

            # نسخ النص
            window.clipboard_clear()
            window.clipboard_append(text)
            window.update()

            # إظهار رسالة نجاح مخصصة
            success_window = tk.Toplevel(window)
            success_window.title("✅ تم النسخ بنجاح")
            success_window.geometry("500x200")
            success_window.configure(bg=self.colors['bg_secondary'])
            success_window.resizable(False, False)

            # توسيط النافذة
            success_window.transient(window)
            success_window.grab_set()

            # محتوى النافذة
            tk.Label(success_window, text="✅ تم نسخ اسم الملف بنجاح!",
                    font=self.fonts['heading'], bg=self.colors['bg_secondary'],
                    fg=self.colors['success']).pack(pady=20)

            # إطار النص المنسوخ
            text_frame = tk.Frame(success_window, bg='white', relief='solid', bd=1)
            text_frame.pack(pady=10, padx=20, fill='x')

            tk.Label(text_frame, text=text, font=('Times New Roman', 11, 'bold'),
                    bg='white', fg=self.colors['primary'], wraplength=450).pack(pady=10)

            # زر إغلاق
            tk.Button(success_window, text="👍 ممتاز",
                     command=success_window.destroy,
                     font=self.fonts['button'], bg=self.colors['success'], fg='white',
                     width=15, height=1).pack(pady=20)

            # إعادة الزر لحالته الأصلية بعد ثانيتين
            def reset_button():
                copy_btn.config(text=original_text, bg=original_bg)

            window.after(2000, reset_button)

        else:
            # تأثير بصري للخطأ
            original_text = copy_btn.cget("text")
            original_bg = copy_btn.cget("bg")

            copy_btn.config(text="❌ لا يوجد نص!", bg=self.colors['danger'])
            window.update()

            # إعادة الزر لحالته الأصلية بعد ثانيتين
            def reset_button_error():
                copy_btn.config(text=original_text, bg=original_bg)

            window.after(2000, reset_button_error)

            messagebox.showwarning("تحذير", "لا يوجد اسم ملف صحيح للنسخ\nيرجى توليد اسم ملف أولاً")

    def quick_copy_filename(self, result_label, quick_copy_btn):
        """نسخ سريع لاسم الملف مع تأثير بصري مصغر"""
        text = result_label.cget("text")
        if text and not text.startswith("⚠️") and not text.startswith("❌"):
            # تأثير بصري سريع
            original_text = quick_copy_btn.cget("text")
            original_bg = quick_copy_btn.cget("bg")

            quick_copy_btn.config(text="✓", bg='#2ecc71')
            quick_copy_btn.update()

            # نسخ النص
            quick_copy_btn.clipboard_clear()
            quick_copy_btn.clipboard_append(text)
            quick_copy_btn.update()

            # إعادة الزر لحالته الأصلية بعد ثانية واحدة
            def reset_quick_button():
                quick_copy_btn.config(text=original_text, bg=original_bg)

            quick_copy_btn.after(1000, reset_quick_button)

        else:
            # تأثير بصري للخطأ
            original_text = quick_copy_btn.cget("text")
            original_bg = quick_copy_btn.cget("bg")

            quick_copy_btn.config(text="✗", bg=self.colors['danger'])
            quick_copy_btn.update()

            # إعادة الزر لحالته الأصلية
            def reset_quick_button_error():
                quick_copy_btn.config(text=original_text, bg=original_bg)

            quick_copy_btn.after(1000, reset_quick_button_error)

    def save_generated_filename(self, result_label, project_var, type_var):
        """حفظ اسم الملف المولد في قاعدة البيانات"""
        filename = result_label.cget("text")
        if not filename or filename.startswith("⚠️") or filename.startswith("❌"):
            messagebox.showwarning("تحذير", "لا يوجد اسم ملف صحيح للحفظ")
            return

        # تحديد المشروع
        project_id = None
        selected_project = project_var.get()
        if selected_project != "بدون مشروع":
            project_number = selected_project.split(" - ")[0]
            projects = self.db.get_projects()
            project_data = next((p for p in projects if p[2] == project_number), None)
            if project_data:
                project_id = project_data[0]

        # حفظ في قاعدة البيانات
        try:
            self.db.add_generated_file(filename, project_id, type_var.get())
            messagebox.showinfo("تم الحفظ", f"تم حفظ اسم الملف في قاعدة البيانات:\n\n{filename}")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في حفظ اسم الملف:\n{str(e)}")

    def show_filename_examples_window(self):
        """نافذة عرض أمثلة التسمية"""
        examples_window = tk.Toplevel(self.root)
        examples_window.title("💡 أمثلة على قواعد التسمية")
        examples_window.geometry("900x600")
        examples_window.configure(bg=self.colors['bg_main'])

        # العنوان
        tk.Label(examples_window, text="💡 أمثلة شاملة على قواعد التسمية الاحترافية",
                font=self.fonts['heading'], bg=self.colors['bg_main'],
                fg=self.colors['primary']).pack(pady=20)

        # إطار الأمثلة
        examples_frame = tk.Frame(examples_window, bg=self.colors['bg_secondary'], relief='groove', bd=2)
        examples_frame.pack(pady=20, padx=20, fill='both', expand=True)

        # نص الأمثلة
        examples_text = tk.Text(examples_frame, font=('Times New Roman', 11),
                               bg='white', wrap='word', relief='solid', bd=1)
        examples_text.pack(pady=15, padx=15, fill='both', expand=True)

        examples_content = """📋 قواعد التسمية الاحترافية

⚙️ القاعدة العامة:
YYYY-MM-DD_[النوع]_[العميل-المشروع]_[وصف_موجز]_vXX.[الامتداد]

📘 أمثلة تفصيلية:

🏢 العمل الرسمي:
• 2024-11-15_Report_SanaaUni_Admission-Analysis_v02.pdf
  (تقرير بتاريخ 15 نوفمبر، لجامعة صنعاء، عن تحليل القبول، الإصدار الثاني)

• 2024-12-01_Proposal_MinistryEducation_Digital-Transformation_v01.docx
  (اقتراح بتاريخ 1 ديسمبر، لوزارة التعليم، عن التحول الرقمي، الإصدار الأول)

💼 العمل الحر:
• 2024-10-28_Design_NahdaCo_Logo-Concepts_v03.ai
  (تصميم بتاريخ 28 أكتوبر، لشركة النهضة، مقترحات شعار، الإصدار الثالث)

• 2024-11-20_Invoice_TechStartup_INV-045_vFINAL.pdf
  (فاتورة بتاريخ 20 نوفمبر، لشركة تقنية ناشئة، رقم الفاتورة 045، النسخة النهائية)

🎓 الخدمات الطلابية:
• 2025-01-20_Research_ScienceUni_Eco-Impact-Study_vFINAL.docx
  (بحث بتاريخ 20 يناير، لجامعة العلوم، عن الأثر البيئي، النسخة النهائية)

• 2024-12-15_Presentation_EngineeringCollege_Graduation-Project_v02.pptx
  (عرض تقديمي بتاريخ 15 ديسمبر، لكلية الهندسة، مشروع التخرج، الإصدار الثاني)

📚 الدراسة (واجبات):
• 2024-09-30_HW_CS101_OOP-Assignment_v01.zip
  (واجب بتاريخ 30 سبتمبر، لمادة CS101، عن البرمجة الكائنية، الإصدار الأول)

• 2024-11-10_HW_MATH201_Calculus-Problems_v02.pdf
  (واجب بتاريخ 10 نوفمبر، لمادة الرياضيات 201، مسائل التفاضل، الإصدار الثاني)

🎓 الدراسة (محاضرات) - قاعدة خاصة:
• Lec03_CS101_Data-Structures.pdf
  (المحاضرة رقم 3، لمادة CS101، عن هياكل البيانات - بدون تاريخ)

• Lec15_PHYS102_Quantum-Mechanics.pptx
  (المحاضرة رقم 15، لمادة الفيزياء 102، عن ميكانيكا الكم)

💰 الفواتير والمالية:
• 2024-11-01_Invoice_NahdaCo_INV-023_vFINAL.pdf
  (فاتورة بتاريخ 1 نوفمبر، لشركة النهضة، رقم الفاتورة 023، النسخة النهائية)

• 2024-10-25_Contract_TechSolutions_Service-Agreement_v01.docx
  (عقد بتاريخ 25 أكتوبر، لشركة الحلول التقنية، اتفاقية خدمة، الإصدار الأول)

🎥 الشروحات والتعليم - قاعدة خاصة:
• Tutorial_Flutter_State-Management-Riverpod_v01.mp4
  (شرح عن Flutter، لموضوع إدارة الحالة، الإصدار الأول - بدون تاريخ)

• Tutorial_Python_Web-Scraping-BeautifulSoup_vFINAL.mp4
  (شرح عن Python، لموضوع استخراج البيانات، النسخة النهائية)

🎨 التصميم والإبداع:
• 2024-11-25_Design_CafeChain_Menu-Layout_v04.psd
  (تصميم بتاريخ 25 نوفمبر، لسلسلة مقاهي، تخطيط القائمة، الإصدار الرابع)

• 2024-12-05_Design_EventCompany_Wedding-Invitation_vFINAL.ai
  (تصميم بتاريخ 5 ديسمبر، لشركة فعاليات، دعوة زفاف، النسخة النهائية)

📊 التحليل والتقارير:
• 2024-11-30_Analysis_RetailChain_Sales-Performance-Q4_v01.xlsx
  (تحليل بتاريخ 30 نوفمبر، لسلسلة تجارية، أداء المبيعات للربع الرابع، الإصدار الأول)

• 2024-12-10_Report_HealthMinistry_COVID-Impact-Assessment_vFINAL.pdf
  (تقرير بتاريخ 10 ديسمبر، لوزارة الصحة، تقييم تأثير كوفيد، النسخة النهائية)

💡 نصائح مهمة:
• استخدم التاريخ في البداية للفرز الزمني المثالي
• اختر أسماء مختصرة وواضحة للعملاء
• استخدم الشرطة (-) بدلاً من المسافات في الوصف
• رقم الإصدار مهم جداً لتجنب الخلط بين النسخ
• استخدم vFINAL للنسخة النهائية المعتمدة"""

        examples_text.insert('1.0', examples_content)
        examples_text.config(state='disabled')

        # زر إغلاق
        tk.Button(examples_window, text="❌ إغلاق",
                 command=examples_window.destroy,
                 font=self.fonts['button'], bg=self.colors['danger'], fg='white',
                 width=15, height=2).pack(pady=20)

    def show_reports_window(self):
        """نافذة التقارير والإحصائيات"""
        reports_window = tk.Toplevel(self.root)
        reports_window.title("📈 تقارير وإحصائيات")
        reports_window.geometry("800x600")
        reports_window.configure(bg='#f0f0f0')

        # العنوان
        tk.Label(reports_window, text="📈 تقارير وإحصائيات",
                font=("Arial", 16, "bold"), bg='#f0f0f0').pack(pady=20)

        # إحصائيات سريعة
        stats_frame = tk.Frame(reports_window, bg='#f0f0f0')
        stats_frame.pack(pady=20, padx=40, fill='x')

        structures = self.db.get_structures()
        clients = self.db.get_clients()
        projects = self.db.get_projects()

        stats_text = f"""📊 إحصائيات عامة:

🏗️ عدد الهياكل: {len(structures)}
👥 عدد العملاء: {len(clients)}
📁 عدد المشاريع: {len(projects)}
📈 متوسط المشاريع لكل عميل: {len(projects)/len(clients) if clients else 0:.1f}
        """

        tk.Label(stats_frame, text=stats_text,
                font=("Arial", 12), bg='#f0f0f0', justify='left').pack(anchor='w')

        # زر إغلاق
        tk.Button(reports_window, text="إغلاق",
                 command=reports_window.destroy,
                 font=("Arial", 12), bg='#f44336', fg='white').pack(pady=20)

    def run(self):
        """تشغيل البرنامج"""
        self.root.mainloop()

# تشغيل البرنامج
if __name__ == "__main__":
    app = ProjectOrganizer()
    app.run()
