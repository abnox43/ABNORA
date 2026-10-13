📖 What is ABNORA?
ABNORA is a local-first desktop PDF reader designed around a signature two-page Classic Book reading experience. It combines faithful PDF rendering with twelve distinctive visual themes, ranging from warm parchment libraries to neon-lit cyberpunk interfaces and phosphor-green CRT terminals.
Unlike ordinary document viewers, ABNORA treats the reading environment as part of the experience — without compromising the original document.
Real PDF rendering: Powered by PyMuPDF, preserving the document's original layout, typography, and images.
Native desktop interface: Built with Python, PySide6, and Qt.
Twelve visual worlds: Distinct themes with live previews and customizable appearance.
Privacy by design: No telemetry, accounts, cloud services, or application-initiated network requests.
Performance-conscious: Background rendering, asynchronous search, and bounded caching.
Open source: Built to be explored, modified, and extended.
✨ Features
The Classic Book experience
ABNORA opens into a warm, book-inspired reading environment.
Two-page spreads with a central spine and page-edge shadows.
A walnut reading surface that surrounds the document without altering it.
Optional cover handling, allowing the first page to stand alone.
Smooth spread transitions with reduced-motion support.
Three reading layouts, switchable without closing the document.
Layout
Shortcut
Description
Single Page
1
One page at a time, with fit-page and manual zoom
Classic Book
2
Two-page spreads with a central spine
Continuous
3
Vertical scrolling with fit-width support
Twelve themes, one reader
Switch between twelve complete visual styles without restarting the application. Every theme uses a centralized design-token system rather than a separate copy of the interface.
Full-featured PDF reading
Open PDFs through the file dialog, drag-and-drop, recent files, or the command line.
Handle password-protected documents.
Navigate pages, outlines, tables of contents, and internal links.
Search document text and highlight matching results.
Select and copy text.
Browse rendered page thumbnails.
Create named bookmarks.
Remember reading positions for individual documents.
Zoom, rotate pages, and switch between reading layouts.
Enter fullscreen or distraction-free mode.
Performance without unnecessary complexity
ABNORA renders pages on demand using background workers and a bounded least-recently-used (LRU) cache.
It does not rasterize entire documents into memory, and expensive rendering and search operations are kept off the UI thread.
📦 Installation
Requirements
Python 3.11 or newer
PySide6 6.6 or newer
PyMuPDF 1.24 or newer
Git
Use your distribution's packaged dependencies when they are compatible. Otherwise, install the Python dependencies inside a virtual environment.
Debian 13 / compatible Ubuntu releases
On Debian 13, install the system dependencies:
sudo apt update
sudo apt install -y \
git \
python3 \
python3-venv \
python3-pip \
python3-pyside6.qtwidgets \
python3-pyside6.qtgui \
python3-pyside6.qtcore \
python3-pymupdf
Clone the repository:
git clone https://github.com/abnora/abnora.git
cd abnora
Create a virtual environment that can access the system-installed Qt and PyMuPDF packages:
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
Install ABNORA and launch it:
pip install -e .
python main.py
Older Ubuntu releases: If your distribution does not provide compatible versions of PySide6 or PyMuPDF, use the PyPI installation method below instead. Create the environment without --system-site-packages.
Arch Linux / Manjaro
Install the dependencies:
sudo pacman -S --needed \
git \
python \
python-pip \
python-pyside6 \
python-pymupdf
Clone the repository and create the environment:
git clone https://github.com/abnora/abnora.git
cd abnora
python -m venv --system-site-packages .venv
source .venv/bin/activate
Install and launch:
pip install -e .
python main.py
ABNORA uses the modern pymupdf Python module name.
Windows
Install Python 3.11 or newer from python.org. Enable Add Python to PATH during installation.
In Command Prompt:
git clone https://github.com/abnora/abnora.git
cd abnora
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python main.py
Open a specific PDF directly:
python main.py "C:\path\to\book.pdf"
PowerShell users can activate the environment with:
.\.venv\Scripts\Activate.ps1
If activation is restricted, you can run the environment's Python executable directly instead.
macOS
Install Python 3.11 or newer from python.org or through Homebrew.
git clone https://github.com/abnora/abnora.git
cd abnora
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python main.py
The PyPI installation method is intended to supply the required Python dependencies on supported macOS systems. Native packaging and signing are not yet provided.
Any platform: Python virtual environment
For systems without suitable distribution packages, use the PyPI dependencies:
git clone https://github.com/abnora/abnora.git
cd abnora
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
On Windows, replace the environment activation command with:
.venv\Scripts\activate
Note: The commands above assume the repository includes the referenced requirements.txt and that its dependency versions are compatible with your platform.
Optional: Linux desktop integration
Install a desktop launcher, application icon, and abnora command:
./packaging/install-linux.sh
For a system-wide installation:
sudo env PREFIX=/usr ./packaging/install-linux.sh
The installer is intended to create a launcher and install the application under the selected prefix. Review the script before running it with elevated privileges.
🚀 Usage
Launch ABNORA without opening a document:
python main.py
Open a PDF directly:
python main.py path/to/document.pdf
After installing the package, the command-line entry point can also be used:
abnora path/to/document.pdf
You can also:
Drag and drop a PDF into the application.
Open a document with Ctrl+O.
Access recently opened documents.
Continue reading from a previously saved position.
🎨 Themes
Press T or use the palette button to open the theme browser.
Preview each theme, hover to explore its appearance, select your favorite, and apply the change. Cancel to revert an uncommitted selection.
#
Theme
Atmosphere
01
Classic Book
Warm parchment, walnut wood, muted bronze
02
Cyberpunk
Near-black surfaces, neon cyan, vivid magenta
03
CRT Terminal
Phosphor green, scanlines, adjustable glow
04
Steampunk
Aged parchment, antique copper, brass
05
Hacker's Den
Matte black, muted green, keyboard-first design
06
Gothic Library
Deep burgundy, charcoal, antique silver
07
Synthwave
Midnight blue, purple-pink neon, retro horizons
08
Nordic Minimal
Soft gray surfaces, cool desaturated blue
09
Solarized
Balanced colors inspired by the Solarized palette
10
Japanese Zen
Warm washi paper, charcoal ink, vermilion
11
Blueprint
Technical blue, cyan accents, drafting grids
12
Space Odyssey
Deep navy, cosmic atmosphere, drifting stars
Personalize your reading environment
Depending on the selected theme and available effects, you can customize:
Accent color.
Interface font size.
Reduced-motion behavior.
CRT scanlines and glow.
Other theme-specific visual effects.
Your preferences are saved and restored on subsequent launches.
Important: Themes change the reader's interface, not the PDF itself. Document pages retain their original appearance.
📄 PDF functionality
Feature
Description
Document opening
File dialog, drag-and-drop, recent documents, CLI arguments
Password protection
Prompts for passwords when required
Navigation
Page controls, direct page entry, outlines, internal links
Zoom
Zoom in/out, fit page, fit width
Rotation
Rotate pages by 90-degree increments
Search
Document-wide text search, highlighted matches, result navigation
Text selection
Select and copy available document text
Thumbnails
Browse rendered page previews
Bookmarks
Save named bookmarks
Reading history
Persist reading positions per document
Fullscreen
Expand the reading area
Distraction-free mode
Hide unnecessary interface elements
What about scanned PDFs?
Scanned PDFs display normally, but searching and selecting text require an embedded text layer.
Optical character recognition (OCR) is not currently implemented. Optional OCR support is planned for a future release.
⌨️ Keyboard shortcuts
Press F1 inside ABNORA to open the shortcut reference.
Action
Shortcut
Open document
Ctrl+O
Search
Ctrl+F
Next / previous match
Enter / Shift+Enter
Previous / next page
← / →, PgUp / PgDn, Space
First / last page
Home / End
Go to page
G
Zoom in / out
+ / -
Fit page
0
Fit width
W
Rotate page
R
Single Page layout
1
Classic Book layout
2
Continuous layout
3
Navigation panel
F5
Fullscreen
F11
Distraction-free mode
F9
Switch themes
T
Bookmark current page
Ctrl+D
Document information
Ctrl+I
Keyboard shortcut reference
F1
Quit
Ctrl+Q
🏗️ Architecture
ABNORA separates PDF processing, theme management, persistence, and interface components to keep the codebase modular.
src/abnora/
├── app.py                  # Application bootstrap and AppContext
├── config.py               # Identity, paths, configuration
├── pdf/
│   ├── document.py         # PyMuPDF wrapper and document operations
│   ├── renderer.py         # Background rendering, cache, thumbnails
│   ├── navigation.py       # Layout, spread, and zoom calculations
│   └── search.py            # Asynchronous document search
├── themes/
│   ├── models.py           # Theme, font, and effect models
│   ├── definitions.py      # Declarative theme definitions
│   └── manager.py          # Theme management and stylesheet generation
├── storage/
│   ├── database.py         # SQLite persistence
│   ├── bookmarks.py        # Bookmark storage
│   ├── history.py          # Recent files and reading positions
│   └── settings.py         # Settings persistence
└── ui/
├── main_window.py      # Main window and application wiring
├── toolbar.py          # Primary controls
├── reading_canvas.py   # Reading layouts and book presentation
├── page_view.py        # Page rendering, highlights, and selection
├── side_panel.py       # Outline, thumbnails, bookmarks, search
├── status_bar.py       # Reading status and messages
├── theme_browser.py    # Theme previews and appearance controls
├── effects.py          # Visual effects, including CRT scanlines
├── icons.py            # Programmatic icons and logo
└── shortcuts_dialog.py # Keyboard reference
Design principles
1. Separate the PDF engine from the UI.
Document processing, navigation calculations, and search logic are designed to be testable independently of the graphical interface.
2. Treat themes as data.
Themes are declarative design-token sets. A centralized stylesheet generator applies their colors, typography, and effects consistently.
3. Keep expensive work off the UI thread.
Page rendering and document search use background workers. Rendering uses private document handles and a bounded cache to reduce unnecessary work and memory consumption.
4. Persist only what the application needs.
SQLite and application settings store information such as recent documents, bookmarks, reading positions, and preferences.
🔒 Privacy and security
ABNORA is designed for offline reading and local document handling.
No telemetry: No usage analytics or tracking.
No accounts: No sign-in or user account is required.
No cloud dependency: Documents are processed locally.
No application-initiated network requests: The reader does not need a remote service to function.
No PDF JavaScript execution: Embedded PDF JavaScript is not executed.
No automatic remote-content fetching: Embedded remote content is not fetched by the application.
Local persistence: Reading history, bookmarks, and settings remain on the device.
Malformed or inaccessible PDFs should produce understandable errors rather than crashing the application.
Privacy describes ABNORA's intended application behavior. It is not a guarantee that every dependency or the operating system is free from network activity or vulnerabilities. Only open documents from sources you trust.
🧪 Testing
Activate your virtual environment and run:
source .venv/bin/activate
pytest
On Windows:
.venv\Scripts\activate
pytest
The test suite is intended to cover:
Valid, invalid, missing, and password-protected documents.
Page counts, navigation boundaries, mixed page sizes, and rotation.
Document search and reading-position persistence.
Bookmark and settings persistence.
Render-cache invalidation.
Theme management.
GUI behavior using the main application window.
Tests are configured to run offscreen where supported, so a graphical desktop is not necessarily required.
Capture screenshots
To regenerate the project screenshots, run:
python scripts/capture_screenshots.py
A working graphical display may be required.
🔧 Troubleshooting
Problem
Possible solution
ModuleNotFoundError: No module named 'PySide6'
Activate the correct virtual environment and install the project dependencies, or use compatible distribution packages.
ModuleNotFoundError: No module named 'pymupdf'
Install PyMuPDF with python -m pip install PyMuPDF, or install the matching system package.
externally-managed-environment
Create and activate a virtual environment instead of installing packages into system Python.
Qt platform plugin or xcb errors on Linux
Install the required Qt platform libraries for your distribution and desktop environment.
Blank or incorrectly displayed window on Wayland
Check your Qt platform-plugin dependencies. As a diagnostic, try QT_QPA_PLATFORM=xcb python main.py if XWayland is available.
macOS blocks the application
Run it from Terminal and verify that the Python environment and dependencies are installed correctly.
Windows SmartScreen warning
Verify the source before running it. ABNORA does not currently provide a signed Windows installer.
Search finds no text in a scanned document
The PDF may not contain a text layer. OCR is not currently supported.
If a problem persists, open an issue with your operating system, Python version, installation method, and relevant error output. Avoid attaching private documents or sensitive information.
⚠️ Known limitations
No OCR: Scanned documents without a text layer cannot be searched or text-selected.
Annotations and forms: Editing annotations and interactive form fields is not currently supported.
Large continuous documents: Navigating through documents containing thousands of pages may pause, particularly when jumping near the end.
Page transitions: Transitions use a smooth fade rather than a physical page-curl animation.
Platform verification: Linux is the primary tested platform. Windows and macOS support requires further verification, and platform-specific issues are welcome.
🗺️ Roadmap
Planned improvements include:
Optional OCR integration using Tesseract.
Annotation and PDF form support.
Two-page continuous reading mode.
Per-document theme overrides.
Additional accent colors and appearance presets.
More comprehensive Windows and macOS testing.
Native Windows and macOS installers.
Persistent highlights and personal notes.
The roadmap is a direction for development, not a promise that every feature is already implemented.
🤝 Contributing
Contributions, bug reports, and ideas are welcome.
Fork the repository.
Create a branch for your change.
Make your changes and add tests where appropriate.
Run pytest.
Submit a pull request describing the change.
Please read CONTRIBUTING.md for the project's contribution guidelines, if available.
Platform-specific fixes, accessibility improvements, rendering optimizations, and new theme ideas are especially welcome.
📄 License
ABNORA is released under the MIT License. See LICENSE for the complete license text.
The MIT License allows people to study, modify, distribute, and reuse the project with minimal restrictions.
ABNORA's dependencies, including Qt/PySide6 and PyMuPDF, are distributed under their respective licenses.
