"""办公自动化工具包 · 网页版

启动（在项目根目录 E:\\code\\week1 下）：
    py -3.12 -m uvicorn webapp.app:app --reload --port 8000

然后浏览器打开 http://127.0.0.1:8000
"""
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_rename import rename_files  # noqa: E402
from tools.clean_excel import clean_file  # noqa: E402
from tools.merge_excel import merge_folder  # noqa: E402
from tools.pdf_merge import merge_pdfs  # noqa: E402
from tools.reconcile import reconcile_files  # noqa: E402
from tools.word_tool import replace_in_folder  # noqa: E402

import pandas as pd  # noqa: E402

app = FastAPI(title="办公自动化工具包")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

# 首页上展示的工具清单。done=False 的先占位，避免点进去是空页面。
TOOLS = [
    {"slug": "merge", "no": 1, "name": "合并多个 Excel / CSV", "desc": "多张表合成一张，按列名自动对齐", "done": True},
    {"slug": "clean", "no": 2, "name": "清洗 Excel", "desc": "去重、补空、统一日期格式", "done": True},
    {"slug": "reconcile", "no": 3, "name": "两表对账", "desc": "找出只在A、只在B、字段不符的记录", "done": True},
    {"slug": "rename", "no": 4, "name": "批量重命名", "desc": "给文件加序号和前缀", "done": True},
    {"slug": "pdf", "no": 5, "name": "PDF 合并 / 拆分", "desc": "多个 PDF 合成一个，或拆成单页", "done": True},
    {"slug": "word", "no": 6, "name": "Word 批量处理", "desc": "批量替换文字、汇总表格", "done": True},
]


# ---------- 结果文件暂存 ----------
# 处理完先把文件放临时目录，把下载链接发回页面；用户点下载后再删。
# 本地单人使用，用内存字典够了。多用户部署时该换成 Redis 或对象存储。
_RESULTS = {}
_RESULT_TTL = 600  # 10 分钟后过期


def store_result(path: Path, filename: str) -> str:
    """登记一个待下载的结果，返回下载用的 token。"""
    now = time.time()
    for k, v in list(_RESULTS.items()):
        if now - v[2] > _RESULT_TTL:
            Path(v[0]).parent.exists() and shutil.rmtree(Path(v[0]).parent, ignore_errors=True)
            _RESULTS.pop(k, None)
    token = uuid.uuid4().hex
    _RESULTS[token] = (str(path), filename, now)
    return token


def friendly_error(msg: str, work: Path) -> str:
    """把内部错误信息翻译成客户能看懂的话，顺便藏掉服务器路径。"""
    m = msg.replace(str(work), "你上传的文件")
    if "没找到" in m:
        return "没有找到可处理的表格文件。请确认上传的是 .xlsx / .xlsm / .csv。"
    if "目录不存在" in m or "文件不存在" in m:
        return "上传的文件不存在，请重新选择。"
    return m


async def save_upload(f: UploadFile, folder: Path) -> Path:
    """把上传的文件写到指定目录，返回落盘路径。"""
    name = Path(f.filename or "未命名").name
    target = folder / name
    with target.open("wb") as fp:
        fp.write(await f.read())
    return target


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"tools": TOOLS})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/download/{token}")
def download(token: str):
    item = _RESULTS.pop(token, None)
    if not item:
        return HTMLResponse("<h1>下载链接已过期</h1><p><a href='/'>返回首页</a></p>", status_code=404)
    path, filename, _ = item
    return FileResponse(
        path=path,
        filename=filename,
        background=BackgroundTask(shutil.rmtree, Path(path).parent, ignore_errors=True),
    )


# ---------------- 功能 1：合并 Excel ----------------
@app.get("/merge", response_class=HTMLResponse)
def merge_page(request: Request):
    return templates.TemplateResponse(request, "merge.html", {"error": None})


@app.post("/merge")
async def merge_submit(request: Request, files: list[UploadFile] = File(...)):
    if not files:
        return templates.TemplateResponse(
            request, "merge.html", {"error": "没有收到文件，请重新选择"}, status_code=400
        )

    work = Path(tempfile.mkdtemp(prefix="merge_"))
    try:
        for f in files:
            await save_upload(f, work)
        merged, info = merge_folder(work)
        out = work / "合并结果.xlsx"
        merged.to_excel(out, index=False)
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "merge.html", {"error": friendly_error(str(e), work)}, status_code=400
        )
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "merge.html",
            {"error": f"处理失败：{type(e).__name__}: {e}"}, status_code=500
        )

    return FileResponse(
        path=out,
        filename="合并结果.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(shutil.rmtree, work, ignore_errors=True),
    )


