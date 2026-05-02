import os
import json
import base64
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright
from moviepy import ImageClip, concatenate_videoclips

app = Flask(__name__)
app.secret_key = "scrapbook_secret_key"

UPLOAD_FOLDER = "static/uploads"
DATA_FILE = "data.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

LAYOUTS = {"1": 1, "2": 2, "4": 4, "6": 6}

def load_pages():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_pages(pages):
    with open(DATA_FILE, "w") as f:
        json.dump(pages, f)

def get_base64_image(img_name):
    """Encodes image to base64 to ensure it renders in headless browsers."""
    img_path = os.path.join(app.config["UPLOAD_FOLDER"], img_name)
    if os.path.exists(img_path):
        with open(img_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    pages = load_pages()
    if "current_page" not in session:
        session["current_page"] = 0
    if "scrapbook_theme" not in session:
        session["scrapbook_theme"] = "dream"

    if request.method == "POST":
        pages.append({
            "title": request.form.get("title"),
            "text": request.form.get("text"),
            "layout": request.form.get("layout"),
            "slots": [None] * LAYOUTS.get(request.form.get("layout"), 1)
        })
        save_pages(pages)
        session["current_page"] = len(pages) - 1
        return redirect(url_for("index"))

    current = session["current_page"]
    if pages and current >= len(pages):
        current = len(pages) - 1

    return render_template(
        "index.html",
        pages=pages,
        current_page=current,
        scrapbook_theme=session["scrapbook_theme"]
    )

@app.route("/set_theme", methods=["POST"])
def set_theme():
    session["scrapbook_theme"] = request.form.get("template")
    return redirect(url_for("index"))

@app.route("/add_to_slot", methods=["POST"])
def add_to_slot():
    pages = load_pages()
    file = request.files.get("image")
    slot = int(request.form.get("slot"))
    if file and file.filename:
        name = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, name))
        pages[session["current_page"]]["slots"][slot] = name
        save_pages(pages)
    return redirect(url_for("index"))

