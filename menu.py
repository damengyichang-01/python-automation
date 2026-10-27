"""办公自动化工具包 —— 菜单式入口。

客户双击「启动工具包.bat」即可运行，不需要记命令。
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 没打包时（直接跑 menu.py），把项目根目录放进搜索路径，
# 这样才能 from tools import ...
# 打包成 exe 后判断目录只是临时解压位置，不依赖它。
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(HERE))

# 让中文在 Windows 控制台正常显示
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------- 延迟导入：菜单要秒开，pandas 等用到时再加载 ----------
_TOOLS = {}


def load_tool(name):
    """第一次真正用到某个工具时才导入它。

    pandas + openpyxl 导入要 0.9 秒左右。放在启动时，客户会觉得"双击了没反应"；
    放到选完功能以后再导入，菜单就能立刻出现。

    非打包运行时顺带检查依赖；打包成 exe 后依赖已内置，不必检查。
    """
    if not _TOOLS:
        if not getattr(sys, "frozen", False):
            _missing = []
            for _m in ("pandas", "openpyxl"):
                try:
                    __import__(_m)
                except ImportError:
                    _missing.append(_m)
            if _missing:
                print("\n缺少运行需要的组件：", "、".join(_missing))
                print("请运行：python -m pip install " + " ".join(_missing))
                read("按回车返回菜单...")
                return None
        from tools import batch_rename, clean_excel, merge_excel, reconcile
        _TOOLS.update(
            batch_rename=batch_rename,
            clean_excel=clean_excel,
            merge_excel=merge_excel,
            reconcile=reconcile,
        )
    return _TOOLS.get(name)


def show_menu():
    print()
    print("=" * 48)
    print("            办公自动化工具包")
    print("=" * 48)
    print("  1  批量重命名文件")
    print("  2  合并多个 Excel / CSV")
    print("  3  清洗 Excel（去重 / 补空 / 统一日期）")
    print("  4  两表对账（找出对不上的记录）")
    print("  0  退出")
    print("-" * 48)


def read(prompt):
    """读一行输入。输入流结束（窗口被关、或管道结束）时返回 None，不抛异常。"""
    try:
        s = input(prompt)
    except EOFError:
        print()
        return None
    return s.replace("\ufeff", "").strip()


def ask(prompt, default="", required=True):
    """问一个问题。

    required=False 时允许直接回车跳过（用于"可选"的问题）。
    """
    hint = f"（直接回车用 {default}）" if default else ""
    if not required:
        hint = hint or "（直接回车跳过）"
    while True:
        s = read(f"{prompt}{hint}: ")
        if s is None:
            raise SystemExit(0)
        if s:
            return s
        if default:
            return default
        if not required:
            return ""
        print("  这一项不能空，请重新输入。")


def run(func, argv):
    """临时替换 sys.argv 调用工具的 main()。"""
    old = sys.argv
    try:
        sys.argv = argv
        func()
    except SystemExit as e:
        code = e.code
        if isinstance(code, str):
            print(f"\n[提示] {code}")
        elif code not in (0, None):
            print(f"\n[提示] 程序以退出码 {code} 结束")
    except FileNotFoundError as e:
        print(f"\n[提示] 找不到文件：{e.filename or e}")
        print("       请检查路径是否写对，或是文件是否被移动/删除。")
    except PermissionError as e:
        print(f"\n[提示] 没有权限读写：{e.filename or e}")
        print("       文件可能正被 Excel 打开，关掉再试一次。")
    except KeyError as e:
        print(f"\n[提示] 表格里没有这一列：{e}")
        print("       可以用功能 0 之外的选项重新输入正确的列名。")
    except Exception as e:
        print(f"\n[出错] {type(e).__name__}: {e}")
    finally:
        sys.argv = old
    print()
    read("按回车返回菜单...")


def opt_rename():
    print("\n--- 批量重命名文件 ---\n")
    folder = ask("要处理的文件夹路径（可以直接把文件夹拖进来）")
    ext = ask("只处理哪种文件", ".png")
    prefix = ask("新文件名前缀", "文件")
    preview = ask("先预览不改名？输入 n 直接改名", "y")
    argv = ["batch_rename.py", folder, "--ext", ext, "--prefix", prefix]
    if preview.lower() != "n":
        argv.append("--dry-run")
    tool = load_tool("batch_rename")
    if tool:
        run(tool.main, argv)


def opt_merge():
    print("\n--- 合并多个 Excel / CSV ---\n")
    print("把要合并的文件都放进同一个文件夹，然后告诉我文件夹在哪。\n")
    folder = ask("文件夹路径")
    out = ask("结果保存成", "合并结果.xlsx")
    tool = load_tool("merge_excel")
    if tool:
        run(tool.main, ["merge_excel.py", folder, "-o", out])


def opt_clean():
    print("\n--- 清洗 Excel ---\n")
    src = ask("要清洗的 Excel 文件路径")
    out = ask("结果保存成", "清洗结果.xlsx")
    dedup = ask("按哪一列去重？不填就整行完全一样才删", "", required=False)
    argv = ["clean_excel.py", src, "-o", out]
    if dedup:
        argv += ["--dedup-by", dedup]
    tool = load_tool("clean_excel")
    if tool:
        run(tool.main, argv)


def opt_reconcile():
    print("\n--- 两表对账 ---\n")
    a = ask("表 A 的路径（比如系统导出的表）")
    b = ask("表 B 的路径（比如手工记的表）")
    key = ask("用哪一列匹配两张表", "订单号")
    compare = ask("要比对哪一列", "金额")
    out = ask("结果保存成", "对账结果.xlsx")
    tool = load_tool("reconcile")
    if tool:
        run(tool.main,
            ["reconcile.py", a, b, "--key", key, "--compare", compare, "-o", out])


def main():
    actions = {"1": opt_rename, "2": opt_merge, "3": opt_clean, "4": opt_reconcile}
    while True:
        show_menu()
        choice = read("请选择 0-4: ")
        if choice is None or choice == "0":
            print("\n再见。")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("\n没有这个选项，请重新选择。")
            read("按回车继续...")


if __name__ == "__main__":
    main()
