# Simple enough, just import everything from tkinter.
from tkinter import *
from tkinter.ttk import *
from tkinter.scrolledtext import ScrolledText
from tkinter.filedialog import askopenfilename, asksaveasfilename
import inspect, sys, subprocess, os
from redwall.scrapers import *
from tkinter import simpledialog, messagebox

class SquareButton(Frame):
    def __init__(self, parent, **args):
        Frame.__init__(self, parent, height=45, width=45)
        self.button = Button(self, style="Square.TButton", **args)

        self.rowconfigure(0, weight = 1)
        self.columnconfigure(0, weight = 1)

        self.grid_propagate(0)

        self.grid(row = 0, column = 0)
        self.button.grid(sticky="NSEW")


class SpinColumn(Frame):
    def __init__(self, master, value=0, lo=0, hi=None, command=None):
        Frame.__init__(self, master, borderwidth=1, relief=GROOVE)
        self.rowconfigure(1, weight = 1)
        self.columnconfigure(1, weight = 1)
        self.grid_propagate(0)
        self.value = StringVar()
        self.value.set(value)
        self.lo = lo
        self.hi = hi
        self.command = command

        self.upButton = Label(self, text='▲')
        self.upButton.bind("<Button-1>", lambda a: self.add(1))
        #self.upButton.config(style="Spin.TButton")
        self.upButton.pack(fill=NONE, pady=0)

        #self.entry = Entry(self, state='readonly', textvariable=self.value, width=3, justify=CENTER)
        self.entry = Label(self, textvariable=self.value, width=3, anchor=CENTER)
        self.entry.pack(pady=0)

        self.downButton = Label(self, text='▼')
        self.downButton.bind("<Button-1>",lambda a:self.add(-1))
        self.downButton.pack(fill=None, pady=0, ipady=0)

    def add(self, n):
        n += int(self.value.get())
        if self.lo is not None:
            n = max(self.lo, n)
        if self.hi  is not None:
            n = min(self.hi, n)

        self.value.set(n)
        if self.command:
            self.command(n)

class HistoryDialog(object):

    def __init__(self, master, session):
        self.top = Toplevel(master)

        frm = Frame(self.top)
        frm.pack(fill=BOTH, expand=True)

        self.session = session
        self.history_list = Listbox(frm, width=100)
        self.history_list.pack(fill=X, expand=1)
        for image in session._history:
            self.history_list.insert(END, image['url'])

        self.set_button = Button(frm, text="Set Wallpaper", command=self.set_wallpaper)
        self.set_button.pack()

        b_cancel = Button(frm, text='Cancel')
        b_cancel['command'] = self.top.destroy
        b_cancel.pack(padx=4, pady=4)

    def set_wallpaper(self):
        ind = self.history_list.curselection()
        url = self.history_list.get(ind)
        self.session.setWallpaperFromURL(url)

