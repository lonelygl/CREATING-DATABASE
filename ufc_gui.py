# ufc_gui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
from database import Database, Record

DB_DEFAULT = 'ufc_db.bin'

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('UFC File DB')
        self.geometry('1000x600')
        self.db = Database(DB_DEFAULT)
        if not os.path.exists(DB_DEFAULT):
            try:
                self.db.create()
            except Exception:
                pass
        try:
            self.db.open()
        except Exception:
            pass

        self._combomap = {}
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=8, pady=8)

        left = ttk.Frame(frm)
        left.pack(side='left', fill='y', padx=4)

        labels = ['id','date(YYYY-MM-DD)','fight_time(MM:SS)','event','location','fighter_1','fighter_2','winner']
        self.entries = {}
        for i,lab in enumerate(labels):
            ttk.Label(left, text=lab).grid(row=i, column=0, sticky='w', pady=2)
            e = ttk.Entry(left, width=20)
            e.grid(row=i, column=1, pady=2)
            self.entries[lab.split('(')[0]] = e

        ttk.Button(left, text='Add record', command=self.add_record).grid(row=9, column=0, columnspan=2, pady=6, sticky='ew')

        ttk.Separator(left, orient='horizontal').grid(row=10, column=0, columnspan=2, sticky='ew', pady=8)

        ttk.Button(left, text='Create DB', command=self.create_db).grid(row=11, column=0, columnspan=2, pady=4, sticky='ew')
        ttk.Button(left, text='Delete DB', command=self.delete_db).grid(row=12, column=0, columnspan=2, pady=4, sticky='ew')
        ttk.Button(left, text='Clear DB', command=self._clear_db).grid(row=13, column=0, columnspan=2, pady=4, sticky='ew')
        ttk.Button(left, text='Backup DB', command=self.backup).grid(row=14, column=0, columnspan=2, pady=4, sticky='ew')
        ttk.Button(left, text='Restore DB', command=self.restore).grid(row=15, column=0, columnspan=2, pady=4, sticky='ew')
        ttk.Button(left, text='Import JSON', command=self.import_json).grid(row=16, column=0, columnspan=2, pady=4, sticky='ew')
        ttk.Button(left, text='Export Excel', command=self.export_excel).grid(row=17, column=0, columnspan=2, pady=4, sticky='ew')

        sel_frame = ttk.LabelFrame(left, text='Select specific record')
        sel_frame.grid(row=18, column=0, columnspan=2, pady=8, sticky='ew')
        self.select_combo = ttk.Combobox(sel_frame, state='readonly', width=35)
        self.select_combo.pack(side='top', padx=4, pady=4)
        ttk.Button(sel_frame, text='Refresh list', command=self._refresh_combo).pack(side='top', padx=4, pady=2, fill='x')
        ttk.Button(sel_frame, text='Edit selected', command=self.edit_selected).pack(side='top', padx=4, pady=2, fill='x')
        ttk.Button(sel_frame, text='Delete selected', command=self.delete_selected).pack(side='top', padx=4, pady=2, fill='x')

        right = ttk.Frame(frm)
        right.pack(side='right', fill='both', expand=True)

        searchfrm = ttk.Frame(right)
        searchfrm.pack(fill='x', pady=6)
        self.search_field = tk.StringVar(value='fighter_1')
        fields = ['id','date','fight_time','event','location','fighter_1','fighter_2','winner']
        ttk.Label(searchfrm, text='Search field').pack(side='left')
        self.search_combo = ttk.Combobox(searchfrm, values=fields, textvariable=self.search_field, width=12)
        self.search_combo.pack(side='left', padx=4)
        self.search_value = ttk.Entry(searchfrm, width=20)
        self.search_value.pack(side='left', padx=4)
        ttk.Button(searchfrm, text='Search', command=self.search).pack(side='left', padx=4)
        ttk.Button(searchfrm, text='Search & Delete matches', command=self.search_and_delete).pack(side='left', padx=4)

        cols = ['id','date','fight_time','event','location','fighter_1','fighter_2','winner']
        self.tree = ttk.Treeview(right, columns=cols, show='headings', selectmode='browse')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110, anchor='center')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', self.on_tree_double)

        ttk.Button(right, text='Refresh Table', command=self._refresh_list).pack(pady=6)

    # --- basic DB ops ---
    def create_db(self):
        if os.path.exists(self.db.filepath):
            if not messagebox.askyesno('confirm','Database exists. Overwrite?'):
                return
        try:
            self.db.create(overwrite=True)
            self.db.open()
            messagebox.showinfo('ok','Database created')
            self._refresh_list(); self._refresh_combo()
        except Exception as e:
            messagebox.showerror('error', str(e))

    def delete_db(self):
        if messagebox.askyesno('confirm','Delete database file and index?'):
            try:
                self.db.delete()
                messagebox.showinfo('ok','Database deleted')
                self.db = Database(DB_DEFAULT)
                self._refresh_list(); self._refresh_combo()
            except Exception as e:
                messagebox.showerror('error', str(e))

    def add_record(self):
        try:
            data = {k: e.get().strip() for k,e in self.entries.items()}
            user_id = int(data['id']) if data['id'].isdigit() else 0
            rec = Record(user_id,
                         data['date'] or '0000-00-00',
                         data['fight_time'] or '00:00',
                         data['event'],
                         data['location'],
                         data['fighter_1'],
                         data['fighter_2'],
                         data['winner'])
            assigned = self.db.add(rec)
            messagebox.showinfo('ok', f'added — assigned id {assigned}')
            self._refresh_list(); self._refresh_combo()
        except Exception as e:
            messagebox.showerror('error', str(e))

    def _clear_db(self):
        if messagebox.askyesno('confirm','Clear all records?'):
            try:
                self.db.clear()
                self._refresh_list(); self._refresh_combo()
            except Exception as e:
                messagebox.showerror('error', str(e))

    def backup(self):
        path = filedialog.asksaveasfilename(defaultextension='.bak', title="Save backup as")
        if not path:
            return
        try:
            self.db.backup(path)
            messagebox.showinfo('ok', 'Backup saved')
        except Exception as e:
            messagebox.showerror('error', f'Backup failed: {str(e)}')

    def restore(self):
        path = filedialog.askopenfilename(
            filetypes=[('Backup files', '*.bak'), ('All files', '*.*')],
            title="Select backup file to restore"
        )
        if not path:
            return
        try:

            if hasattr(self.db, 'file') and self.db.file:
                self.db.close()

            self.db.restore_from_backup(path)

            self.db.open()
            messagebox.showinfo('ok', 'Database restored')
            self._refresh_list()
            self._refresh_combo()
        except Exception as e:
            messagebox.showerror('error', f'Restore failed: {str(e)}')

            try:
                self.db.open()
            except:
                pass

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[('JSON files','*.json')])
        if not path:
            return
        try:
            n = self.db.import_json(path)
            messagebox.showinfo('ok', f'Imported {n}')
            self._refresh_list(); self._refresh_combo()
        except Exception as e:
            messagebox.showerror('error', str(e))

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension='.xlsx', filetypes=[('Excel files','*.xlsx')])
        if not path:
            return
        try:
            n = self.db.export_excel(path)
            messagebox.showinfo('ok', f'Exported {n} records')
        except Exception as e:
            messagebox.showerror('error', str(e))

    # --- Search & Delete ---
    def search(self):
        field = self.search_field.get()
        value = self.search_value.get().strip()
        if not value:
            messagebox.showwarning('warn','Enter value'); return
        results = self.db.search(field, value)
        self._show_results(results)

    def search_and_delete(self):
        field = self.search_field.get()
        value = self.search_value.get().strip()
        if not value:
            messagebox.showwarning('warn','Enter value'); return
        if not messagebox.askyesno('confirm', f'Delete all where {field} == {value}?'):
            return
        try:
            n = self.db.delete_by_field(field, value)
            messagebox.showinfo('ok', f'Deleted {n}')
            self._refresh_list(); self._refresh_combo()
        except Exception as e:
            messagebox.showerror('error', str(e))

    # --- Combo-based selection ---
    def _refresh_combo(self):
        items = []
        cmap = {}
        try:
            for r in self.db.iterate():
                label = f"{r.id}: {r.fighter_1} vs {r.fighter_2} ({r.date})"
                items.append(label)
                cmap[label] = r.id
        except Exception:
            items = []; cmap = {}
        self._combomap = cmap
        self.select_combo['values'] = items
        if items:
            self.select_combo.current(0)
        else:
            self.select_combo.set('')

    def edit_selected(self):
        sel = self.select_combo.get()
        if not sel:
            messagebox.showwarning('warn','No record selected'); return
        rid = self._combomap.get(sel)
        if rid is None:
            messagebox.showerror('error','Record not found'); return
        rec = self.db.get_by_id(rid)
        if not rec:
            messagebox.showerror('error','Record not found'); return
        self._open_edit_window(rec)

    def delete_selected(self):
        sel = self.select_combo.get()
        if not sel:
            messagebox.showwarning('warn','No record selected'); return
        rid = self._combomap.get(sel)
        if rid is None:
            messagebox.showerror('error','Record not found'); return
        if not messagebox.askyesno('confirm', f'Delete record id {rid}?'):
            return
        try:
            self.db.delete_by_id(rid)
            messagebox.showinfo('ok', 'Deleted')
            self._refresh_list(); self._refresh_combo()
        except Exception as e:
            messagebox.showerror('error', str(e))

    def _open_edit_window(self, record):
        win = tk.Toplevel(self)
        win.title(f'Edit record {record.id}')
        win.geometry('400x360')
        fields = ['date','fight_time','event','location','fighter_1','fighter_2','winner']
        entries = {}
        for i,f in enumerate(fields):
            ttk.Label(win, text=f).grid(row=i, column=0, sticky='w', padx=8, pady=4)
            e = ttk.Entry(win, width=35)
            e.grid(row=i, column=1, padx=8, pady=4)
            e.insert(0, str(getattr(record, f)))
            entries[f] = e

        def save_changes():
            kwargs = {}
            for f,e in entries.items():
                v = e.get().strip()
                if v != getattr(record, f):
                    kwargs[f] = v
            if not kwargs:
                messagebox.showinfo('info','No changes made'); return
            try:
                self.db.edit(record.id, **kwargs)
                messagebox.showinfo('ok','Record updated')
                win.destroy()
                self._refresh_list(); self._refresh_combo()
            except Exception as ex:
                messagebox.showerror('error', str(ex))

        ttk.Button(win, text='Save changes', command=save_changes).grid(row=len(fields), column=0, columnspan=2, pady=12)

    def _show_results(self, results):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in results:
            self.tree.insert('', 'end', values=(r.id, r.date, r.fight_time, r.event, r.location, r.fighter_1, r.fighter_2, r.winner))

    def _refresh_list(self):
        try:
            items = list(self.db.iterate())
        except Exception:
            items = []
        self._show_results(items)
        self._refresh_combo()

    def on_tree_double(self, event):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])['values']
        keys = ['id','date','fight_time','event','location','fighter_1','fighter_2','winner']
        for k,v in zip(keys, vals):
            if k in self.entries:
                self.entries[k].delete(0, 'end')
                self.entries[k].insert(0, str(v))

if __name__ == '__main__':
    app = App()
    app.mainloop()
