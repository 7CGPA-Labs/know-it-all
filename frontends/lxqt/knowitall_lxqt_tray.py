import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QTextBrowser, QSystemTrayIcon, QMenu, QAction, QLabel)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QDesktopServices, QCursor
from pydbus import SessionBus

class KnowItAllWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_position = None
        self.resize_margin = 8
        self.resizing_edge = 0
        self.setMouseTracking(True)
        self.init_ui()

    def init_ui(self):
        # Sleek borderless popup window (like Copilot panel)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.resize(400, 550)
        self.setStyleSheet("""
            QWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 13px;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
                color: #c9d1d9;
            }
            QLineEdit:focus {
                border: 1px solid #58a6ff;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #c9d1d9;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
            QTextBrowser {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 10px;
            }
            QScrollBar:vertical {
                background-color: #0d1117;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #30363d;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #8b949e;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
        """)

        # Layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 2)
        
        title_label = QLabel("KNOW-IT-ALL")
        title_label.setStyleSheet("font-weight: bold; color: #58a6ff; border: none; background: transparent;")
        
        self.minimize_btn = QPushButton("—")
        self.minimize_btn.setFixedSize(24, 24)
        self.minimize_btn.setCursor(Qt.PointingHandCursor)
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #8b949e;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #21262d;
                color: #c9d1d9;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
        """)
        self.minimize_btn.clicked.connect(self.hide)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.minimize_btn)
        main_layout.addLayout(header_layout)

        # Input Row
        input_layout = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask Know-It-All...")
        self.query_input.returnPressed.connect(self.send_query)
        
        self.search_btn = QPushButton("Ask")
        self.search_btn.clicked.connect(self.send_query)
        
        input_layout.addWidget(self.query_input)
        input_layout.addWidget(self.search_btn)
        main_layout.addLayout(input_layout)

        # Browser Viewport
        self.browser = QTextBrowser()
        self.browser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml("""
            <div style='color: #8b949e; text-align: center; margin-top: 150px;'>
                <h3>Know-It-All Panel</h3>
                <p>Type a question above or click the tray icon to start.</p>
            </div>
        """)
        main_layout.addWidget(self.browser)

        self.setLayout(main_layout)

    def send_query(self):
        query = self.query_input.text().strip()
        if not query:
            return

        self.browser.setHtml(f"<div style='color: #58a6ff;'>Searching DuckDuckGo for: <b>{query}</b>...</div>")
        QApplication.processEvents()

        try:
            bus = SessionBus()
            service = bus.get('org.knowitall.CrawlerService')
            html_response = service.AskQuestion(query)
            self.browser.setHtml(html_response)
        except Exception as e:
            self.browser.setHtml(f"""
                <div style='color: #f85149; padding: 10px;'>
                    <h4>Error connecting to CrawlerService</h4>
                    <p>{e}</p>
                    <p style='color: #8b949e;'>Ensure that the D-Bus service is registered or check your system configuration.</p>
                </div>
            """)

    def show_near_tray(self, tray_icon):
        # Position panel overlay nicely near the system tray icon
        geom = tray_icon.geometry()
        
        # Determine X coordinate (center on tray or cursor)
        if geom.isEmpty() or (geom.x() == 0 and geom.y() == 0):
            pos = QCursor.pos()
            target_x = pos.x()
        else:
            pos = geom.topLeft()
            target_x = pos.x() + geom.width() // 2
            
        # Get screen geometries
        screen = QApplication.primaryScreen()
        screen_geom = screen.geometry()
        avail_geom = screen.availableGeometry()
        
        # Calculate horizontal position (x)
        x = target_x - self.width() // 2
        
        # Ensure horizontal boundaries are within the working area
        if x < avail_geom.left() + 5:
            x = avail_geom.left() + 5
        if x + self.width() > avail_geom.right() - 5:
            x = avail_geom.right() - self.width() - 5
            
        # Calculate vertical position (y) based on panel location
        # Check if panel is at top (available top is pushed down)
        if avail_geom.top() > screen_geom.top():
            y = avail_geom.top() + 5
        # Check if panel is at bottom (available bottom is pulled up)
        elif avail_geom.bottom() < screen_geom.bottom() - 1:
            y = avail_geom.bottom() - self.height() - 5
        # Default fallback (usually bottom panel)
        else:
            y = avail_geom.bottom() - self.height() - 5
            
        self.move(x, y)
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            self.query_input.setFocus()

    def focusOutEvent(self, event):
        if not self.drag_position and not self.resizing_edge:
            self.hide()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.resizing_edge != 0:
                event.accept()
            else:
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        
        if not event.buttons() & Qt.LeftButton:
            edge = 0
            if x < self.resize_margin:
                edge |= 1
            elif x > w - self.resize_margin:
                edge |= 2
            if y < self.resize_margin:
                edge |= 4
            elif y > h - self.resize_margin:
                edge |= 8
                
            self.resizing_edge = edge
            
            if edge == (1 | 4) or edge == (2 | 8):
                self.setCursor(Qt.SizeFDiagCursor)
            elif edge == (2 | 4) or edge == (1 | 8):
                self.setCursor(Qt.SizeBDiagCursor)
            elif edge & 1 or edge & 2:
                self.setCursor(Qt.SizeHorCursor)
            elif edge & 4 or edge & 8:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        else:
            if self.resizing_edge:
                global_pos = event.globalPos()
                rect = self.geometry()
                min_w = 300
                min_h = 400
                
                if self.resizing_edge & 1:
                    new_w = rect.right() - global_pos.x()
                    if new_w >= min_w:
                        rect.setLeft(global_pos.x())
                elif self.resizing_edge & 2:
                    new_w = global_pos.x() - rect.left()
                    if new_w >= min_w:
                        rect.setRight(global_pos.x())
                        
                if self.resizing_edge & 4:
                    new_h = rect.bottom() - global_pos.y()
                    if new_h >= min_h:
                        rect.setTop(global_pos.y())
                elif self.resizing_edge & 8:
                    new_h = global_pos.y() - rect.top()
                    if new_h >= min_h:
                        rect.setBottom(global_pos.y())
                        
                self.setGeometry(rect)
                event.accept()
            elif self.drag_position is not None:
                self.move(event.globalPos() - self.drag_position)
                event.accept()
                
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        self.resizing_edge = 0
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)


class KnowItAllTrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Create panel overlay
        self.panel = KnowItAllWidget()

        # System Tray Configuration
        self.tray = QSystemTrayIcon(self.app)
        
        # Use a standard fallback system icon (like a search or network globe icon)
        icon = QIcon.fromTheme("system-search", QIcon.fromTheme("applications-other"))
        self.tray.setIcon(icon)
        self.tray.setToolTip("Know-It-All (Semi-AI Panel)")

        # Single click to toggle the panel
        self.tray.activated.connect(self.on_tray_activated)

        # Context Menu
        menu = QMenu()
        open_action = QAction("Open Panel", menu)
        open_action.triggered.connect(lambda: self.panel.show_near_tray(self.tray))
        
        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(self.exit_app)
        
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self.tray.setContextMenu(menu)
        
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.panel.show_near_tray(self.tray)

    def exit_app(self):
        self.panel.close()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec_())

if __name__ == '__main__':
    app = KnowItAllTrayApp()
    app.run()
