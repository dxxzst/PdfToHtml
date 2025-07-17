
import fitz  # PyMuPDF
import os
from bs4 import BeautifulSoup
from PIL import Image
import io

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
    soup = BeautifulSoup("<html><head><style>"
                         "body { margin: 0; }"
                         ".page { position: relative; }"
                         ".block { position: absolute; }"
                         "img { position: absolute; }"
                         "</style></head><body></body></html>", "html.parser")

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_div = soup.new_tag("div", attrs={"class": "page", "style": f"width:{page.rect.width}px; height:{page.rect.height}px;"})
        soup.body.append(page_div)

        # Extract images
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Get image position
            img_rects = page.get_image_rects(img)
            if not img_rects:
                continue
            
            img_rect = img_rects[0] # Use the first occurrence
            
            img_filename = f"page{page_num+1}_img{img_index}.{image_ext}"
            img_path = os.path.join(output_dir, img_filename)
            
            with open(img_path, "wb") as img_file:
                img_file.write(image_bytes)

            img_tag = soup.new_tag("img", attrs={
                "src": img_filename,
                "style": f"left:{img_rect.x0}px; top:{img_rect.y0}px; width:{img_rect.width}px; height:{img_rect.height}px;"
            })
            page_div.append(img_tag)

        # Extract text blocks
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            for l in b["lines"]:
                for s in l["spans"]:
                    text = s["text"]
                    font_size = s["size"]
                    font_color = "#{:02x}{:02x}{:02x}".format(int(s['color']) >> 16, int(s['color']) >> 8 & 0xff, int(s['color']) & 0xff)
                    pos = s["bbox"]
                    
                    span_tag = soup.new_tag("span", attrs={
                        "class": "block",
                        "style": f"left:{pos[0]}px; top:{pos[1]}px; font-size:{font_size}px; color:{font_color}; white-space: pre;"
                    })
                    span_tag.string = text
                    page_div.append(span_tag)

    html_path = os.path.join(output_dir, "output.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(str(soup.prettify()))

    print(f"Successfully converted {pdf_path} to {html_path}")
