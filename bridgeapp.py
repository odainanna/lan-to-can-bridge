import argparse
import tkinter as tk

from bridge import Bridge

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--port', default=62222, type=int)
parser.add_argument('--seg', default=5, type=int)
parser.add_argument('--bitrate', default=125000, type=int)
parser.add_argument('--interface', default='pcan')
args = parser.parse_args()


class BridgeApp(tk.Frame):
    def __init__(self):
        root = tk.Tk()
        args_string = f'BridgeApp(net={args.net}, port={args.port}, seg={args.seg}, bitrate={args.bitrate}, ' \
                      f'interface={args.interface})'
        root.title(args_string)
        root.geometry('800x200+50+50')
        # root.wm_state('iconic')
        tk.Frame.__init__(self, root)
        self.grid()

        # start the bridge
        self.bridge = Bridge(args.net, args.port, args.seg, args.bitrate, args.interface)
        self.bridge.start()

        report = self.bridge.report()
        names = report.keys()
        counts = report.values()

        # write the names of the buses
        for i, name in enumerate(names):
            var = tk.StringVar()
            var.set(name)
            tk.Label(root, textvariable=var).grid(column=0, row=i, padx=20)


app = BridgeApp()
app.mainloop()