# ---------------- 功能 2：清洗 Excel ----------------
@app.get("/clean", response_class=HTMLResponse)
def clean_page(request: Request):
    return templates.TemplateResponse(request, "clean.html", {"error": None})


@app.post("/clean")
async def clean_submit(
    request: Request,
    file: UploadFile = File(...),
    dedup_by: str = Form(""),
):
    work = Path(tempfile.mkdtemp(prefix="clean_"))
    try:
        src = await save_upload(file, work)
        dedup = [c.strip() for c in dedup_by.split(",") if c.strip()] or None
        cleaned, report = clean_file(src, dedup_by=dedup)
        out = work / "清洗结果.xlsx"
        cleaned.to_excel(out, index=False)
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "clean.html", {"error": friendly_error(str(e), work)}, status_code=400
        )
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "clean.html",
            {"error": f"处理失败：{type(e).__name__}: {e}"}, status_code=500
        )

    token = store_result(out, "清洗结果.xlsx")
    preview = cleaned.head(10).to_html(index=False, classes="preview", border=0)
    return templates.TemplateResponse(request, "result.html", {
        "title": "清洗完成",
        "report": [
            ("删除重复行", f"{report['去重']} 行"),
            ("填充空值", f"{report['补空']} 个单元格"),
            ("日期归一", f"{report['日期归一']} 个单元格"),
            ("原始行数", f"{report['原始行数']} 行"),
            ("清洗后行数", f"{report['清洗后行数']} 行"),
        ],
        "preview": preview,
        "download_url": f"/download/{token}",
        "filename": "清洗结果.xlsx",
    })


# ---------------- 功能 3：两表对账 ----------------
@app.get("/reconcile", response_class=HTMLResponse)
def reconcile_page(request: Request):
    return templates.TemplateResponse(request, "reconcile.html", {"error": None})


@app.post("/reconcile")
async def reconcile_submit(
    request: Request,
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    key: str = Form("订单号"),
    compare: str = Form("金额"),
):
    work = Path(tempfile.mkdtemp(prefix="rec_"))
    try:
        pa = await save_upload(file_a, work)
        pb = await save_upload(file_b, work)
        compare_cols = [c.strip() for c in compare.split(",") if c.strip()]
        only_a, only_b, diff, info = reconcile_files(
            pa, pb, key=(key.strip() or "订单号"), compare_cols=compare_cols
        )
        out = work / "对账结果.xlsx"
        with pd.ExcelWriter(out) as w:
            only_a.to_excel(w, sheet_name="只在A表", index=False)
            only_b.to_excel(w, sheet_name="只在B表", index=False)
            diff.to_excel(w, sheet_name="值不同", index=False)
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "reconcile.html",
            {"error": friendly_error(str(e), work)}, status_code=400
        )
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "reconcile.html",
            {"error": f"处理失败：{type(e).__name__}: {e}"}, status_code=500
        )

    token = store_result(out, "对账结果.xlsx")
    if len(diff):
        preview = diff.head(10).to_html(index=False, classes="preview", border=0)
    else:
        preview = "<p class='hint'>两边完全一致，没有发现差异 🎉</p>"

    return templates.TemplateResponse(request, "result.html", {
        "title": "对账完成",
        "report": [
            ("A 表", f"{info['rows_a']} 行"),
            ("B 表", f"{info['rows_b']} 行"),
            ("匹配用的列", info["key"]),
            ("比对的字段", "、".join(info["compare_cols"])),
            ("只在 A 表", f"{len(only_a)} 条"),
            ("只在 B 表", f"{len(only_b)} 条"),
            ("字段不符", f"{len(diff)} 条"),
        ],
        "preview": preview,
        "download_url": f"/download/{token}",
        "filename": "对账结果.xlsx",
    })


# ---------------- 功能 4：PDF 合并 ----------------
@app.get("/pdf", response_class=HTMLResponse)
def pdf_page(request: Request):
    return templates.TemplateResponse(request, "pdf.html", {"error": None})


@app.post("/pdf")
async def pdf_submit(request: Request, files: list[UploadFile] = File(...)):
    if not files:
        return templates.TemplateResponse(
            request, "pdf.html", {"error": "没有收到文件，请重新选择"}, status_code=400
        )

    work = Path(tempfile.mkdtemp(prefix="pdf_"))
    try:
        for f in files:
            await save_upload(f, work)
        out = work / "合并结果.pdf"
        info = merge_pdfs(work, out)
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "pdf.html", {"error": friendly_error(str(e), work)}, status_code=400
        )
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "pdf.html",
            {"error": f"处理失败：{type(e).__name__}: {e}"}, status_code=500
        )

    token = store_result(out, "合并结果.pdf")
    rows = "".join(
        f"<tr><td>{d['name']}</td><td style='text-align:right'>{d['pages']}</td>"
        f"<td>{d['note']}</td></tr>"
        for d in info["files"]
    )
    preview = (
        "<table class='preview'><thead><tr><th>文件</th>"
        "<th style='text-align:right'>页数</th><th>说明</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return templates.TemplateResponse(request, "result.html", {
        "title": "PDF 合并完成",
        "report": [
            ("文件数", f"{info['count']} 个"),
            ("合计页数", f"{info['pages']} 页"),
        ],
        "preview": preview,
        "download_url": f"/download/{token}",
        "filename": "合并结果.pdf",
    })


