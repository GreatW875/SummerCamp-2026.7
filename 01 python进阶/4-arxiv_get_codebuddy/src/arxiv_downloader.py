"""arXiv 论文下载器"""
import arxiv
import os
import urllib.request
from pathlib import Path
from typing import List, Dict


def search_papers(query: str, max_results: int = 10) -> List[Dict]:
    """搜索 arXiv 论文"""
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )

    # 使用 Client 运行搜索
    client = arxiv.Client()
    results = list(client.results(search))

    papers = []
    for result in results:
        papers.append({
            "title": result.title,
            "authors": [a.name for a in result.authors],
            "year": result.published.year,
            "abstract": result.summary,
            "pdf_url": result.pdf_url,
            "arxiv_id": result.entry_id.split("/")[-1]
        })
    return papers


def download_paper(pdf_url: str, save_path: Path) -> None:
    """下载论文 PDF"""
    os.makedirs(save_path.parent, exist_ok=True)
    urllib.request.urlretrieve(pdf_url, save_path)
    print(f"已下载: {save_path.name}")