# -*- coding: utf-8 -*-
"""Bộ đếm Claude — script hook trên máy (seam 1).

Chạy script ĐÚNG như Claude Code gọi: process con, stdin JSON của hook Stop, biến môi trường
`CLAUDE_PLUGIN_OPTION_KHOA_CLAUDE` + `CLAUDE_PLUGIN_DATA`, với HOME giả chứa log mẫu và một máy chủ
HTTP giả chạy cục bộ (ghi lại TỪNG BYTE nhận được). Không import hàm nội bộ của script.

`APP_THEU_DEM_DONG_BO=1` = chạy luôn trong process hook (không tách nền) để test đọc kết quả ngay;
một ca riêng kiểm chế độ tách nền thật.

Chạy: python3 -B tests/test_dem_claude.py   (không cần pytest; pytest cũng chạy được)
"""
from __future__ import annotations

import http.server
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "app-theu" / "scripts" / "dem_claude.py"
KHOA = "atk_khoa_thu_nghiem_0123456789"
BI_MAT = "NOI_DUNG_CHAT_BI_MAT_xyz"
DUONG_DAN = "/home/huy/App/du_an_bi_mat"


# ============================================================ máy chủ giả
class _MayChu:
    def __init__(self):
        self.nhan: list[dict] = []        # mỗi request: {"headers":..., "raw": bytes, "json":...}
        self.da_co: set[str] = set()
        self.ma_tra = 200
        chu = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n)
                try:
                    body = json.loads(raw)
                except Exception:  # noqa: BLE001
                    body = None
                chu.nhan.append({"headers": dict(self.headers), "raw": raw, "json": body, "path": self.path})
                if chu.ma_tra != 200:
                    self.send_response(chu.ma_tra)
                    self.end_headers()
                    return
                moi = trung = 0
                for l in (body or {}).get("luot", []):
                    if l["ma_tin"] in chu.da_co:
                        trung += 1
                    else:
                        chu.da_co.add(l["ma_tin"])
                        moi += 1
                out = json.dumps({"ok": True, "moi": moi, "trung": trung, "loai": 0}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/api/v2/dem-claude/lo"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tat(self):
        self.srv.shutdown()
        self.srv.server_close()

    def luot(self):
        return [l for r in self.nhan if r["json"] for l in r["json"].get("luot", [])]


# ============================================================ máy giả
def _dong_assistant(ma, *, luc="2026-11-03T05:00:00.000Z", model="claude-opus-5-5", sidechain=False, usage=None):
    return {
        "parentUuid": "p", "isSidechain": sidechain, "userType": "external",
        "cwd": DUONG_DAN, "sessionId": "ses-1", "version": "2.1.317", "gitBranch": "main",
        "entrypoint": "claude-vscode", "type": "assistant", "requestId": "req_" + ma,
        "timestamp": luc, "uuid": "u-" + ma,
        "message": {
            "id": ma, "type": "message", "role": "assistant", "model": model,
            "content": [{"type": "text", "text": BI_MAT}],
            "usage": usage or {
                "input_tokens": 3, "cache_creation_input_tokens": 120, "cache_read_input_tokens": 5000,
                "cache_creation": {"ephemeral_5m_input_tokens": 20, "ephemeral_1h_input_tokens": 100},
                "output_tokens": 77, "service_tier": "standard",
                "server_tool_use": {"web_search_requests": 1, "web_fetch_requests": 0},
            },
        },
    }


def _dong_user():
    return {"type": "user", "cwd": DUONG_DAN, "sessionId": "ses-1", "timestamp": "2026-11-03T04:59:00.000Z",
            "message": {"role": "user", "content": BI_MAT}}


class _May:
    def __init__(self):
        self.goc = pathlib.Path(tempfile.mkdtemp(prefix="dem_claude_test_"))
        self.home = self.goc / "home"
        self.data = self.goc / "plugin_data"
        self.proj = self.home / ".claude" / "projects" / "-home-huy-App-du-an-bi-mat"
        self.proj.mkdir(parents=True)
        self.data.mkdir()
        self.dat_email("tk1@gmail.com")

    def dat_email(self, email):
        (self.home / ".claude.json").write_text(json.dumps({
            "oauthAccount": {"emailAddress": email, "displayName": "x"},
            "projects": {DUONG_DAN: {"lastPrompt": BI_MAT}},
        }), encoding="utf-8")

    def ghi(self, ten, dong, *, them=True):
        p = self.proj / ten
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a" if them else "w", encoding="utf-8") as f:
            for d in dong:
                f.write((d if isinstance(d, str) else json.dumps(d, ensure_ascii=False)) + "\n")
        return p

    def chay(self, url, *, khoa=KHOA, dong_bo=True, them_env=None, args=()):
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
        env.update({"HOME": str(self.home), "USERPROFILE": str(self.home),
                    "CLAUDE_PLUGIN_DATA": str(self.data), "APP_THEU_DEM_URL": url,
                    "APP_THEU_DEM_TU": "2026-11-01"})
        if khoa is not None:
            env["CLAUDE_PLUGIN_OPTION_KHOA_CLAUDE"] = khoa
        if dong_bo:
            env["APP_THEU_DEM_DONG_BO"] = "1"
        env.update(them_env or {})
        stdin = json.dumps({"session_id": "ses-1", "hook_event_name": "Stop", "cwd": DUONG_DAN,
                            "last_assistant_message": BI_MAT, "stop_hook_active": False})
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True,
                              text=True, env=env, timeout=60)

    def don(self):
        shutil.rmtree(self.goc, ignore_errors=True)


