"""办公自动化工具包 · 网页版

启动（在项目根目录 E:\\code\\week1 下）：
    py -3.12 -m uvicorn webapp.app:app --reload --port 8000

然后浏览器打开 http://127.0.0.1:8000
"""
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.merge_excel import merge_folder  # noqa: E402

app = FastAPI(title="办公自动化工具包")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

# 首页上展示的工具清单。done=False 的先占位，避免点进去是空页面。
TOOLS = [
    {"slug": "merge", "no": 1, "name": "合并多个 Excel / CSV", "desc": "多张表合成一张，按列名自动对齐", "done": True},
    {"slug": "clean", "no": 2, "name": "清洗 Excel", "desc": "去重、补空、统一日期格式", "done": False},
    {"slug": "reconcile", "no": 3, "name": "两表对账", "desc": "找出只在A、只在B、字段不符的记录", "done": False},
    {"slug": "rename", "no": 4, "name": "批量重命名", "desc": "给文件加序号和前缀", "done": False},
    {"slug": "pdf", "no": 5, "name": "PDF 合并 / 拆分", "desc": "多个 PDF 合成一个，或拆成单页", "done": False},
    {"slug": "word", "no": 6, "name": "Word 批量处理", "desc": "批量替换文字、汇总表格", "done": False},
]


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"tools": TOOLS})


@app.get("/merge", response_class=HTMLResponse)
def merge_page(request: Request):
    return templates.TemplateResponse(request, "merge.html", {"error": None})


def friendly_error(msg: str, work: Path) -> str:
    """把内部错误信息翻译成客户能看懂的话，顺便藏掉服务器路径。"""
    m = msg.replace(str(work), "你上传的文件")
    if "没找到" in m:
        return "没有找到可处理的表格文件。请确认上传的是 .xlsx / .xlsm / .csv。"
    if "目录不存在" in m:
        return "上传的文件夹不存在，请重试。"
    return m


@app.post("/merge")
async def merge_submit(request: Request, files: list[UploadFile] = File(...)):
    """接收多个文件，合并，然后把结果直接下载给浏览器。"""
    if not files:
        return templates.TemplateResponse(
            request, "merge.html", {"error": "没有收到文件，请重新选择"}, status_code=400
        )

    work = Path(tempfile.mkdtemp(prefix="merge_"))
    try:
        for f in files:
            # 只取文件名本身，防止上传时带进来奇怪路径
            name = Path(f.filename or "未命名").name
            target = work / name
            with target.open("wb") as fp:
                fp.write(await f.read())

        merged, info = merge_folder(work)
        out = work / "合并结果.xlsx"
        merged.to_excel(out, index=False)
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "merge.html",
            {"error": friendly_error(str(e), work)}, status_code=400
        )
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "merge.html",
            {"error": f"处理失败：{type(e).__name__}: {e}"}, status_code=500
        )

    # 下载完成后删临时目录
    return FileResponse(
        path=out,
        filename="合并结果.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(shutil.rmtree, work, ignore_errors=True),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
