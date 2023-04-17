import argparse
import tkinter as tk

from bridge import Bridge

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('--net', default='127.0.0.1')
parser.add_argument('--port', default=62222, type=int)
parser.add_argument('--seg', default=5, type=int)
parser.add_argument('--bitrate', default=125000, type=int)
parser.add_argument('--interface', default='virtual')
args = parser.parse_args()


class BridgeApp(tk.Frame):
    def __init__(self):
        root = tk.Tk()
        self.root = root
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
        names = ['BUS'] + list(report.keys())
        counts = ['SENT'] + list(report.values())

        # write the names of the buses
        for i, name in enumerate(names):
            var = tk.StringVar()
            var.set(name)
            tk.Label(root, textvariable=var, anchor="e").grid(column=0, row=i)

        self.editable_labels = []
        # write the initial counts
        for i, count in enumerate(counts):
            var = tk.StringVar()
            var.set(str(count))
            tk.Label(root, textvariable=var, anchor="e").grid(column=1, row=i)
            if i != 0:  # ignore the first label, which is a header
                self.editable_labels.append(var)

    def refresh(self):
        # get counts
        counts = self.bridge.report().values()
        # update values
        for i, count in enumerate(counts):
            self.editable_labels[i].set(str(count))
        # schedule next update
        self.root.after(500, self.refresh)


app = BridgeApp()
app.refresh()
app.mainloop()
