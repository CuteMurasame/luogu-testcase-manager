#!/usr/bin/env python3
"""
Testcase Manager GUI

Features:
- Choose a directory and scan for matching pairs of *.in and *.ans files (matching by basename).
- List each pair as an item with properties: Name (*.in), timeLimit (ms), memoryLimit (kb), score, subtaskId
- Defaults: timeLimit=2000, memoryLimit=1048576, score=0, subtaskId=0
- Reorder items (move up / move down)
- Multi-select items and bulk-edit timeLimit/memoryLimit/score/subtaskId (leave blank to skip changing a field)
- Double-click an item to edit its fields individually
- Export to a YAML file with the format shown by the user

No external dependencies (uses Tkinter which is included with Python).

Run: python3 testcase_manager.py
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from typing import List, Dict

DEFAULTS = {
    'timeLimit': 2000,
    'memoryLimit': 1048576,
    'score': 0,
    'subtaskId': 0,
}


class TestcaseManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Testcase Manager')
        self.geometry('1200x600')

        self.dirpath = tk.StringVar()
        self.items: List[Dict] = []  # each item: {name, timeLimit, memoryLimit, score, subtaskId}

        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill='x', padx=8, pady=6)

        ttk.Label(top_frame, text='Directory:').pack(side='left')
        ttk.Entry(top_frame, textvariable=self.dirpath, width=60).pack(side='left', padx=6)
        ttk.Button(top_frame, text='Browse', command=self.browse_dir).pack(side='left')
        ttk.Button(top_frame, text='Scan', command=self.scan_dir).pack(side='left', padx=6)

        main_pane = ttk.Panedwindow(self, orient='horizontal')
        main_pane.pack(fill='both', expand=True, padx=8, pady=6)

        # Left: treeview list
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=3)

        columns = ('timeLimit', 'memoryLimit', 'score', 'subtaskId')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings', selectmode='extended')
        self.tree.heading('timeLimit', text='timeLimit (ms)')
        self.tree.heading('memoryLimit', text='memoryLimit (kb)')
        self.tree.heading('score', text='score')
        self.tree.heading('subtaskId', text='subtaskId')
        self.tree.column('timeLimit', width=100, anchor='center')
        self.tree.column('memoryLimit', width=120, anchor='center')
        self.tree.column('score', width=80, anchor='center')
        self.tree.column('subtaskId', width=80, anchor='center')

        # add first column for Name (we'll hack a heading by inserting as the tree's 'text')
        self.tree['show'] = 'headings'
        # To show the name, we'll insert it as the 'iid' and use the treeview's first column via a separate heading label.
        # Instead, we prepend a separate Listbox-like Label column above the tree.

        # Use a separate Treeview to show name-like column by using the '#0' column hack
        # Simpler: create a Treeview with '#0' column by setting show='tree headings'
        self.tree.config(show='tree headings')
        self.tree.heading('#0', text='Name (InputFile)')
        self.tree.column('#0', width=300)

        self.tree.pack(fill='both', expand=True, side='left')

        sb = ttk.Scrollbar(left_frame, orient='vertical', command=self.tree.yview)
        sb.pack(side='left', fill='y')
        self.tree.configure(yscrollcommand=sb.set)

        # Bindings
        self.tree.bind('<Double-1>', self.on_double_click)

        btns_frame = ttk.Frame(left_frame)
        btns_frame.pack(fill='x', pady=6)
        ttk.Button(btns_frame, text='Move Up', command=self.move_up).pack(side='top')
        ttk.Button(btns_frame, text='Move Down', command=self.move_down).pack(side='top', padx=6)
        ttk.Button(btns_frame, text='Bulk Edit...', command=self.bulk_edit).pack(side='top')
        ttk.Button(btns_frame, text='Import YAML', command=self.import_yaml).pack(side='top', padx=6)
        ttk.Button(btns_frame, text='Export YAML', command=self.export_yaml).pack(side='top')

        # Right: details & quick edit
        right_frame = ttk.Frame(main_pane, width=260)
        main_pane.add(right_frame, weight=1)

        ttk.Label(right_frame, text='Selected Item Details').pack(anchor='w', pady=(6,2))
        fields = ['timeLimit', 'memoryLimit', 'score', 'subtaskId']
        self.detail_vars = {f: tk.StringVar() for f in fields}
        for f in fields:
            frm = ttk.Frame(right_frame)
            frm.pack(fill='x', padx=6, pady=4)
            ttk.Label(frm, text=f + ':', width=12).pack(side='left')
            ttk.Entry(frm, textvariable=self.detail_vars[f]).pack(side='left', fill='x', expand=True)

        ttk.Button(right_frame, text='Apply to Selected', command=self.apply_details_to_selected).pack(padx=6, pady=8)

        # status bar
        self.status = tk.StringVar(value='Ready')
        ttk.Label(self, textvariable=self.status, relief='sunken', anchor='w').pack(fill='x', side='bottom')

    def browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.dirpath.set(d)

    def scan_dir(self):
        d = self.dirpath.get().strip()
        if not d:
            messagebox.showwarning('No directory', 'Please choose a directory first.')
            return
        if not os.path.isdir(d):
            messagebox.showerror('Not found', 'Directory does not exist.')
            return

        files = os.listdir(d)
        in_files = {os.path.splitext(f)[0]: f for f in files if f.endswith('.in')}
        ans_files = {os.path.splitext(f)[0]: f for f in files if f.endswith('.ans')}

        pairs = sorted(set(in_files.keys()) & set(ans_files.keys()))
        self.items = []
        for base in pairs:
            name = in_files[base]
            self.items.append({
                'name': name,
                'timeLimit': DEFAULTS['timeLimit'],
                'memoryLimit': DEFAULTS['memoryLimit'],
                'score': DEFAULTS['score'],
                'subtaskId': DEFAULTS['subtaskId'],
            })

        self.refresh_tree()
        self.status.set(f'Scanned directory: {d} — found {len(self.items)} matching pairs')

    def refresh_tree(self):
        # Clear
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        # Insert
        for idx, it in enumerate(self.items):
            iid = f'item_{idx}'
            self.tree.insert('', 'end', iid=iid, text=it['name'], values=(it['timeLimit'], it['memoryLimit'], it['score'], it['subtaskId']))

    def get_selected_indices(self) -> List[int]:
        sel = self.tree.selection()
        indices = [self.tree.index(iid) for iid in sel]
        return sorted(indices)

    def move_up(self):
        idxs = self.get_selected_indices()
        if not idxs:
            return
        if idxs[0] == 0:
            return
        for i in idxs:
            # swap with previous
            self.items[i-1], self.items[i] = self.items[i], self.items[i-1]
        self.refresh_tree()
        # restore selection: each selected moves up by 1
        new_selection = []
        for i in idxs:
            new_selection.append(f'item_{i-1}')
        for iid in new_selection:
            self.tree.selection_add(iid)

    def move_down(self):
        idxs = self.get_selected_indices()
        if not idxs:
            return
        n = len(self.items)
        if idxs[-1] == n-1:
            return
        for i in reversed(idxs):
            # swap with next
            self.items[i+1], self.items[i] = self.items[i], self.items[i+1]
        self.refresh_tree()
        new_selection = []
        for i in idxs:
            new_selection.append(f'item_{i+1}')
        for iid in new_selection:
            self.tree.selection_add(iid)

    def bulk_edit(self):
        idxs = self.get_selected_indices()
        if not idxs:
            messagebox.showinfo('No selection', 'Please select one or more items to bulk edit.')
            return
        dialog = BulkEditDialog(self, title='Bulk Edit', fields=['timeLimit', 'memoryLimit', 'score', 'subtaskId'])
        self.wait_window(dialog)
        if dialog.result is None:
            return
        changes = dialog.result
        # apply changes if not empty
        for i in idxs:
            for k, v in changes.items():
                if v != '':
                    try:
                        val = int(v)
                    except ValueError:
                        messagebox.showerror('Invalid value', f'Field {k} requires integer values')
                        return
                    self.items[i][k] = val
        self.refresh_tree()

    def on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        idx = self.tree.index(iid)
        it = self.items[idx]
        # open edit dialog with prefilled values
        dialog = BulkEditDialog(self, title=f'Edit {it["name"]}', fields=['timeLimit', 'memoryLimit', 'score', 'subtaskId'], prefill={
            'timeLimit': str(it['timeLimit']),
            'memoryLimit': str(it['memoryLimit']),
            'score': str(it['score']),
            'subtaskId': str(it['subtaskId']),
        }, allow_blank=False)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        changes = dialog.result
        try:
            for k, v in changes.items():
                self.items[idx][k] = int(v)
        except ValueError:
            messagebox.showerror('Invalid value', 'Please provide integer values')
            return
        self.refresh_tree()

    def apply_details_to_selected(self):
        idxs = self.get_selected_indices()
        if not idxs:
            messagebox.showinfo('No selection', 'Please select items first')
            return
        # apply non-empty detail fields
        for k, var in self.detail_vars.items():
            val = var.get().strip()
            if val == '':
                continue
            try:
                num = int(val)
            except ValueError:
                messagebox.showerror('Invalid input', f'{k} must be integer')
                return
            for i in idxs:
                self.items[i][k] = num
        self.refresh_tree()

    def export_yaml(self):
        if not self.items:
            messagebox.showinfo('Empty', 'No items to export')
            return
        fpath = filedialog.asksaveasfilename(defaultextension='.yml', filetypes=[('YAML files', '*.yml;*.yaml'), ('All files', '*.*')])
        if not fpath:
            return
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                for it in self.items:
                    # The user requested format with two-space indents
                    f.write(f"{it['name']}:\n")
                    f.write(f"  timeLimit: {int(it['timeLimit'])}\n")
                    f.write(f"  memoryLimit: {int(it['memoryLimit'])}\n")
                    f.write(f"  score: {int(it['score'])}\n")
                    f.write(f"  subtaskId: {int(it['subtaskId'])}\n\n")
            messagebox.showinfo('Exported', f'Exported YAML to {fpath}')
            self.status.set(f'Exported to {fpath}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save file: {e}')


    def import_yaml(self):
        """Import configuration from a YAML file and apply to current items by Name.
        - Updates fields for matching names
        - Optionally reorders items to match YAML order
        - Skips names not present in the current directory scan
        """
        if not self.items:
            messagebox.showinfo('No items', 'Please scan a directory first (Scan) before importing YAML.')
            return
        fpath = filedialog.askopenfilename(filetypes=[('YAML files', '*.yml;*.yaml'), ('All files', '*.*')])
        if not fpath:
            return
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            messagebox.showerror('Error', f'Failed to open file: {e}')
            return

        data, order = self._parse_yaml_simple(text)
        if not data:
            messagebox.showwarning('Empty/Unrecognized', 'No valid entries were found in the YAML file.')
            return

        name_to_idx = {it['name']: i for i, it in enumerate(self.items)}
        updated = 0
        missing = []
        invalid_values = []

        for name, fields in data.items():
            if name not in name_to_idx:
                missing.append(name)
                continue
            idx = name_to_idx[name]
            for k in ('timeLimit', 'memoryLimit', 'score', 'subtaskId'):
                if k in fields:
                    v = str(fields[k]).strip()
                    if v == '':
                        continue
                    try:
                        self.items[idx][k] = int(v)
                    except ValueError:
                        invalid_values.append((name, k, v))
            updated += 1

        # Ask whether to reorder as per YAML order
        yaml_names_in_list = [n for n in order if n in name_to_idx]
        if yaml_names_in_list:
            try:
                apply_order = messagebox.askyesno('Reorder by YAML?', 'Apply imported order to current list (unmatched remain at end)?')
            except Exception:
                apply_order = False
            if apply_order:
                present = set(yaml_names_in_list)
                remainder = [it for it in self.items if it['name'] not in present]
                new_items = [self.items[name_to_idx[n]] for n in yaml_names_in_list] + remainder
                self.items = new_items

        self.refresh_tree()

        msg = [f'Imported from: {os.path.basename(fpath)}', f'Updated items: {updated}']
        if missing:
            msg.append(f'Names not in current list: {len(missing)}')
        if invalid_values:
            # Show up to 5 examples
            examples = ', '.join([f"{n}.{k}='{v}'" for n, k, v in invalid_values[:5]])
            msg.append(f"Skipped invalid values: {len(invalid_values)} (e.g., {examples})")
        messagebox.showinfo('Import complete', '\n'.join(msg))
        self.status.set('Import complete — ' + '; '.join(msg[1:]))

    def _parse_yaml_simple(self, text: str):
        """Very small, permissive parser for the exported format.
        Returns (mapping, order). mapping: { name -> {field: value(str)} }, order is top-level key order.
        Supports lines like:
        name:

          key: value
        Ignores blank lines and lines starting with '#'.
        """
        mapping = {}
        order = []
        current = None
        for raw in text.splitlines():
            line = raw.rstrip('\n')
            if not line.strip() or line.strip().startswith('#'):
                continue
            if line[0] not in (' ', '	'):
                # Top-level key
                if ':' in line:
                    key = line.split(':', 1)[0].strip()
                    if key:
                        current = key
                        order.append(key)
                        mapping.setdefault(key, {})
                    else:
                        current = None
                else:
                    current = None
            else:
                if current is None:
                    continue
                s = line.strip()
                if ':' not in s:
                    continue
                k, v = s.split(':', 1)
                mapping[current][k.strip()] = v.strip()
        return mapping, order


class BulkEditDialog(tk.Toplevel):
    def __init__(self, parent, title='Bulk Edit', fields=None, prefill=None, allow_blank=True):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        if fields is None:
            fields = []
        if prefill is None:
            prefill = {}
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)
        self.vars = {}
        for f in fields:
            row = ttk.Frame(frm)
            row.pack(fill='x', pady=6)
            ttk.Label(row, text=f + ':', width=12).pack(side='left')
            v = tk.StringVar(value=prefill.get(f, ''))
            self.vars[f] = v
            ent = ttk.Entry(row, textvariable=v)
            ent.pack(side='left', fill='x', expand=True)
            if allow_blank:
                ttk.Label(row, text='(leave blank to keep)').pack(side='left', padx=6)

        btns = ttk.Frame(frm)
        btns.pack(fill='x', pady=(8,0))
        ttk.Button(btns, text='OK', command=self.on_ok).pack(side='right')
        ttk.Button(btns, text='Cancel', command=self.on_cancel).pack(side='right', padx=6)

        self.grab_set()
        self.wait_visibility()
        self.focus()

    def on_ok(self):
        self.result = {k: v.get().strip() for k, v in self.vars.items()}
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


if __name__ == '__main__':
    app = TestcaseManager()
    app.mainloop()
