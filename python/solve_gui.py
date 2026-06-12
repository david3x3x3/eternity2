import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import queue
import json
import os
import re
import sys
import pyopencl as cl

_COMPLETE_RE = re.compile(r'complete=([\d.]+)%')
_STATUS_LINE_RE = re.compile(r'^calls=\d+,')
_NODE_LIMIT_RE = re.compile(r'^node.?limit = (\d+)')
_STATUS_FIELDS = ['calls', 'nodes', 'active', 'found', 'remain',
                  'rate', 'time', 'mindepth', 'best', 'complete',
                  'node_limit']


def _data_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _config_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'solve_gui_config.json')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve_gui_config.json')


def _find_square_puzzles():
    puzzles = []
    pieces_dir = os.path.join(_data_dir(), 'pieces_set_1')
    if os.path.isdir(pieces_dir):
        for fname in sorted(os.listdir(pieces_dir)):
            m = re.match(r'pieces_(\d+)x(\d+)\.txt$', fname)
            if m and m.group(1) == m.group(2):
                puzzles.append(f"{m.group(1)}x{m.group(2)}_1")
    return puzzles


class SolveApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Eternity II Solver")
        self.root.geometry("800x600")
        self.process = None
        self.output_queue = queue.Queue()
        self._build_ui()
        self._populate_platforms()
        self._load_config()

    def _load_config(self):
        try:
            with open(_config_path(), 'r') as f:
                cfg = json.load(f)
        except Exception:
            return

        if 'platform' in cfg and 'device' in cfg:
            p, d = cfg['platform'], cfg['device']
            for i, (pi, di) in enumerate(self.device_map):
                if pi == p and di == d:
                    self.device_combo.current(i)
                    break

        if 'puzzle' in cfg and cfg['puzzle'] in self.puzzle_combo['values']:
            self.puzzle_var.set(cfg['puzzle'])

        for key, var in [('partial', self.partial_var), ('reporter', self.reporter_var)]:
            if key in cfg:
                var.set(cfg[key])

        if 'noreport' in cfg:
            self.noreport_var.set(cfg['noreport'])

    def _save_config(self):
        pi, di = self.device_map[self.device_combo.current()]
        cfg = {
            'platform': pi,
            'device': di,
            'puzzle': self.puzzle_var.get(),
            'partial': self.partial_var.get(),
            'reporter': self.reporter_var.get(),
            'noreport': self.noreport_var.get(),
        }
        try:
            with open(_config_path(), 'w') as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f'warning: could not save config: {e}')

    def _build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=5)

        sf = ttk.LabelFrame(top, text="Settings", padding=5)
        sf.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        for row, label in enumerate(["Device:", "Puzzle:", "Partial:", "Reporter:"]):
            ttk.Label(sf, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)

        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(sf, textvariable=self.device_var, state='readonly', width=60)
        self.device_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        self.puzzle_var = tk.StringVar()
        self.puzzle_combo = ttk.Combobox(sf, textvariable=self.puzzle_var, state='readonly', width=20)
        self.puzzle_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        self.partial_var = tk.StringVar()
        ttk.Entry(sf, textvariable=self.partial_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        self.reporter_var = tk.StringVar()
        ttk.Entry(sf, textvariable=self.reporter_var, width=20).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        self.noreport_var = tk.BooleanVar()
        ttk.Checkbutton(sf, text="Don't report results", variable=self.noreport_var).grid(
            row=4, column=1, sticky=tk.W, padx=5, pady=2)

        stf = ttk.LabelFrame(top, text="Status", padding=5)
        stf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.status_labels = {}
        cols = 2
        for i, field in enumerate(_STATUS_FIELDS):
            row, col = divmod(i, cols)
            ttk.Label(stf, text=f"{field}:").grid(row=row, column=col*2, sticky=tk.W, padx=(8, 2), pady=2)
            lbl = ttk.Label(stf, text="-", width=10, anchor=tk.W)
            lbl.grid(row=row, column=col*2+1, sticky=tk.W, padx=(0, 8), pady=2)
            self.status_labels[field] = lbl

        bf = ttk.Frame(self.root)
        bf.pack(fill=tk.X, padx=10, pady=5)

        self.start_btn = ttk.Button(bf, text="Start", command=self._start)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(bf, text="Stop", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        pf = ttk.Frame(self.root)
        pf.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(pf, variable=self.progress_var, maximum=100.0, length=200)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_label = ttk.Label(pf, text="0.00%", width=8, anchor=tk.E)
        self.progress_label.pack(side=tk.LEFT, padx=(5, 0))

        of = ttk.LabelFrame(self.root, text="Output", padding=5)
        of.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.output = scrolledtext.ScrolledText(of, state=tk.DISABLED, wrap=tk.WORD, font=('Courier', 9))
        self.output.pack(fill=tk.BOTH, expand=True)

    def _populate_platforms(self):
        self.device_map = []
        names = []
        for pi, platform in enumerate(cl.get_platforms()):
            for di, device in enumerate(platform.get_devices()):
                self.device_map.append((pi, di))
                names.append(f"{platform.name} / {device.name}")
        self.device_combo['values'] = names
        if names:
            self.device_combo.current(0)

        puzzles = _find_square_puzzles()
        self.puzzle_combo['values'] = puzzles
        if puzzles:
            default = '10x10_1'
            idx = puzzles.index(default) if default in puzzles else len(puzzles) - 1
            self.puzzle_combo.current(idx)
        self.partial_var.set('10,r')
        self.reporter_var.set('John Doe')

    def _build_args(self):
        if getattr(sys, 'frozen', False):
            args = [sys.executable]
        else:
            args = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve.py')]

        pi, di = self.device_map[self.device_combo.current()]
        args += ['--platform', str(pi), '--device', str(di)]

        puzzle = self.puzzle_var.get().strip()
        if puzzle:
            args += ['--puzzle', puzzle]

        partial = self.partial_var.get().strip()
        if partial:
            args += ['--partial', partial]

        reporter = self.reporter_var.get().strip()
        if reporter:
            args += ['--reporter', reporter]

        if self.noreport_var.get():
            args.append('--noreport')

        return args

    def _start(self):
        self._save_config()

        self.output.configure(state=tk.NORMAL)
        self.output.delete('1.0', tk.END)
        self.output.configure(state=tk.DISABLED)
        self.progress_var.set(0.0)
        self.progress_label.configure(text="0.00%")
        for lbl in self.status_labels.values():
            lbl.configure(text='-')

        self.process = subprocess.Popen(
            self._build_args(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

        threading.Thread(target=self._reader, daemon=True).start()
        self.root.after(100, self._poll)

    def _reader(self):
        for line in self.process.stdout:
            self.output_queue.put(line)
        self.process.wait()
        self.output_queue.put(None)

    @staticmethod
    def _fmt_nodes(val):
        n = int(val)
        if n <= 9999:
            return str(n)
        for suffix in ['K', 'M', 'G', 'T', 'P']:
            n /= 1000
            if n < 1000:
                s = f"{n:.1f}"
                if s.endswith('.0'):
                    s = s[:-2]
                return s + suffix
        return str(int(n))

    @staticmethod
    def _fmt_time(seconds):
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m:02d}m {s:02d}s"
        if m:
            return f"{m}m {s:02d}s"
        return f"{s}s"

    def _update_status(self, line):
        for part in line.split(','):
            key, _, val = part.partition('=')
            if key in self.status_labels:
                if key == 'nodes':
                    val = self._fmt_nodes(val)
                elif key == 'time':
                    val = self._fmt_time(val)
                self.status_labels[key].configure(text=val)
        m = _COMPLETE_RE.search(line)
        if m:
            pct = float(m.group(1))
            self.progress_var.set(pct)
            self.progress_label.configure(text=f"{pct:.2f}%")

    def _poll(self):
        while True:
            try:
                line = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if line is None:
                self._on_done()
                return
            if _STATUS_LINE_RE.match(line):
                self._update_status(line.strip())
            elif m := _NODE_LIMIT_RE.match(line):
                self.status_labels['node_limit'].configure(text=m.group(1))
            else:
                m = _COMPLETE_RE.search(line)
                if m:
                    pct = float(m.group(1))
                    self.progress_var.set(pct)
                    self.progress_label.configure(text=f"{pct:.2f}%")
                self.output.configure(state=tk.NORMAL)
                self.output.insert(tk.END, line)
                self.output.see(tk.END)
                self.output.configure(state=tk.DISABLED)
        self.root.after(100, self._poll)

    def _on_done(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.process = None
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, '\n--- process finished ---\n')
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _stop(self):
        if self.process:
            self.process.terminate()

    def run(self):
        self.root.mainloop()