@app.route("/export_mp4")
def export_mp4():
    pages = load_pages()
    theme = session.get("scrapbook_theme", "dream")
    frames = []

    shared_css = """
    <style>
        body { margin: 0; padding: 0; background: #eee; }
        .page { width: 100%; height: 100%; position: absolute; top: 0; left: 0; padding: 80px; box-sizing: border-box; min-height: 100%; position: relative; overflow: hidden; }
        
        /* Updated Themes to match UI */
        .dream { background: linear-gradient(135deg, #fff0f6 0%, #e6e6ff 100%); color: #3E2C23; font-family: 'serif'; }
        
        .midnight { 
            background-color: #c4dfff; 
            background-image: url("https://www.transparenttextures.com/patterns/cartographer.png");
            background-blend-mode: multiply;
            background-size: 300px 300px;
            color: #fffbf8; 
        }
        .midnight h1 { color: #11273c !important; }
        .midnight p { color: #fffbf8 !important; text-shadow: 1px 1px 0px rgba(255,255,255,0.3); }

        .polaroid { 
            background: #CCD5AE; 
            background-image: linear-gradient(rgba(62, 44, 35, 0.05) 1px, transparent 1px), 
                            linear-gradient(90deg, rgba(62, 44, 35, 0.05) 1px, transparent 1px);
            background-size: 30px 30px;
            color: #3E2C23; 
        }

        .journal { 
            background: #fff; 
            background-image: repeating-linear-gradient(#fff, #fff 31px, #e5e5e5 32px); 
            color: #3E2C23; 
        }
        
        h1 { font-size: 80px; margin-top: 50px; margin-bottom: 10px; font-family: 'serif'; position: relative; z-index: 5; }
        p { font-size: 35px; width: 1000px; line-height: 1.4; font-family: 'serif'; margin-bottom: 40px; position: relative; z-index: 5; }

        .slot { 
            position: absolute; 
            background: white; 
            padding: 15px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.2); 
            z-index: 4;
        }
        /* Specific Slot styling for Midnight/Muse theme */
        .midnight .slot { padding: 10px 10px 30px 10px; border: none; }

        .slot img { width: 100%; height: 100%; object-fit: cover; display: block; }

        /* Layout styles remain the same... */
        .l-1-0 { left: 300px; top: 500px; width: 600px; height: 550px; transform: rotate(-2deg); }
        .l-2-0 { left: 80px; top: 550px; width: 500px; height: 450px; transform: rotate(-3deg); }
        .l-2-1 { left: 620px; top: 600px; width: 500px; height: 450px; transform: rotate(3deg); }
        .l-4-0 { left: 80px; top: 500px; width: 500px; height: 400px; transform: rotate(-2deg); }
        .l-4-1 { left: 620px; top: 520px; width: 500px; height: 400px; transform: rotate(2deg); }
        .l-4-2 { left: 80px; top: 950px; width: 500px; height: 400px; transform: rotate(1deg); }
        .l-4-3 { left: 620px; top: 980px; width: 500px; height: 400px; transform: rotate(-1deg); }
        .l-6-0 { left: 60px;  top: 500px; width: 340px; height: 250px; transform: rotate(-0.2deg); }
        .l-6-1 { left: 430px; top: 500px; width: 340px; height: 250px; transform: rotate(0.3deg); }
        .l-6-2 { left: 800px; top: 500px; width: 340px; height: 250px; transform: rotate(-0.1deg); }
        .l-6-3 { left: 60px;  top: 780px; width: 340px; height: 250px; transform: rotate(0.2deg); }
        .l-6-4 { left: 430px; top: 780px; width: 340px; height: 250px; transform: rotate(-0.3deg); }
        .l-6-5 { left: 800px; top: 780px; width: 340px; height: 250px; transform: rotate(0.1deg); }
    </style>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1600})
        for idx, p_data in enumerate(pages):
            slots_html = ""
            for i, img in enumerate(p_data["slots"]):
                if img:
                    b64 = get_base64_image(img)
                    if b64:
                        slots_html += f'<div class="slot l-{p_data["layout"]}-{i}"><img src="data:image/jpeg;base64,{b64}"></div>'
            
            html = f"<html><head>{shared_css}</head><body><div class='page {theme}'><h1>{p_data['title']}</h1><p>{p_data['text']}</p>{slots_html}</div></body></html>"
            page.set_content(html)
            page.wait_for_timeout(1000)
            img_path = f"static/frame_{idx}.png"
            page.screenshot(path=img_path)
            frames.append(img_path)
        browser.close()

    clips = [ImageClip(f).with_duration(3) for f in frames]
    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile("static/scrapbook.mp4", fps=24, codec="libx264")
    for f in frames: os.remove(f)
    return redirect("/static/scrapbook.mp4")

@app.route("/export_pdf")
def export_pdf():
    pages = load_pages()
    theme = session.get("scrapbook_theme", "dream")
    
    shared_css = """
    <style>
        @page { size: A4; margin: 0; }
        body { margin: 0; padding: 0; }
        .page-wrapper { width: 210mm; height: 297mm; position: relative; overflow: hidden; page-break-after: always; }
        .page { width: 100%; height: 100%; padding: 20mm; box-sizing: border-box; }
        
        /* Updated PDF Themes */
        .dream { background: linear-gradient(135deg, #fff0f6 0%, #e6e6ff 100%); color: #3E2C23; }
        
        .midnight { 
            background-color: #c4dfff; 
            background-image: url("https://www.transparenttextures.com/patterns/cartographer.png");
            background-blend-mode: multiply;
        }
        .midnight h1 { color: #11273c !important; }
        .midnight p { color: #fffbf8 !important; }

        .polaroid { 
            background: #CCD5AE; 
            background-image: linear-gradient(rgba(62, 44, 35, 0.05) 1px, transparent 1px), 
                            linear-gradient(90deg, rgba(62, 44, 35, 0.05) 1px, transparent 1px);
            background-size: 10mm 10mm;
            color: #3E2C23; 
        }

        .journal { background: #fff; background-image: repeating-linear-gradient(#fff, #fff 31px, #e5e5e5 32px); color: #3E2C23; }
        
        h1 { font-size: 40pt; font-family: 'serif'; margin-top: 0; }
        p { font-size: 18pt; line-height: 1.4; font-family: 'serif'; }
        
        .slot { position: absolute; width: 80mm; height: 65mm; background: white; padding: 4mm; box-shadow: 0 5mm 10mm rgba(0,0,0,0.1); }
        .midnight .slot { padding: 3mm 3mm 10mm 3mm; }
        .slot img { width: 100%; height: 100%; object-fit: cover; }
        
        /* PDF Layout positions remain the same... */
        .l-1-0 { left: 55mm; top: 120mm; width: 100mm; height: 80mm; transform: rotate(-2deg); }
        .l-2-0 { left: 20mm; top: 120mm; transform: rotate(-3deg); }
        .l-2-1 { left: 110mm; top: 130mm; transform: rotate(3deg); }
        .l-4-0 { left: 20mm; top: 100mm; transform: rotate(-2deg); }
        .l-4-1 { left: 110mm; top: 105mm; transform: rotate(2deg); }
        .l-4-2 { left: 20mm; top: 180mm; transform: rotate(1deg); }
        .l-4-3 { left: 110mm; top: 185mm; transform: rotate(-1deg); }
        .l-6-0 { left: 15mm;  top: 90mm;  width: 60mm; height: 45mm; transform: rotate(-1deg); }
        .l-6-1 { left: 75mm;  top: 90mm;  width: 60mm; height: 45mm; transform: rotate(1deg); }
        .l-6-2 { left: 135mm; top: 90mm;  width: 60mm; height: 45mm; transform: rotate(-1.5deg); }
        .l-6-3 { left: 15mm;  top: 140mm; width: 60mm; height: 45mm; transform: rotate(1.5deg); }
        .l-6-4 { left: 75mm;  top: 140mm; width: 60mm; height: 45mm; transform: rotate(-1deg); }
        .l-6-5 { left: 135mm; top: 140mm; width: 60mm; height: 45mm; transform: rotate(1deg); }
    </style>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        content = "<html><head>" + shared_css + "</head><body>"
        
        for p_data in pages:
            slots = ""
            for i, img in enumerate(p_data["slots"]):
                if img:
                    b64 = get_base64_image(img)
                    if b64: 
                        slots += f'<div class="slot l-{p_data["layout"]}-{i}"><img src="data:image/jpeg;base64,{b64}"></div>'
            
            # Wrapped each page in .page-wrapper to trigger the page-break
            content += f"<div class='page-wrapper'><div class='page {theme}'><h1>{p_data['title']}</h1><p>{p_data['text']}</p>{slots}</div></div>"
        
        content += "</body></html>"
        page.set_content(content)
        page.wait_for_timeout(1000)
        
        pdf_path = "static/scrapbook.pdf"
        page.pdf(path=pdf_path, format="A4", print_background=True)
        browser.close()
        
    return redirect(f"/{pdf_path}")

@app.route("/delete_image", methods=["POST"])
def delete_image():
    pages = load_pages()
    file = request.json.get("file")
    for p in pages:
        for i in range(len(p["slots"])):
            if p["slots"][i] == file: p["slots"][i] = None
    save_pages(pages)
    return {"status": "ok"}

@app.route("/reset")
def reset():
    if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
    for f in os.listdir(UPLOAD_FOLDER): os.remove(os.path.join(UPLOAD_FOLDER, f))
    session.clear()
    return redirect(url_for("index"))

@app.route("/next")
def next_page():
    pages = load_pages()
    if session["current_page"] < len(pages) - 1: session["current_page"] += 1
    return redirect(url_for("index"))

@app.route("/prev")
def prev_page():
    if session["current_page"] > 0: session["current_page"] -= 1
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)