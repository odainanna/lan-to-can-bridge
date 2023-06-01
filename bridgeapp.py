import argparse
import sys
import tkinter as tk
from tkinter.messagebox import showinfo

from can.interfaces.pcan import PcanBus

from bridge import Bridge
from lan_bus import LANBus

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--port', default=62222, type=int)
parser.add_argument('--seg', default=5, type=int)
parser.add_argument('--bitrate', default=125000, type=int)
parser.add_argument('--interface', default='pcan')
args = parser.parse_args()


class Table:
    def __init__(self, root, columns):
        self.vars = dict()
        self.n_rows = n_rows = len(columns[0])
        self.n_cols = n_cols = len(columns)
        for i in range(n_rows):
            for j in range(n_cols):
                font = ("Arial Bold", 14) if i == 0 else ("Arial", 14)
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
        args_string = f'BridgeApp(net={args.net}, port={args.port}, seg={args.seg}, bitrate={args.bitrate}'
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
        bus_1 = PcanBus(channel=channel_info[0]['channel'], bitrate=args.bitrate)
        bus_2 = PcanBus(channel=channel_info[1]['channel'], bitrate=args.bitrate)
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
