# bridgeapp.py (--dbitrate 2000000 --bitrate 250000)

import argparse
import sys
import tkinter as tk
from tkinter.messagebox import showinfo

import can
from can.interfaces.pcan import PcanBus
from can.interfaces.pcan.pcan import PcanCanInitializationError

from bridge import Bridge
from lan_bus import LANBus

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--port', default=62222, type=int)
parser.add_argument('--seg', default=1, type=int)
parser.add_argument('--bitrate', default=125_000, type=int)
parser.add_argument('--dbitrate', type=int)
args = parser.parse_args()

VERSION = '1.0.0'


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
        args_string = f'BridgeApp(net={args.net}, port={args.port}, seg={args.seg}, bitrate={args.bitrate} v{VERSION}'
        root.title(args_string)

        # add an icon
        # photo = tk.PhotoImage(file='bridge-icon.png')
        # root.wm_iconphoto(False, photo)

        # minimize window after opening
        root.wm_state('iconic')
        tk.Frame.__init__(self, root)
        self.grid()

        # detect PCAN channels
        channel_info = Bridge.detect()
        n_configs = len(channel_info)
        if n_configs == 0:
            showinfo(title='Not detected', message='No PCAN channels detected.')
            sys.exit(0)
        elif n_configs == 1:
            showinfo(title=None, message=f'{n_configs}/2 PCAN channels detected.')
            sys.exit(0)

        # start bridge
        if args.dbitrate:
            timing = can.BitTimingFd.from_sample_point(
                f_clock=80_000_000,
                nom_bitrate=args.bitrate,
                nom_sample_point=81.3,
                data_bitrate=args.dbitrate,
                data_sample_point=80.0,
            )
            bus_kwargs = dict(auto_reset=True, timing=timing)
        else:
            bus_kwargs = dict(auto_reset=True, bitrate=args.bitrate, fd=False)

        try:
            bus_1 = PcanBus(channel=channel_info[0]['channel'], **bus_kwargs)
            bus_2 = PcanBus(channel=channel_info[1]['channel'], **bus_kwargs)
        except PcanCanInitializationError:
            showinfo(title=None, message=f'PCAN initialization failed')
            sys.exit(0)

        if not (bus_1.status_is_ok() and bus_2.status_is_ok()):
            showinfo(title='Unexpected bus state', message=f'{bus_1.channel_info}: {bus_1.status_string()}\n'
                                                           f'{bus_2.channel_info}: {bus_2.status_string()}')
            sys.exit(0)

        lan_bus = LANBus(port=args.port, dest='239.0.0.' + str(args.seg), segment=args.seg)
        self.bridge = Bridge(bus_1, bus_2, lan_bus)

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
