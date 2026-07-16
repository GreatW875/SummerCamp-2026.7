#!/bin/bash

# 把当前目录下所有 .txt 文件重命名为 .md

for file in *.txt; do
    # 如果没有 .txt 文件，*.txt 会保留字面量，跳过
    if [ ! -f "$file" ]; then
        echo "没有 .txt 文件"
        break
    fi

    # ${file%.txt} 去掉末尾的 .txt，再加上 .md
    mv "$file" "${file%.txt}.md"
    echo "$file → ${file%.txt}.md"
done
