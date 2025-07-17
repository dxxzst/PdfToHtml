
import argparse
from pdf_converter.converter import convert_pdf_to_html
import os

def main():
    parser = argparse.ArgumentParser(description="Convert a PDF file to a high-fidelity HTML file.")
    parser.add_argument("pdf_path", help="The path to the PDF file to convert.")
    parser.add_argument("--output_dir", default="output", help="The directory to save the HTML file and images. Defaults to 'output'.")

    args = parser.parse_args()

    # Ensure the output directory is inside the src directory for this environment
    # In a real-world scenario, this would likely be relative to the project root or CWD.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, args.output_dir)

    convert_pdf_to_html(args.pdf_path, output_path)

if __name__ == "__main__":
    main()
