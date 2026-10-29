"""批量重命名工具 —— 加序号和前缀，支持预览。

用法：
    python batch_rename.py "目录" --ext .png --prefix 图片
    python batch_rename.py "目录" --ext .png --prefix 图片 --dry-run
"""
import argparse
import shutil
from pathlib import Path

try:
    from tools.textutil import natural_key
except ImportError:  # 直接用 python tools/xxx.py 运行时，按同目录导入
    from textutil import natural_key


def build_plan(folder: Path, ext: str, prefix: str, width: int, sort_by: str = "name"):
    """生成 [(原文件, 新文件名), ...]，不真正改名。

    按文件名排序时用自然排序：1.jpg、2.jpg、10.jpg，
    否则字符串排序会变成 1、10、2，序号就错位了。
    """
    if sort_by == "name":
        key = lambda f: natural_key(f.name)
    else:
        key = lambda f: f.stat().st_mtime
    files = sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ext.lower()],
        key=key
    )
    plan = []
    for i, f in enumerate(files, start=1):
        new_name = f"{prefix}_{i:0{width}d}{f.suffix}"
        plan.append((f, new_name))
    return plan


def rename_files(src_folder, out_folder, prefix, width=3, sort_by="name"):
    """把 src_folder 里所有文件改名后**复制**到 out_folder，返回 (输出目录, info)。

    供网页版调用：网页改不了客户本地文件名，只能改名后打包给客户下载。
    """
    src = Path(src_folder)
    files = [f for f in src.iterdir() if f.is_file() and not f.name.startswith("~$")]
    if not files:
        raise ValueError(f"在 {src_folder} 里没找到文件")
    if not prefix:
        raise ValueError("新文件名前缀不能为空")

    if sort_by == "name":
        files.sort(key=lambda f: natural_key(f.name))
    else:
        files.sort(key=lambda f: f.stat().st_mtime)

    out = Path(out_folder)
    out.mkdir(parents=True, exist_ok=True)

    detail = []
    used = set()
    for i, f in enumerate(files, start=1):
        new_name = f"{prefix}_{i:0{width}d}{f.suffix}"
        # 极端情况下前缀+序号可能撞名，加个后缀避免覆盖
        while new_name in used:
            new_name = f"{prefix}_{i:0{width}d}_{len(used)}{f.suffix}"
        used.add(new_name)
        shutil.copy2(f, out / new_name)
        detail.append({"old": f.name, "new": new_name})

    return out, {"files": detail, "count": len(files)}


def main():
    p = argparse.ArgumentParser(description="批量重命名文件")
    p.add_argument("folder", help="要处理的目录")
    p.add_argument("--ext", required=True, help="文件扩展名，例如 .png")
    p.add_argument("--prefix", required=True, help="新文件名前缀")
    p.add_argument("--width", type=int, default=3, help="序号位数，默认 3")
    p.add_argument("--sort",choices=["name","mtime"], default="name",help="排列方式: name=按文件名(默认),mtime=按时间修改")
    p.add_argument("--dry-run", action="store_true", help="只预览，不改名")
    args = p.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        raise SystemExit(f"目录不存在: {folder}")

    plan = build_plan(folder, args.ext, args.prefix, args.width,args.sort)
    if not plan:
        print(f"没有找到 {args.ext} 文件")
        return

    for old, new in plan:
        if args.dry_run:
            print(f"[预览] {old.name}  ->  {new}")
        else:
            old.rename(folder / new)
            print(f"[完成] {old.name}  ->  {new}")

    print(f"\n共 {len(plan)} 个文件" + ("（预览模式，未修改）" if args.dry_run else "已重命名"))


if __name__ == "__main__":
    main()