# ---------------- 功能 5：Word 批量替换 ----------------
@app.get("/word", response_class=HTMLResponse)
def word_page(request: Request):
    return templates.TemplateResponse(request, "word.html", {"error": None})


@app.post("/word")
async def word_submit(
    request: Request,
    files: list[UploadFile] = File(...),
    old: str = Form(""),
    new: str = Form(""),
):
    if not files:
        return templates.TemplateResponse(
            request, "word.html", {"error": "没有收到文件，请重新选择"}, status_code=400
        )

    work = Path(tempfile.mkdtemp(prefix="word_"))
    try:
        src = work / "in"
        src.mkdir()
        for f in files:
            await save_upload(f, src)
        out_dir = work / "out"
        out_dir, info = replace_in_folder(src, old, new, out_dir)
        if info["changed"] == 0:
            raise ValueError(f"所有文件里都没有找到「{old}」，没有可输出的文件")

        # 多个 docx 打成 zip，浏览器一次下载
        zip_base = work / "替换结果"
        zip_path = Path(shutil.make_archive(str(zip_base), "zip", root_dir=str(out_dir)))
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "word.html", {"error": friendly_error(str(e), work)}, status_code=400
        )
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "word.html",
            {"error": f"处理失败：{type(e).__name__}: {e}"}, status_code=500
        )

    token = store_result(zip_path, "替换结果.zip")
    rows = "".join(
        f"<tr><td>{d['name']}</td><td style='text-align:right'>{d['paras']}</td>"
        f"<td>{d['note']}</td></tr>"
        for d in info["files"]
    )
    preview = (
        "<table class='preview'><thead><tr><th>文件</th>"
        "<th style='text-align:right'>替换段数</th><th>说明</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    return templates.TemplateResponse(request, "result.html", {
        "title": "Word 替换完成",
        "report": [
            ("处理文件", f"{info['count']} 个"),
            ("有替换的文件", f"{info['changed']} 个"),
            ("替换段落合计", f"{info['total_hits']} 段"),
        ],
        "preview": preview,
        "download_url": f"/download/{token}",
        "filename": "替换结果.zip",
    })


# ---------------- 功能 6：批量重命名 ----------------
@app.get("/rename", response_class=HTMLResponse)
def rename_page(request: Request):
    return templates.TemplateResponse(request, "rename.html", {"error": None})


@app.post("/rename")
async def rename_submit(
    request: Request,
    files: list[UploadFile] = File(...),
    prefix: str = Form("文件"),
    width: int = Form(3),
):
    if not files:
        return templates.TemplateResponse(
            request, "rename.html", {"error": "没有收到文件，请重新选择"}, status_code=400
        )

    width = max(1, min(int(width or 3), 6))
    work = Path(tempfile.mkdtemp(prefix="rename_"))
    try:
        src = work / "in"
        src.mkdir()
        for f in files:
            await save_upload(f, src)
        out_dir, info = rename_files(src, work / "out", prefix, width=width)
        zip_base = work / "重命名结果"
        zip_path = Path(shutil.make_archive(str(zip_base), "zip", root_dir=str(out_dir)))
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "rename.html", {"error": friendly_error(str(e), work)}, status_code=400
        )
    except Exception as e:
        shutil.rmtree(work, ignore_errors=True)
        return templates.TemplateResponse(
            request, "rename.html",
            {"error": f"处理失败：{type(e).__name__}: {e}"}, status_code=500
        )

    token = store_result(zip_path, "重命名结果.zip")
    rows = "".join(
        f"<tr><td>{d['old']}</td><td>→</td><td>{d['new']}</td></tr>"
        for d in info["files"]
    )
    preview = (
        "<table class='preview'><thead><tr><th>原文件名</th><th></th>"
        f"<th>新文件名</th></tr></thead><tbody>{rows}</tbody></table>"
    )
    return templates.TemplateResponse(request, "result.html", {
        "title": "重命名完成",
        "report": [
            ("文件数", f"{info['count']} 个"),
            ("新名字前缀", prefix),
        ],
        "preview": preview,
        "download_url": f"/download/{token}",
        "filename": "重命名结果.zip",
    })




