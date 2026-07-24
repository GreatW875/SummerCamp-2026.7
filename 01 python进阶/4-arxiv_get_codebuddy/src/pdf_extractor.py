"""PDF 内容提取器"""
import fitz  # PyMuPDF
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Any


def extract_text_by_page(pdf_path: Path) -> List[str]:
    """按页提取文本"""
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages


def extract_images(pdf_path: Path, output_dir: Path) -> List[str]:
    """提取图片"""
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []

    for page_num, page in enumerate(doc):
        for img_idx, img in enumerate(page.get_images()):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            img_path = output_dir / f"page{page_num + 1}_img{img_idx + 1}.{image_ext}"
            with open(img_path, "wb") as f:
                f.write(image_bytes)
            image_paths.append(str(img_path.name))

    doc.close()
    return image_paths


def extract_tables(pdf_path: Path) -> List[Dict]:
    """提取表格（简化版）"""
    doc = fitz.open(pdf_path)
    tables = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        lines = text.split("\n")
        # 简单启发式：查找包含多列数字的行
        potential_table = [line for line in lines
                          if re.search(r'\d+\.\d+\s+\d+\.\d+|\d+\s+\d+\s+\d+', line)]
        if len(potential_table) >= 2:
            tables.append({
                "page": page_num + 1,
                "content": "\n".join(potential_table[:5])
            })

    doc.close()
    return tables


def extract_references(text: str) -> List[str]:
    """提取参考文献"""
    ref_start = re.search(r'(References|Bibliography|REFERENCES)', text, re.IGNORECASE)
    if not ref_start:
        return []

    ref_text = text[ref_start.end():]
    # 匹配 [1] 或 数字. 开头的引用
    pattern = r'(?:\[\d+\]|\d+\.)\s*[A-Z].*?(?=(?:\[\d+\]|\d+\.)|$)'
    matches = re.findall(pattern, ref_text, re.DOTALL)
    return [m.strip()[:200] for m in matches[:10]]  # 取前10条，每条截断


def extract_paper_content(pdf_path: Path, paper_dir: Path) -> Dict[str, Any]:
    """提取论文所有内容"""
    images_dir = paper_dir / "images"

    # 提取文本
    pages = extract_text_by_page(pdf_path)
    full_text = "\n".join(pages)

    # 提取标题（第一页前几行）
    title = pages[0].split("\n")[0].strip() if pages else "Unknown"

    # 提取摘要
    abstract_match = re.search(
        r'Abstract\s*(.*?)(?=\n{2,}|Introduction|1\s)',
        full_text, re.DOTALL | re.IGNORECASE
    )
    abstract = abstract_match.group(1).strip() if abstract_match else ""

    # 提取图片、表格、参考文献
    images = extract_images(pdf_path, images_dir)
    tables = extract_tables(pdf_path)
    references = extract_references(full_text)

    return {
        "title": title,
        "abstract": abstract,
        "full_text": full_text,
        "images": images,
        "tables": tables,
        "references": references
    }