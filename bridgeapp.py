# bridgeapp.py (--dbitrate 2000000 --bitrate 250000)

import argparse
import sys
import tkinter as tk
from tkinter.messagebox import showinfo

import can
from can.interfaces.pcan.pcan import PcanCanInitializationError
from bridge import Bridge, batch_create_pcan_buses, create_lan_bus

VERSION = '1.0.3'

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--port', default=62222, type=int)
parser.add_argument('--seg', default=1, type=int)
parser.add_argument('--bitrate', default=250_000, type=int)
parser.add_argument('--dbitrate', type=int)
parser.add_argument('--single', default=3, type=int)
args = parser.parse_args()


class Table:
    def __init__(self, root, columns):
        self.vars = dict()
        self.n_rows = n_rows = len(columns[0])
        self.n_cols = n_cols = len(columns)
        for i in range(n_rows):
            for j in range(n_cols):
                font = ("Arial Bold", 14) if (i == 0 or j == 0) else ("Arial", 14)
                var = tk.StringVar()
                var.set(str(columns[j][i]))
                self.e = tk.Label(root, textvariable=var, font=font)
                self.e.grid(row=i, column=j, sticky='W', padx=10)
                self.vars[i, j] = var

    def update(self, data):
        for i in range(self.n_rows):
            for j in range(self.n_cols):
                self.vars[i, j].set(str(data[j][i]))


class BridgeApp(tk.Frame):
    def __init__(self):
        root = tk.Tk()
        self.root = root

        # set the window title
        title = ' '.join(f'{k}={v}' for (k, v) in args.__dict__.items())
        title += f' v{VERSION}'
        root.title(title)

        # minimize window after opening
        root.wm_state('iconic')
        tk.Frame.__init__(self, root)
        self.grid()

        # create bridge
        lan_bus = create_lan_bus(args.port, args.seg)
        try:
            can_1, can_2 = batch_create_pcan_buses(args.bitrate, args.dbitrate, args.single)
        except PcanCanInitializationError or IndexError:
            showinfo(title=None, message=f'PCAN initialization failed')
            sys.exit(0)
        self.bridge = Bridge(lan_bus, c_1=can_1, c_2=can_2)

        # create table widget
        self.table = self.table = Table(self, self.bridge.stats())

        # pad the inside of the frame
        self.grid(padx=10, pady=10)

    def refresh(self):
        """Update the number of sent messages on the screen"""
        stats = self.bridge.stats()
        self.table.update(stats)
        # schedule next update
        self.root.after(500, self.refresh)


app = BridgeApp()
app.refresh()
app.mainloop()
