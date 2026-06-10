from pathlib import Path

# ====== 在这里修改你的路径 ======
SOURCE_DIR = r"C:\Users\24130\Desktop\food"   # 要扫描的文件夹（含子文件夹）
OUTPUT_FILE = r"C:\Users\24130\Desktop\food\copy.txt"  # 合并输出的txt文件
# ==============================

def merge_md_to_txt(src_dir, output_file):
    """
    递归查找 src_dir 下所有 .md 文件，将内容按顺序合并写入 output_file。
    每个文件内容前会添加文件名和分隔标记。
    """
    src_path = Path(src_dir).resolve()
    output_path = Path(output_file).resolve()

    # 确保源目录存在
    if not src_path.is_dir():
        print(f"错误：源文件夹不存在 -> {src_path}")
        return

    # 创建输出文件所在目录（如果不存在）
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 递归查找所有 .md 文件，按路径排序保证顺序稳定
    md_files = sorted(src_path.rglob("*.md"))

    if not md_files:
        print(f"在 {src_path} 中没有找到任何 .md 文件。")
        return

    # 写入合并文件
    with output_path.open("w", encoding="utf-8") as out:
        for i, md_file in enumerate(md_files, start=1):
            try:
                content = md_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # 如果 utf-8 读取出错，尝试用系统默认编码（例如 gbk）
                try:
                    content = md_file.read_text(encoding="gbk", errors="replace")
                    print(f"注意：{md_file.name} 可能不是 utf-8 编码，已尝试用 gbk 读取。")
                except Exception as e:
                    print(f"跳过无法读取的文件 {md_file}: {e}")
                    continue

            # 写入分隔信息和内容
            out.write(f"========== 文件 {i}: {md_file.name} ==========\n")
            out.write(f"相对路径: {md_file.relative_to(src_path)}\n\n")
            out.write(content)
            out.write("\n\n")   # 文件间空两行

    print(f"完成！已将 {len(md_files)} 个 .md 文件的内容合并到 -> {output_path}")

if __name__ == "__main__":
    merge_md_to_txt(SOURCE_DIR, OUTPUT_FILE)