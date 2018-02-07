from redwall.ScraperWindow import ScraperWindow
from redwall.scrapers import *
from tkinter import *
from tkinter.ttk import *

def newScraper():
	print("Which type of scraper do you want?")
	print("\n".join(["%d: %s" % (i, SCRAPER_TYPES[i].__name__) for i in range(len(SCRAPER_TYPES))]))
	resp = int(input("::"))
	s = SCRAPER_TYPES[resp].newScraper()
	return s

def nogui(args = []):
	if len(args) == 1:
		session = ScraperSession.fromFile(args[0])
	else:
		session = ScraperSession()

	options = {
	'a': 'add scraper',
	'r': 'remove scraper',
	'n': 'next image',
	'e': 'export image',
	's': 'save session file',
	'l': 'load session file',
	'q': 'quit'}

	prompt = ''
	prompt = '\n'.join(['%s\t: %s' % (k, v) for k, v in options.items()])

	while True:
		print(prompt)
		response = input('::').lower()
		if response in options:
			if response == 'a':
				s = newScraper()
				session.addScraper(s)
			elif response == 'n':
				if len(session.scrapers) == 0:
					print("No scrapers created.")
				else:
					session.nextWallpaper()
			elif response == 'r':
				scrapers = session.scrapers
				p = '\n'.join(['%d: %s' % (i, scrapers[i]) for i in range(len(scrapers))])
				i = input(p + "\nRemove scraper ::")
				session.removeScraper(int(i))
			elif response == 'e':
				fname = input("Save image as: ")
				img = session.current_image['url']
				download_from_url(img, fname)
			elif response == 'l':
				fname = input("Session file: ")
				session = ScraperSession.fromFile(fname)
			elif response == 's':
				fname = input("Save as: ")
				session.save(fname)
			elif response == 'q':
				break
		else:
			print("Unrecognized response")

def run():
    if '-nogui' in sys.argv:
        nogui()
        exit()

    root = Tk()
    style = Style()

    style.configure("Spin.TButton", relief=FLAT, padding=0, font=("Monospace", 12), borderwidth=0, highlightthickness=0)
    style.configure("Square.TButton", relief=FLAT, padding=0, font=("Monospace", 20), borderwidth=0, highlightthickness=0)

    style.configure("Normal.TFrame", background="gray")
    style.configure("Invalid.TFrame", background="red")
    style.configure("Current.TFrame", background="green")
    app = ScraperWindow(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.close()


if __name__ == '__main__':
    run()
