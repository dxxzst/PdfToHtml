# PDF 转高保真 HTML 转换器

本项目是一个基于 Python 的命令行工具，旨在将 PDF 文件转换为高保真度的 HTML 文件。它会精心保留原始的布局，包括文本和图片的精确位置，以确保输出的 HTML 文件在视觉上是源 PDF 文件的忠实再现。

## 功能特性

-   **高保真转换**：保留文本元素精确的位置、大小和颜色。
-   **图片提取**：从 PDF 中提取图片，并将其嵌入到 HTML 输出中。
-   **布局保留**：每个 PDF 页面都被转换为一个对应的 `div` 层，通过绝对定位来匹配原始文档的布局。
-   **独立的输出**：生成一个 HTML 文件以及一个包含所有提取图片的目录。

## 安装

1.  **克隆仓库：**
    ```bash
    git clone <repository-url>
    cd PdfToHtml
    ```

2.  **创建虚拟环境（推荐）：**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # 在 Windows 上，使用 `.venv\Scripts\activate`
    ```

3.  **安装依赖：**
    项目使用 `pyproject.toml` 文件来定义依赖项。您可以使用 pip 来安装它们：
    ```bash
    pip install .
    ```
    这将安装 `PyMuPDF`、`beautifulsoup4` 和 `Pillow`。

## 如何使用

通过命令行运行此脚本，并提供您的 PDF 文件路径。

### 命令语法

```bash
python main.py <你的PDF文件路径> [--output_dir <输出目录>]
```

-   `<你的PDF文件路径>`: (必需) 您想要转换的 PDF 文件的完整路径。
-   `--output_dir`: (可选) 用于保存 `output.html` 文件和提取图片的目录。默认为 `output/`。

### 示例

```bash
python main.py "C:\Users\MyUser\Documents\report.pdf" --output_dir "converted_files"
```

执行后，您将在 `converted_files` 目录中找到 `output.html` 和所有提取出的图片。

## 工作原理

该转换器的工作原理是将每个 PDF 页面视为一个“画布”。它会遍历每个页面并执行以下步骤：

1.  **页面分析**：使用 `PyMuPDF` (fitz) 库逐页打开和分析 PDF 文档。
2.  **HTML 骨架构建**：使用 `BeautifulSoup4` 在内存中构建一个 HTML 文档。
3.  **元素提取**：对于每个页面，它会提取所有的文本块和图片，并捕获它们的精确坐标 (`x`, `y`)、尺寸、字体大小和颜色。
4.  **CSS 定位**：每个提取出的元素（文本或图片）都被放置在一个绝对定位的 HTML 元素中（`<span>` 用于文本，`<img>` 用于图片）。通过设置 `top` 和 `left` CSS 属性，使其与 PDF 中的原始坐标完全匹配。
5.  **文件生成**：最后，将完整的 HTML 结构写入到一个 `output.html` 文件中，并将提取的图片保存到指定的输出目录。这确保了在 Web 浏览器中的最终渲染效果与原始 PDF 布局高度一致。