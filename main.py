from set_wallpaper import set_wallpaper
from qtpy.QtWidgets import *
from PyQt5.QtWebKitWidgets import QWebView
from qtpy import uic, QtCore, QtWidgets, QtGui
from reddit_download import main, download_from_url
import threading, time
import os, pandas, sys
from os.path import (
    exists as pathexists, join as pathjoin, basename as pathbasename,
    splitext as pathsplitext)
import re
from window import Ui_MainWindow

print("Starting Web Scraper")
app = QApplication([])

def hideConsole():
    from ctypes import windll
    GetConsoleWindow = windll.kernel32.GetConsoleWindow
    console_window_handle = GetConsoleWindow()
    ShowWindow = windll.user32.ShowWindow
    ShowWindow(console_window_handle, False) 

class MainWindow(QMainWindow, Ui_MainWindow):
    NUM_LOAD = 100
    firstPostLoaded = QtCore.Signal()
    nextImageSig = QtCore.Signal()
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        #uic.loadUi("window.ui", self)
        self.image_ind = 0
        self.post_ind = 0
        self.posts = []
        self.subreddit = 'wallpaperdump'
        self.lastInput = ''
        self.stop = False
        self.stepping = False
        self.dir = "C:/Users/Brett/Pictures/Wallpapers"

        #self.scores = pandas.read_pickle("ratings.txt") if os.path.exists("ratings.txt") else pandas.DataFrame(columns=["url", "rating"])

        self.likeBtn.pressed.connect(self.like)
        self.dislikeBtn.pressed.connect(self.dislike)
        self.nextBtn.pressed.connect(self.nextImage)
        self.previousBtn.pressed.connect(self.previousImage)
        self.saveAction.triggered.connect(self.saveImage)
        self.previewBtn.pressed.connect(self.preview)    
        self.nextPostBtn.pressed.connect(self.nextPost)
        self.prevPostBtn.pressed.connect(self.previousPost)
        self.firstPostLoaded.connect(self.showImage)
        self.label = QtWidgets.QLabel("")
        self.label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.centerLayout.addWidget(self.label, 0, 0)
        #self.postIDEdit.setText("")
        self.show()
        self.nextImageSig.connect(self.nextImage)
        self.playing = False

        self.webView.setAutoFillBackground(True)
        p = self.webView.palette()
        p.setColor(self.webView.backgroundRole(), QtCore.Qt.black)
        self.webView.setPalette(p)

        palette = self.webView.palette()
        palette.setBrush(QtGui.QPalette.Base, QtCore.Qt.transparent)
        self.webView.page().setPalette(palette)
        self.webView.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)
    
    def nextPost(self):
        self.image_ind = 0
        self.post_ind = min(len(self.posts)-1, self.post_ind + 1)

        self.showImage()

    def previousPost(self):
        self.post_ind = max(self.post_ind - 1, 0)
        self.image_ind = 0
        self.showImage()

    def keyPressEvent(self, ev):
        key = ev.key()
        if key == 49:
            self.like()
        elif key == 48:
            self.dislike()
        elif key == 45 or key == 16777234:
            self.previousImage()
        elif key == 61 or key == 16777236:
            self.nextImage()
        elif key == 78:
            self.nextPost()
        elif key == 80:
            self.previousPost()
        elif ev.text() == 's':
            self.playing = not self.playing
            if self.playing and not self.stepping:
                threading.Thread(None, self.play).start()
            else:
                self.infoText.setPlainText(self.infoText.toPlainText().rsplit('\n', 1)[0])

        elif ev.text() == 'x':
            self.stop = True
        elif ev.text() == 'e':
            wasRunning = False
            if self.playing:
                wasRunning = True
                self.playing = False
            self.saveImage()
            if wasRunning:
                self.playing = True
                threading.Thread(None, self.play).start()
        elif ev.text() == 'g':
            self.preview()
        elif ev.text() == 'c':
            from pyqtgraph.console import ConsoleWidget
            self.cw = ConsoleWidget()
            self.cw.localNamespace['self'] = self
            self.cw.show()
        elif ev.key() == 16777235:
            s = self.stepSpinner.value()
            self.stepSpinner.setValue(s + 1)
        elif ev.key() == 16777237:
            s = self.stepSpinner.value()
            self.stepSpinner.setValue(max(1, s - 1))
        elif ev.text() == 'f':
            if not hasattr(self, 'fullWebView'):
                self.fullWebView = QWebView()
                self.fullWindow = QWidget()
                layout  = QGridLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                self.fullWindow.setLayout(layout)
                
                self.fullInfoLabel = QLabel()
                self.fullInfoLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)

                self.fullLabel = QtWidgets.QLabel()
                self.fullLabel.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignCenter) 
                self.fullLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
                def setText():
                    t = self.idLabel.text()
                    try:
                        t = t.split('\n')[1].split(' ')[-1]
                    except:
                        pass
                    if self.stepping:
                        t += '\n' + str(self.stepSpinner.value()) + 's'
                    self.fullInfoLabel.setText(t)
                setText()
                self.fullFont = QtGui.QFont('Helvetica')
                #self.fullFont.setPointSize(12)
                self.fullInfoLabel.setFont(self.fullFont)
                self.fullInfoLabel.setContentsMargins(10, 10, 10, 10)
                self.fullInfoLabel.setStyleSheet('color: white; font-size:12;')
                layout.addWidget(self.fullWebView, 0, 0)
                layout.addWidget(self.fullLabel, 0, 0)
                layout.addWidget(self.fullInfoLabel, 0, 0)
                
                self.fullWebView.setUrl(self.webView.url())

                self.fullWindow.keyPressEvent = self.keyPressEvent

                self.fullWebView.setAutoFillBackground(True)
                p = self.fullWebView.palette()
                p.setColor(self.fullWebView.backgroundRole(), QtCore.Qt.black)
                self.fullWebView.setPalette(p)

                palette = self.fullWebView.palette()
                palette.setBrush(QtGui.QPalette.Base, QtCore.Qt.transparent)
                self.fullWebView.page().setPalette(palette)
                self.fullWebView.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, False)

            if self.fullWindow.isFullScreen():
                self.fullWindow.showNormal()
                self.fullWindow.hide()
            else:
                self.fullWindow.showFullScreen()


    def play(self):
        self.stepping = True
        while self.playing and not self.stop:
            self.nextImageSig.emit()
            QApplication.instance().processEvents()
            time.sleep(self.stepSpinner.value())
        self.stepping = False

    def closeEvent(self, ev):
        self.stop = True
        self.removeTempImages()

        if hasattr(self, 'scrapeThread'):
            self.scrapeThread.join()
            self.cacheThread.join()
            while self.cacheThread.isAlive() or self.scrapeThread.isAlive():
                QtWidgets.qApp.processEvents()
        QMainWindow.closeEvent(self, ev)
        #self.scores.to_pickle("ratings.txt")

    def preview(self):
        if hasattr(self, 'scrapeThread'):
            self.stop = True
            self.scrapeThread.join()
            self.cacheThread.join()
            del self.scrapeThread, self.cacheThread

        if self.postIDEdit.text() != '' or self.subreddit != self.subredditEntry.text():
            self.removeTempImages()
            self.posts = []
            self.image_ind = 0
            self.post_ind = 0
            self.subreddit = self.subredditEntry.text()
            self.lastInput = self.postIDEdit.text()
            self.infoText.setPlainText("Loading")
            self.idLabel.setText("Post -/0\nImage ID: -/0")
            self.webView.setUrl(QtCore.QUrl(""))

        self.stop = False
        self.scrapeThread = threading.Thread(None, self.generateURLs)
        self.scrapeThread.start()

        if not hasattr(self, 'cacheThread') or not self.cacheThread.isAlive():
            self.cacheThread = threading.Thread(None, self.cache_thread)
            self.cacheThread.start()

    def appendRating(self, url, rating):
        if '/comments/' in url:
            return
        #if url in self.scores['url'].values:
        #    self.scores[self.scores['url'] == url] = [url, rating]
        #else:
        #    self.scores.loc[len(self.scores.index)] = [url, rating]

    def like(self):
        image = self.webView.url().toString()
        if image == 'about:blank':
            return
        rating = 1
        self.appendRating(image,  rating)
        self.nextImage()

    def dislike(self):
        image = self.webView.url().toString()
        if image == 'about:blank':
            return
        rating = 0
        self.appendRating(image,  rating)
        self.nextImage()

    def nextImage(self):
        post, img = self.offset(-10)
        if (self.image_ind > 10 or self.post_ind > 6) and post is not None:
            if os.path.exists(self.posts[post]['URLS'][img].localUrl):
                os.unlink(self.posts[post]['URLS'][img].localUrl)
                #os.remove(self.posts[post]['URLS'][img].localUrl)
            self.posts[post]['URLS'][img].localUrl = ""

        self.image_ind += 1
        if self.post_ind >= len(self.posts):
            return
        if self.image_ind >= len(self.posts[self.post_ind]['URLS']):
            self.nextPost()
        else:
            self.showImage()

    def removeTempImages(self):
        for post in self.posts:
            for url in post['URLS']:
                if os.path.exists(url.localUrl):
                    os.unlink(url.localUrl)
                    #os.remove(url.localUrl)


    def showImage(self):
        if self.filterGroup.isChecked() and self.skipCheck.isChecked():
            #if self.posts[self.post_ind]['URLS'][self.image_ind].url in self.scores['url']:
            #    self.nextImage()
            #    return
            pass
        if self.post_ind >= len(self.posts):
            print("Images not loaded yet")
            return
        post = self.posts[self.post_ind]
        url = QtCore.QUrl(post['URLS'][self.image_ind].url)
        local = False
        pix = QtGui.QPixmap()
        pixFull = QtGui.QPixmap()
        if os.path.exists(post['URLS'][self.image_ind].localUrl):
            set_wallpaper(pos['URLS'][self.image_ind].localUrl)
            '''
            local = True
            pixMain = QtGui.QPixmap()
            pixMain.load(post['URLS'][self.image_ind].localUrl)
            if not pixMain.isNull():
                if hasattr(self, 'fullWindow') and self.fullWindow.isFullScreen() and self.fullWindow.isVisible():
                    size =  QtWidgets.QDesktopWidget().size()
                    w, h = size.width(), size.height()
                    pixFull = pixMain.scaled(w, h, QtCore.Qt.KeepAspectRatio)
            
                size =  self.webView.size()
                w, h = size.width(), size.height()
                pix = pixMain.scaled(w, h, QtCore.Qt.KeepAspectRatio)

                url = QtCore.QUrl.fromLocalFile(post['URLS'][self.image_ind].localUrl)
            '''
        self.postIDEdit.setText(post['id'])
        info = "Title: %s\nURL: %s\nID: %s\nUps: %d, Downs: %d" % (post["title"], url.url(), post['id'], post['ups'], post['downs'])
        #if url.url() in self.scores['url'].values:
        #    info += "\nScore: %d" % self.scores[self.scores['url'] == url.url()]['rating']
        if self.playing:
            info += "\nShowing for %d seconds" % self.stepSpinner.value()
        self.infoText.setPlainText(info)
        self.idLabel.setText("Post %d/%d\nImage ID: %d/%d" % (self.post_ind+1, len(self.posts), self.image_ind + 1, len(self.posts[self.post_ind]["URLS"])))
        if hasattr(self, 'fullInfoLabel'):
            t = '%s/%s' % (self.image_ind + 1, len(self.posts[self.post_ind]["URLS"]))
            if self.playing:
                t += '\n%ss' % self.stepSpinner.value()
            self.fullInfoLabel.setText(t)

        if not pix.isNull():
            if hasattr(self, "fullWindow"):
                self.fullLabel.setPixmap(pixFull)
                self.fullWebView.setUrl(QtCore.QUrl(''))
            self.webView.setUrl(QtCore.QUrl(''))
            self.label.setPixmap(pix)
            
        else:
            if hasattr(self, "fullWindow"):
                self.fullWebView.setUrl(url)
                self.fullLabel.setPixmap(QtGui.QPixmap())
            self.webView.setUrl(url)
            self.label.setPixmap(QtGui.QPixmap())
            
    def offset(self, off):
        post = self.post_ind
        img = max(0, self.image_ind + off)
        while post >= len(self.posts) or img >= len(self.posts[self.post_ind]['URLS']):
             post += 1
             if post > len(self.posts):
                return None, None
             img -= len(self.posts[self.post_ind]['URLS'])
        if post >= len(self.posts) or img > len(self.posts[self.post_ind]['URLS']):
            return None, None
        return post, img

    def cache_thread(self):
        while True:
            if self.stop:
                break
            #if len(self.posts) < 5:
            #    continue
            for i in range(15):
                post, img = self.offset(i)
                if post is not None and img is not None:
                    if post >= len(self.posts) or img >= len(self.posts[post]['URLS']):
                        break
                    if self.posts[post]['URLS'][img].localUrl != '':
                        continue
                    if not self.posts[post]['URLS'][img].downloadThread.isAlive():
                        self.posts[post]['URLS'][img].downloadThread.start()
                    

    def generateURLs(self):
        attempts = 0
        while True:
            if self.stop:
                break
            if len(self.posts) - self.post_ind < 5:
                args = [self.subreddit, '--num', '15']
                if self.filterGroup.isChecked():
                    if self.sfwCheck.isChecked():
                        args.extend(['--sfw'])
                    if self.nsfwCheck.isChecked():
                        args.extend(['--nsfw'])
                    if len(self.keywordEntry.text()) > 0:
                        args.extend(['--title-contain', self.keywordEntry.text()])
                    if self.nonImageCheck.isChecked():
                        args.extend(['--non-images'])
                if self.posts:
                    args.extend(['--last', self.posts[-1]['id']])
                elif self.lastInput:
                    args.extend(['--last', self.lastInput])
                    self.lastInput = ''
                args.extend(['--verbose'])
                images = 0
                for item in main(args, download=False):
                    images += 1
                    self.posts.append(item)
                    if len(self.posts) == 1:
                        self.firstPostLoaded.emit()
                    if self.stop:
                        break
                if images == 0:
                    attempts += 1
                if attempts > 5:
                    self.stop = True

            time.sleep(.5)

    def previousImage(self):
        self.image_ind -= 1
        if self.image_ind < 0:
            self.previousPost()
        else:
            self.showImage()


    def saveImage(self):
        URL = self.posts[self.post_ind]["URLS"][self.image_ind].url
        FILEEXT = pathsplitext(self.posts[self.post_ind]["URLS"][self.image_ind].url)[1]
        # Trim any http query off end of file extension.
        FILEEXT = re.sub(r'\?.*$', '', FILEEXT)
        if not FILEEXT:
            # A more usable option that empty.
            # The extension can be fixed after downloading, but then the 'already downloaded' check will be harder.
            FILEEXT = '.jpg'

        FILENAME = '%s%s%s' % (pathsplitext(pathbasename(URL))[0], '', FILEEXT)
        # join file with directory
        FILEPATH = pathjoin(self.dir, FILENAME)

        fname = QFileDialog.getSaveFileName(self, "Save Image", FILEPATH, "Images (*%s)" % FILEEXT)
        if len(fname) == 2:
            fname = fname[0]
        download_from_url(URL, fname)


if __name__ == "__main__":
    mw = MainWindow()
    if '--no-console' in sys.argv:
        hideConsole()
    app.exec_()
