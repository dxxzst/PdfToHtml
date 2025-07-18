import fitz  # PyMuPDF
import os
from bs4 import BeautifulSoup
import base64

def convert_pdf_to_html(pdf_path, output_dir):
    """
    Converts a PDF file to a high-fidelity HTML file, preserving layout,
    fonts, images, and vector graphics.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(pdf_path)
    
    # --- Overall Setup ---
    font_styles = ""
    processed_fonts = {}

    # --- 1. Font Extraction ---
    # Must be done first across all pages to ensure all fonts are available.
    for page in doc:
        for font in page.get_fonts(full=True):
            xref = font[0]
            basefont = font[3]
            if basefont in processed_fonts:
                continue
            try:
                font_name = f"font_{xref}"
                processed_fonts[basefont] = font_name
                font_data = doc.extract_font(xref)
                if not (font_data and font_data[1]):
                    continue
                font_buffer = font_data[1]
                if isinstance(font_buffer, str):
                    font_buffer = font_buffer.encode('utf-8')
                font_ext = font_data[0]
                font_mimetype = {
                    "ttf": "font/truetype", "otf": "font/opentype",
                    "woff": "font/woff", "woff2": "font/woff2"
                }.get(font_ext, "application/octet-stream")
                font_base64 = base64.b64encode(font_buffer).decode('utf-8')
                font_styles += (
                    f"@font-face {{ font-family: '{font_name}'; "
                    f"src: url(data:{font_mimetype};base64,{font_base64}); }}\n"
                )
            except Exception as e:
                print(f"Warning: Could not extract font {basefont}: {e}")

    # --- 2. HTML and CSS Structure ---
    styles = f"""
        body {{ background-color: #f0f0f0; margin: 0; }}
        .page {{
            position: relative; margin: 20px auto;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            background-color: white; overflow: hidden;
        }}
        .drawing {{ position: absolute; left: 0; top: 0; z-index: 0; }}
        .block {{ position: absolute; white-space: pre; z-index: 2; }}
        img {{ position: absolute; z-index: 1; }}
    """
    soup = BeautifulSoup(f"<html><head><meta charset=\"utf-8\"><style>{styles}{font_styles}</style></head><body></body></html>", "html.parser")

    # --- 3. Page by Page Processing ---
    for page_num, page in enumerate(doc):
        page_div = soup.new_tag("div", attrs={
            "class": "page",
            "style": f"width:{page.rect.width:.2f}px; height:{page.rect.height:.2f}px;"
        })
        soup.body.append(page_div)

        # --- Vector Graphics (SVG) ---
        drawings = page.get_drawings()
        if drawings:
            svg_container = soup.new_tag("svg", attrs={
                "class": "drawing", "width": f"{page.rect.width:.2f}", "height": f"{page.rect.height:.2f}",
                "xmlns": "http://www.w3.org/2000/svg"
            })
            for path in drawings:
                stroke_color = f"rgb({path['color'][0]*255:.0f},{path['color'][1]*255:.0f},{path['color'][2]*255:.0f})" if path.get("color") else "none"
                fill_color = f"rgb({path['fill'][0]*255:.0f},{path['fill'][1]*255:.0f},{path['fill'][2]*255:.0f})" if path.get("fill") else "none"
                d_cmds = []
                for item in path["items"]:
                    cmd, *points = item
                    if cmd == "l": d_cmds.append(f"M {points[0].x:.2f} {points[0].y:.2f} L {points[1].x:.2f} {points[1].y:.2f}")
                    elif cmd == "re": d_cmds.append(f"M {points[0].x0:.2f} {points[0].y0:.2f} H {points[0].x1:.2f} V {points[0].y1:.2f} H {points[0].x0:.2f} Z")
                    elif cmd == "c": d_cmds.append(f"M {points[0].x:.2f} {points[0].y:.2f} C {points[1].x:.2f} {points[1].y:.2f} {points[2].x:.2f} {points[2].y:.2f} {points[3].x:.2f} {points[3].y:.2f}")
                if not d_cmds: continue
                stroke_width = path.get("width")
                if stroke_width is None:
                    stroke_width = 1
                path_tag = soup.new_tag("path", attrs={
                    "d": " ".join(d_cmds), "stroke": stroke_color, "fill": fill_color,
                    "stroke-width": f"{stroke_width:.2f}",
                })
                svg_container.append(path_tag)
            page_div.append(svg_container)

        # --- Images ---
        for img_info in page.get_images(full=True):
            try:
                xref = img_info[0]
                if xref == 0: continue
                base_image = doc.extract_image(xref)
                if not base_image: continue
                
                # Use page.get_image_bbox to get the transformed position
                img_bbox = page.get_image_bbox(img_info)
                if not img_bbox.is_valid: continue

                img_filename = f"page{page_num + 1}_img{xref}.{base_image['ext']}"
                img_path = os.path.join(output_dir, img_filename)
                with open(img_path, "wb") as img_file: img_file.write(base_image["image"])
                
                img_tag = soup.new_tag("img", attrs={
                    "src": img_filename,
                    "style": f"left:{img_bbox.x0:.2f}px; top:{img_bbox.y0:.2f}px; width:{img_bbox.width:.2f}px; height:{img_bbox.height:.2f}px;"
                })
                page_div.append(img_tag)
            except Exception as e:
                print(f"Warning: Could not process image xref {img_info[0]} on page {page_num + 1}: {e}")

        # --- Text (using accurate baseline positioning) ---
        for b in page.get_text("rawdict")["blocks"]:
            if b['type'] == 0:
                for l in b["lines"]:
                    for s in l["spans"]:
                        font_color = "#{:02x}{:02x}{:02x}".format((s['color'] >> 16) & 0xff, (s['color'] >> 8) & 0xff, s['color'] & 0xff)
                        
                        # Use text origin (baseline) and ascender to calculate CSS 'top'
                        origin_x, origin_y = s['origin']
                        ascender = s.get('ascender', 0.8) # Default ascender if not available
                        
                        # CSS top is the top of the bounding box. PDF origin is the baseline.
                        # Approximate top by shifting baseline up by the font's ascent.
                        adjusted_top = origin_y - (s['size'] * ascender)

                        style = (
                            f"left:{origin_x:.2f}px; top:{adjusted_top:.2f}px; "
                            f"font-family: \"{processed_fonts.get(s['font'], 'sans-serif')}\"; "
                            f"font-size:{s['size']:.2f}px; color:{font_color};"
                        )
                        span_tag = soup.new_tag("span", attrs={"class": "block", "style": style})
                        # In 'rawdict' mode, text must be reconstructed from individual characters.
                        span_text = "".join(c["c"] for c in s["chars"])
                        span_tag.string = span_text
                        page_div.append(span_tag)

    # --- 4. Final Output ---
    html_path = os.path.join(output_dir, "output.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    print(f"Successfully converted {pdf_path} to {html_path}")
