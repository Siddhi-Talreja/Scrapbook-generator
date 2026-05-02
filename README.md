# Scrapbook Generator 
An automated multimedia tool that transforms web-based content into digital scrapbooks and video highlights using Python.

## Key Features
* **Automated Captures:** Uses **Playwright** to navigate and capture high-quality snapshots of scrapbook layouts.
* **Video Generation:** Leverages **MoviePy** to compile images into seamless video clips.
* **Web Management:** A **Flask**-powered dashboard to manage your memories and media.
* **Secure Handling:** Integrated file security using `werkzeug`.

## Tech Stack
* **Backend:** Python (Flask)
* **Automation:** Playwright (Headless Browser)
* **Video Processing:** MoviePy
* **Frontend:** HTML5, CSS3, Jinja2

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Siddhi-Talreja/Scrapbook-generator.git
   cd Scrapbook-generator
   ```
   
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
3. Install Browser Engines (Required for Playwright):
   ```bash
    playwright install chromium
   ```
   
## How to Run

1. Start the Flask server:
   ```bash
   python app.py
   ```
   
2. Open your browser to
   http://127.0.0.1:5000
   