class ScraperEditorDialog(simpledialog.Dialog):

    def body(self, master):
        scraper = None
        if isinstance(self.master, ScraperFrame):
            scraper = self.master.scraper

        self.selectedScraper = StringVar()
        self.scraperCombo = Combobox(master, textvariable=self.selectedScraper, state='readonly')
        self.scraperCombo.bind("<<ComboboxSelected>>", self.newSelection)
        self.scraperCombo['values'] = [s.__name__ for s in SCRAPER_TYPES]

        self.scraperCombo.grid(row=0)

        self.optsFrame = Frame(master, borderwidth=2, relief=GROOVE)
        self.optsFrame.grid(row=1)
        self.optsFrame.rowconfigure(0, weight = 1)
        self.optsFrame.columnconfigure(0, weight = 1)
        self.optsFrame.grid_propagate(0)

        self.entries = []
        self.labels = []
        self.parameters = {}

        if scraper is None:
            self.scraperCombo.current(0)

        self.newSelection(scraper=scraper)
        return self.scraperCombo # initial focus

    def newSelection(self, event=None, scraper=None):
        sc = SCRAPER_TYPES[self.scraperCombo.current()] if scraper == None else scraper.__class__

        if scraper is not None:
            self.selectedScraper.set(scraper.__class__.__name__)
            self.scraperCombo.config(state='disabled')

        for entry in self.entries:
            entry.destroy()
        self.entries = []

        for label in self.labels:
            label.destroy()
        self.labels = []

        self.parameters = {}
        if sc is None or not hasattr(sc, 'DEFAULT_ARGUMENTS'):
            return

        defaults = sc.DEFAULT_ARGUMENTS.copy()
        if scraper is not None:
            defaults.update(scraper.options)

        for i, c in enumerate(defaults):
            label = Label(self.optsFrame, text=c)
            label.grid(row=i, column=0)
            self.labels.append(label)

            entry = None
            var = None
            if isinstance(defaults[c], bool):
                var = IntVar()
                var.set(defaults[c])
                entry = Checkbutton(self.optsFrame, variable=var)
                entry.grid(row=i, column=1)
            elif isinstance(defaults[c], int):
                var = StringVar()
                var.set(defaults[c])
                entry = Spinbox(self.optsFrame, from_=-10000, to=10000, textvariable=var)
                entry.grid(row=i, column=1)

            if entry is None:
                var = StringVar()
                var.set(defaults[c])
                entry = Entry(self.optsFrame, textvariable=var)
                entry.grid(row=i, column=1)

            if scraper is not None:
                if c in scraper.options:
                    var.set(scraper.options[c])

            self.parameters[c] = var
            self.entries.append(entry)

        self.optsFrame.grid_forget()
        self.optsFrame.grid(row=1)

    def apply(self):
        sc = SCRAPER_TYPES[self.scraperCombo.current()]
        data = {}
        for p in self.parameters:
            t = type(sc.DEFAULT_ARGUMENTS[p])
            data[p] = t(self.parameters[p].get())
        #data = {n: self.parameters[n].get() for n in self.parameters}
        try:
            scraper = sc(**data)
        except Exception as e:
            messagebox.showinfo("Error", e)
            return
        self.result = scraper

class ScraperEditFrame(Frame):
    def __init__(self, master, scraper):
        Frame.__init__(self, master)


class VerticalScrolledFrame(Frame):
    """A pure Tkinter scrollable frame that actually works!
    * Use the 'interior' attribute to place widgets inside the scrollable frame
    * Construct and pack/place/grid normally
    * This frame only allows vertical scrolling

    """
    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)

        # create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # create a frame inside the canvas which will be scrolled with it
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)

        # track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)

