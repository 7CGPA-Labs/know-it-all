import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QTextBrowser, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QDesktopServices, QCursor
from pydbus import SessionBus

class KnowItAllWidget(QWidget):
    def __init__(self):
        super().__init__()
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
        # Auto hide when user clicks away
        self.hide()
        super().focusOutEvent(event)


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
