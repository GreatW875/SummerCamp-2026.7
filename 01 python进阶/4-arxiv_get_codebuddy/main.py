"""主程序：下载并处理 arXiv 论文"""
import json
from pathlib import Path
from src.arxiv_downloader import search_papers, download_paper
from src.pdf_extractor import extract_paper_content


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    return "".join(c if c.isalnum() or c in " -_" else "_" for c in name)


def main():
    project_dir = Path(__file__).parent
    papers_dir = project_dir / "papers"
    output_dir = project_dir / "output"

    papers_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    # 1. 搜索论文
    print("=" * 60)
    print("正在搜索 arXiv 论文...")
    query = "deep learning"  # 搜索关键词
    papers = search_papers(query, max_results=10)
    print(f"找到 {len(papers)} 篇论文\n")

    # 2. 下载并处理每篇论文
    for idx, paper in enumerate(papers, 1):
        print(f"{'=' * 60}")
        print(f"[{idx}/10] {paper['title'][:55]}...")

        # 文件夹名：index_作者姓_year
        first_author = paper["authors"][0].split()[-1] if paper["authors"] else "Unknown"
        folder_name = f"{idx:02d}_{sanitize_filename(first_author)}_{paper['year']}"
        paper_dir = output_dir / folder_name
        paper_dir.mkdir(exist_ok=True)

        # 下载 PDF
        pdf_path = papers_dir / f"{paper['arxiv_id']}.pdf"
        if not pdf_path.exists():
            try:
                download_paper(paper["pdf_url"], pdf_path)
            except Exception as e:
                print(f"  下载失败: {e}")
                continue

        # 提取内容
        print("  正在提取内容...")
        try:
            content = extract_paper_content(pdf_path, paper_dir)
        except Exception as e:
            print(f"  提取失败: {e}")
            continue

        # 保存元数据
        metadata = {
            "index": idx,
            "title": paper["title"],
            "authors": paper["authors"],
            "year": paper["year"],
            "arxiv_id": paper["arxiv_id"],
            "abstract": paper["abstract"]
        }

        # 保存各部分到 JSON
        with open(paper_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        with open(paper_dir / "abstract.json", "w", encoding="utf-8") as f:
            json.dump({"abstract": content["abstract"]}, f, ensure_ascii=False, indent=2)

        with open(paper_dir / "full_text.json", "w", encoding="utf-8") as f:
            json.dump({"text": content["full_text"][:50000]}, f, ensure_ascii=False, indent=2)  # 截断防止过大

        with open(paper_dir / "references.json", "w", encoding="utf-8") as f:
            json.dump({"references": content["references"]}, f, ensure_ascii=False, indent=2)

        # 保存表格
        if content["tables"]:
            tables_dir = paper_dir / "tables"
            tables_dir.mkdir(exist_ok=True)
            with open(tables_dir / "tables.json", "w", encoding="utf-8") as f:
                json.dump(content["tables"], f, ensure_ascii=False, indent=2)

        print(f"  完成! 图片: {len(content['images'])} 张, 表格: {len(content['tables'])} 个")

    print(f"\n{'=' * 60}")
    print("全部完成! 结果保存在 output/ 目录")


if __name__ == "__main__":
    main()