class ScraperWindow(Frame):
    DEFAULT_SESSION_FILE = 'redwall_session.rw'
    def __init__(self, master=None):
        self.last_dir = "/"
        # parameters that you want to send through the Frame class.
        Frame.__init__(self, master)

        #reference to the master widget, which is the tk window
        self.master = master

        #with that, we want to then run init_window, which doesn't yet exist
        self.init_menu()
        self.init_window()

        self.scraper_map = {}

        self.session = None

        if os.path.exists(ScraperWindow.DEFAULT_SESSION_FILE):
            session = ScraperSession.fromFile(ScraperWindow.DEFAULT_SESSION_FILE)
            self.load_session(session)
        else:
            self.session = ScraperSession()
        #DEFAULT_SCRAPER = SubredditScraper('wallpaperdump')
        #DEFAULT_SCRAPER = FlickrProfileScraper('dasugaking')
        #self.addScraper(DEFAULT_SCRAPER)

        AbstractScraper.ScraperValidityChanged.connect(self.validityChanged)
        ScraperSession.ImageChanged.connect(self.imageChanged)
        ScraperFrame.ScraperWeightChanged.connect(self.weightChanged)
        ScraperFrame.ScraperRemoved.connect(self.scraperRemoved)
        ScraperFrame.ScraperEdited.connect(self.scraperEdited)
        ScraperFrame.ScraperSelected.connect(self.scraperSelected)

        self.master.protocol("WM_DELETE_WINDOW", self.close)

    def scraperSelected(self, scraperFrame):
        if scraperFrame.scraper._current_image is None:
            try:
                img = next(scraperFrame.scraper)
            except ImageScrapeError as e:
                messagebox.showinfo("Error", e)
                return
        self.session.setScraper(scraperFrame.scraper)

        for scraper in self.scraper_map.values():
            scraper.setState('Normal')

        scraperFrame.setState('Current')

        message = self.session.getState()
        message += '\n' + '\n'.join(['%s: %s' % (k, v) for k, v in self.session._current_image.items()])
        self.info_label.config(state="normal")
        self.info_label.delete('1.0', END)
        self.info_label.insert(END, message)
        self.info_label.config(state="disabled")


    def scraperEdited(self, scraperFrame, newScraper):
        scraperFrame.setScraper(newScraper)

    def close(self):
        if len(self.session.scrapers) > 0:
            v = messagebox.askyesno("Save", "Do you want to save the session file?")
            if v:
                self.session.save(ScraperWindow.DEFAULT_SESSION_FILE)
        self.master.destroy()

    def scraperRemoved(self, s):
        self.session.removeScraper(s)

    def weightChanged(self, scraper, weight):
        if scraper in self.session.scrapers:
            self.session.setWeight(scraper, weight)
        if scraper in self.scraper_map:
            self.scraper_map[scraper].setState('Normal')

    def validityChanged(self, scraper, invalid):
        if scraper in self.scraper_map:
            self.scraper_map[scraper].setState('Invalid' if invalid else 'Normal')
        if invalid:
            self.session.setWeight(scraper, 0)

    def imageChanged(self, old_scraper, new_scraper):
        if old_scraper in self.scraper_map:
            self.scraper_map[old_scraper].setState('Normal')

        if new_scraper in self.scraper_map:
            self.scraper_map[new_scraper].setState('Current')

    def init_menu(self):

        self.master.title("Redwall")
        self.pack(fill=BOTH, expand=1)
        menu = Menu(self.master)
        self.master.config(menu=menu)

        # create the file object)
        file = Menu(menu)

        file.add_command(label="Load Session", command=self.open_session)
        file.add_command(label="Save Session", command=self.save_session)
        file.add_separator()
        file.add_command(label="Save Image", command=self.saveImage)

        # adds a command to the menu option, calling it exit, and the
        # command it runs on event is client_exit
        file.add_command(label="Exit", command=self.close)

        #added "file" to our menu
        menu.add_cascade(label="File", menu=file)

        # create the file object)
        edit = Menu(menu)
        edit.add_command(label="View History", command=self.showHistory)
        edit.add_command(label="Start Screensaver", command=self.startScreensaver)
        menu.add_cascade(label="Scrapers", menu=edit)


    def startScreensaver(self):
        val = simpledialog.askinteger(self, "Screen duration (seconds)")
        if val > 0:
            self.master.withdraw()
            try:
                self.session.screensaver(val)
            except KeyboardInterrupt:
                pass
            self.master.deiconify()

    def showHistory(self):
        hist = HistoryDialog(self, self.session)

    def saveImage(self):
        f = asksaveasfilename(initialdir=self.last_dir, title="Save wallpaper locally", filetypes = (("jpg file","*.jpg"),))
        if f:
            self.last_dir = os.path.dirname(f)
            os.copy(self.session._current_url, f)

    def addScraper(self, s):
        obj = ScraperFrame(self.scraperList, s)
        self.scraper_map[s] = obj
        self.scraperList.addLine(obj)
        if s not in self.session.scrapers:
            self.session.addScraper(s)


    def init_window(self):
        self.columnconfigure(0, weight=1)
        frame1 = Frame(self)
        #frame1.grid(row=0, column=0, sticky="NSEW")

        self.addButton = SquareButton(frame1, text='+', command=self.newScraper)
        self.addButton.pack(side=LEFT, padx=5, pady=5)

        self.nextButton = SquareButton(frame1, text='>', command=self.nextImage)
        self.nextButton.pack(side=RIGHT, padx=5, pady=5)

        frame2 = Frame(self, relief=GROOVE, borderwidth=2)
        #frame2.grid(row=1, column=0, sticky="NSEW")

        #self.info_label = Label(frame2, textvariable=self.info, justify=LEFT)
        self.info_label = ScrolledText(frame2, height=3)
        self.info_label.insert(END, "No current scraper")
        self.info_label.config(state='disabled')
        self.info_label.bind("<1>", lambda event: self.info_label.focus_set())

        self.info_label.pack(fill=X, padx=5, expand=True)

        self.scraperList = ListFrame(self)
        #self.scraperList.grid(row=2, column=0, sticky="NSEW", padx=4, pady=4)

        frame1.pack(fill=X)
        frame2.pack(fill=X)
        self.scraperList.pack(fill=BOTH, expand=1)

    def nextImage(self):
        im = self.session.nextWallpaper()
        message = self.session.getState()
        message += '\n' + '\n'.join(['%s: %s' % (k, v) for k, v in self.session._current_image.items()])
        self.info_label.config(state="normal")
        self.info_label.delete('1.0', END)
        self.info_label.insert(END, message)
        self.info_label.config(state="disabled")

    def newScraper(self):
        newScraper = ScraperEditorDialog(self.master)
        if newScraper.result is not None:
            self.addScraper(newScraper.result)

    def open_session(self):
        f = askopenfilename(initialdir = self.last_dir, title = "Save redwall session",filetypes = (("rw file","*.rw"),))
        if os.path.exists(f):
            self.last_dir = os.path.dirname(f)
            session = ScraperSession.fromFile(f)
            self.load_session(session)

    def load_session(self, session):
        self.session = session
        self.scraperList.clear()

        for s in self.session.scrapers:
            self.addScraper(s)

        message = "New session loaded. Load a new image to see its information here"
        self.info_label.config(state="normal")
        self.info_label.delete('1.0', END)
        self.info_label.insert(END, message)
        self.info_label.config(state="disabled")

    def save_session(self):
        f = asksaveasfilename(initialdir=self.last_dir, title="Save redwall session", filetypes = (("rw file","*.rw"),))
        if f:
            self.last_dir = os.path.dirname(f)
            self.session.save(f)

