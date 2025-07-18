import fitz  # PyMuPDF
import os
from bs4 import BeautifulSoup
import base64


def convert_pdf_to_html(pdf_path, output_dir):
    """
    Converts a PDF file to a high-fidelity HTML file.

    Args:
        pdf_path (str): The path to the PDF file.
        output_dir (str): The directory to save the HTML file and images.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    doc = fitz.open(pdf_path)

    # --- Font Extraction ---
    font_styles = ""
    processed_fonts = {}  # Use dict to map font base name to its unique CSS name
    for page in doc:
        for font in page.get_fonts(full=True):
            xref = font[0]
            basefont = font[3]
            if basefont in processed_fonts:
                continue

            try:
                # Sanitize font name for CSS, using xref for uniqueness
                font_name = f"font_{xref}"
                processed_fonts[basefont] = font_name

                font_data = doc.extract_font(xref)
                if not font_data or not font_data[1]:
                    print(f"Warning: No font data for {basefont} (xref: {xref}). Skipping.")
                    continue

                # 确保字体数据是字节类型
                font_buffer = font_data[1]
                if isinstance(font_buffer, str):
                    font_buffer = font_buffer.encode('utf-8')

                font_ext = font_data[0]

                font_mimetype = {
                    "ttf": "font/truetype",
                    "otf": "font/opentype",
                    "woff": "font/woff",
                    "woff2": "font/woff2",
                }.get(font_ext, "application/octet-stream")

                font_base64 = base64.b64encode(font_buffer).decode('utf-8')

                font_styles += (
                    f"@font-face {{\n"
                    f"  font-family: '{font_name}';\n"
                    f"  src: url(data:{font_mimetype};base64,{font_base64});\n"
                    f"}}\n"
                )
            except Exception as e:
                print(f"Warning: Could not extract font {basefont}: {e}")

    # --- HTML and CSS Setup ---
    styles = f"""
        body {{
            background-color: #f0f0f0;
            margin: 0;
            font-family: sans-serif;
        }}
        .page {{
            position: relative;
            margin: 20px auto;
            border: 1px solid #ccc;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            background-color: white;
            overflow: hidden;
        }}
        .block {{
            position: absolute;
            white-space: pre;
        }}
        img {{
            position: absolute;
            object-fit: none;  /* 不缩放图片 */
            image-rendering: -webkit-optimize-contrast;  /* 提高图片清晰度 */
            image-rendering: crisp-edges;
        }}
        {font_styles}
    """
    soup = BeautifulSoup(f"<html><head><meta charset=\"utf-8\"><style>{styles}</style></head><body></body></html>", "html.parser")

    # --- Page Processing ---
    for page_num, page in enumerate(doc):
        page_div = soup.new_tag("div", attrs={"class": "page",
                                             "style": f"width:{page.rect.width}px; height:{page.rect.height}px;"})
        soup.body.append(page_div)

        # Extract images
        image_list = page.get_images()
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue

                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # 获取图片在页面上的位置和变换信息
                img_bbox = None
                transform = None

                # 从页面字典中获取图片信息
                page_dict = page.get_text("dict")
                for block in page_dict["blocks"]:
                    if block.get("type") == 1 and block.get("xref") == xref:  # 图片块
                        img_bbox = block.get("bbox")
                        transform = block.get("transform", None)
                        break

                if not img_bbox:
                    # 如果在blocks中找不到，尝试从resources中获取图片信息
                    pix = fitz.Pixmap(doc, xref)
                    img_bbox = [0, 0, pix.width, pix.height]
                    pix = None

                rect = fitz.Rect(img_bbox)

                # 计算图片实际显示尺寸
                display_width = rect.width
                display_height = rect.height

                # 如果有变换矩阵，应用缩放因子
                if transform:
                    scale_x = abs(transform[0])
                    scale_y = abs(transform[3])
                    if scale_x != 0 and scale_y != 0:
                        display_width *= scale_x
                        display_height *= scale_y

                img_filename = f"page{page_num + 1}_img{img_index}.{image_ext}"
                img_path = os.path.join(output_dir, img_filename)

                with open(img_path, "wb") as img_file:
                    img_file.write(image_bytes)

                # 创建图片标签，使用精确的位置和尺寸
                style = (
                    f"left:{rect.x0}px; "
                    f"top:{rect.y0}px; "
                    f"width:{display_width}px; "
                    f"height:{display_height}px; "
                )

                img_tag = soup.new_tag("img", attrs={
                    "src": img_filename,
                    "style": style
                })
                page_div.append(img_tag)

            except Exception as e:
                print(f"Warning: Could not process image {img_index} on page {page_num + 1}: {str(e)}")
                continue

        # Extract text blocks
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b['type'] == 0:  # It's a text block
                for l in b["lines"]:
                    for s in l["spans"]:
                        text = s["text"]
                        font_name = s["font"]
                        font_size = s["size"]
                        color_int = s['color']
                        font_color = "#{:02x}{:02x}{:02x}".format((color_int >> 16) & 0xff, (color_int >> 8) & 0xff, color_int & 0xff)
                        pos = s["bbox"]

                        css_font_name = processed_fonts.get(font_name, "sans-serif")  # Fallback to sans-serif

                        style = (
                            f"left:{pos[0]}px; "
                            f"top:{pos[1]}px; "
                            f"font-family: \"{css_font_name}\"; "
                            f"font-size:{font_size}px; "
                            f"color:{font_color};"
                        )

                        span_tag = soup.new_tag("span", attrs={
                            "class": "block",
                            "style": style
                        })
                        span_tag.string = text
                        page_div.append(span_tag)

    html_path = os.path.join(output_dir, "output.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(soup.prettify()))

    print(f"Successfully converted {pdf_path} to {html_path}")