def _ca(fn):
    def boc():
        m, s = _May(), _MayChu()
        try:
            fn(m, s)
        finally:
            s.tat()
            m.don()
    boc.__name__ = fn.__name__
    return boc


# ============================================================ ca — ticket 02
@_ca
def test_gui_dung_danh_sach_trang_va_khong_lot_noi_dung(m, s):
    m.ghi("ses-1.jsonl", [_dong_user(), _dong_assistant("msg_A"), "{dòng hỏng", _dong_assistant("msg_B")])
    r = m.chay(s.url)
    assert r.returncode == 0 and r.stdout == "", (r.returncode, r.stdout, r.stderr)
    assert len(s.nhan) >= 1
    tat_ca_byte = b"".join(x["raw"] for x in s.nhan) + b"".join(
        json.dumps(x["headers"]).encode() for x in s.nhan)
    for chuoi in (BI_MAT, DUONG_DAN, "du_an_bi_mat", "du-an-bi-mat", "/home/", str(m.home)):
        assert chuoi.encode() not in tat_ca_byte, f"lọt {chuoi!r}"
    assert s.nhan[0]["headers"].get("Authorization") == f"Bearer {KHOA}"
    ds = s.luot()
    assert [l["ma_tin"] for l in ds] == ["msg_A", "msg_B"]
    a = ds[0]
    assert set(a) <= {"ma_tin", "request_id", "session_id", "luc", "model", "entrypoint", "phien_ban",
                      "la_subagent", "usage"}, sorted(a)
    assert a["usage"] == {"input_tokens": 3, "cache_creation_5m": 20, "cache_creation_1h": 100,
                          "cache_read_input_tokens": 5000, "output_tokens": 77,
                          "web_search_requests": 1, "web_fetch_requests": 0}
    assert (a["request_id"], a["luc"], a["model"], a["entrypoint"], a["phien_ban"]) == (
        "req_msg_A", "2026-11-03T05:00:00.000Z", "claude-opus-5-5", "claude-vscode", "2.1.317")


@_ca
def test_khong_gui_lai_phan_da_gui(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    m.chay(s.url)
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_B")])
    m.chay(s.url)
    m.chay(s.url)
    assert [l["ma_tin"] for l in s.luot()] == ["msg_A", "msg_B"]


@_ca
def test_dong_dang_ghi_do_chua_xuong_dong_thi_cho_lan_sau(m, s):
    p = m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(_dong_assistant("msg_B"))[:40])  # Claude đang ghi dở
    m.chay(s.url)
    assert [l["ma_tin"] for l in s.luot()] == ["msg_A"]
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_C")], them=False)  # ghi lại cả file (≈ cắt)
    m.chay(s.url)
    assert "msg_C" in [l["ma_tin"] for l in s.luot()]


@_ca
def test_bo_qua_model_synthetic_va_dong_khong_usage(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_S", model="<synthetic>"), _dong_user(),
                          {"type": "summary", "summary": BI_MAT}, _dong_assistant("msg_A")])
    m.chay(s.url)
    assert [l["ma_tin"] for l in s.luot()] == ["msg_A"]


@_ca
def test_loi_bat_ky_thoat_0_khong_in(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    s.tat()
    for kw in ({"khoa": None}, {"khoa": ""}, {}):
        r = m.chay(s.url, **kw)
        assert r.returncode == 0 and r.stdout == "" and r.stderr == "", (kw, r)
    chan = m.goc / "la_file"
    chan.write_text("x")
    r = m.chay("http://127.0.0.1:1/khong-co", them_env={"CLAUDE_PLUGIN_DATA": str(chan / "con")})
    assert r.returncode == 0 and r.stdout == ""


@_ca
def test_mot_tin_nhieu_dong_log_chi_gui_mot_lan(m, s):
    """Claude ghi mỗi khối content của MỘT tin thành một dòng, cùng message.id + cùng usage."""
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A"), _dong_assistant("msg_A"), _dong_assistant("msg_B")])
    m.ghi("ses-2.jsonl", [_dong_assistant("msg_A")])  # phiên resume chép lại lịch sử
    m.chay(s.url)
    assert sorted(l["ma_tin"] for l in s.luot()) == ["msg_A", "msg_B"]


@_ca
def test_tach_nen_hook_thoat_ngay_roi_van_gui(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    t0 = time.monotonic()
    r = m.chay(s.url, dong_bo=False)
    assert r.returncode == 0 and r.stdout == ""
    assert time.monotonic() - t0 < 5
    for _ in range(100):
        if s.luot():
            break
        time.sleep(0.1)
    assert [l["ma_tin"] for l in s.luot()] == ["msg_A"]


if __name__ == "__main__":
    import inspect
    ds = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and inspect.isfunction(f)]
    hong = 0
    for n, f in ds:
        try:
            f()
            print("✅", n)
        except Exception as e:  # noqa: BLE001
            hong += 1
            print("❌", n, type(e).__name__, e)
    print(f"{len(ds) - hong}/{len(ds)} xanh")
    sys.exit(1 if hong else 0)