class ScraperFrame(Frame):
    ScraperWeightChanged = Signal()
    ScraperRemoved = Signal()
    ScraperEdited = Signal()
    ScraperSelected = Signal()
    def __init__(self, list_container, scraper):
        Frame.__init__(self, list_container.interior, borderwidth=2, relief=GROOVE, padding=0, style="Normal.TFrame")

        self.list_container = list_container
        self.scraper = scraper

        self.weightEntry = SpinColumn(self, lo=0, hi=100, value=1, command=lambda v: self.ScraperWeightChanged.fire(self.scraper, v))
        self.weightEntry.pack(side=LEFT, fill=X)

        self.name = StringVar()
        self.name.set(scraper.getState())
        self.label = Label(self, textvariable=self.name, width=30)
        self.label.pack(side=LEFT, expand=1, fill=Y)

        self.removeButton = SquareButton(self, text="-", command=self.remove)
        self.removeButton.pack(side=RIGHT, fill=Y)
        self.editButton = SquareButton(self, text="...", command=self.edit)
        self.editButton.pack(side=RIGHT, fill=Y)

        self.label.bind("<Button-1>", self.clicked)
        self.bind("<Button-1>", self.clicked)

    def clicked(self, e):
        ScraperFrame.ScraperSelected.fire(self)

    def edit(self):
        editor = ScraperEditorDialog(self)
        if hasattr(editor, 'result') and editor.result is not None:
            self.setScraper(editor.result)

    def setScraper(self, scraper):
        self.name.set(scraper.getState())

    def weightChanged(self):
        val = self.weight.get()
        self.ScraperWeightChanged.fire(self.scraper, val)

    def setState(self, a):
        try:
            self.config(style=a + ".TFrame")
        except:
            pass

        self.name.set(self.scraper.getState())

    def remove(self):
        self.list_container.removeScraper(self)
        self.ScraperRemoved.fire(self.scraper)

class ListFrame(VerticalScrolledFrame):
    def __init__(self, parent):
        VerticalScrolledFrame.__init__(self, parent, borderwidth=2, relief=GROOVE)
        self.lines = []

    def addLine(self, w):
        w.pack(fill=X, expand=1, anchor=N)
        self.lines.append(w)

    def clear(self):
        for l in self.lines:
            l.destroy()
        self.lines = []

    def removeScraper(self, s):
        s.destroy()
        self.lines.remove(s)

    def removeLine(self, l):
        self.lines[l].destroy()
        self.lines.pop(l)
