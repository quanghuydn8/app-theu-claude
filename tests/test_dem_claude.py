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
TOKEN = "sk-ant-oat01-TOKEN_BI_MAT_KHONG_DUOC_GUI"


# ============================================================ máy chủ giả
class _MayChu:
    def __init__(self):
        self.nhan: list[dict] = []        # mỗi request: {"headers":..., "raw": bytes, "json":...}
        self.da_co: set[str] = set()
        self.ma_tra = 200
        self.hoi_usage: list[dict] = []
        self.usage_ma = 200
        self.usage_tra = {"five_hour": {"utilization": 12.0, "resets_at": "2026-11-03T08:00:00+00:00"},
                          "seven_day": {"utilization": 53.0, "resets_at": "2026-11-04T06:00:00.818775+00:00"},
                          "iguana_necktie": None}
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

            def do_GET(self):  # noqa: N802 — giả đường /api/oauth/usage của Anthropic
                chu.hoi_usage.append(dict(self.headers))
                if chu.usage_ma != 200:
                    self.send_response(chu.usage_ma)
                    self.end_headers()
                    return
                out = json.dumps(chu.usage_tra).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/api/v2/dem-claude/lo"
        self.url_usage = f"http://127.0.0.1:{self.srv.server_address[1]}/api/oauth/usage"
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

    def dat_token(self, tok=TOKEN, *, het_han_ms=None):
        (self.home / ".claude").mkdir(parents=True, exist_ok=True)
        (self.home / ".claude" / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {
            "accessToken": tok, "refreshToken": "REFRESH_" + tok,
            "expiresAt": het_han_ms if het_han_ms is not None else int((time.time() + 3600) * 1000)},
            "pluginSecrets": {"app-theu@app-theu-claude": {"khoa_claude": KHOA}}}), encoding="utf-8")

    def dat_email(self, email):
        (self.home / ".claude.json").write_text(json.dumps({
            "oauthAccount": {"emailAddress": email, "displayName": "x",
                             "subscriptionCreatedAt": "2026-05-12T03:04:05.000Z", "accountUuid": "uuid-bi-mat"},
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
                    "APP_THEU_DEM_TU": "2026-11-01", "APP_THEU_DEM_URL_USAGE": url.rsplit("/api/", 1)[0] + "/api/oauth/usage"})
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


# ============================================================ ca — ticket 03 (script bền)
def _luot_gui(s):
    return [l["ma_tin"] for l in s.luot()]


@_ca
def test_may_chu_sap_de_danh_roi_gui_bu(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    m.chay("http://127.0.0.1:1/api/v2/dem-claude/lo")       # máy chủ không nối được
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_B")])
    s.ma_tra = 503
    m.chay(s.url)                                           # máy chủ lỗi 503
    assert all(r["json"] for r in s.nhan) and not s.da_co
    s.ma_tra = 200
    m.chay(s.url)
    assert sorted(s.da_co) == ["msg_A", "msg_B"]
    m.chay(s.url)
    assert sorted(_luot_gui(s)).count("msg_A") == 2         # 1 lần bị 503 + 1 lần nhận — không thêm nữa


@_ca
def test_lo_bi_tu_choi_4xx_bo_lo_do_khong_tac_ca_hang(m, s):
    """400/413 = lô hỏng vĩnh viễn ⇒ bỏ lô đó (ghi nhật ký), các lô sau vẫn đi. 401 (khoá sai) mới giữ lại."""
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    s.ma_tra = 413
    m.chay(s.url)
    s.ma_tra = 200
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_B")])
    m.chay(s.url)
    assert sorted(s.da_co) == ["msg_B"]
    assert "bỏ lô" in (m.data / "dem_claude" / "nhat_ky.log").read_text(encoding="utf-8")


@_ca
def test_khoa_sai_401_giu_lo_cho_doi_khoa(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    s.ma_tra = 401
    m.chay(s.url)
    s.ma_tra = 200
    m.chay(s.url)
    assert sorted(s.da_co) == ["msg_A"]


@_ca
def test_hai_process_chay_chong_khong_gui_doi(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant(f"msg_{i}") for i in range(300)])
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env.update({"HOME": str(m.home), "USERPROFILE": str(m.home), "CLAUDE_PLUGIN_DATA": str(m.data),
                "APP_THEU_DEM_URL": s.url, "APP_THEU_DEM_TU": "2026-11-01", "APP_THEU_DEM_DONG_BO": "1",
                "CLAUDE_PLUGIN_OPTION_KHOA_CLAUDE": KHOA, "APP_THEU_DEM_URL_USAGE": s.url_usage})
    ps = [subprocess.Popen([sys.executable, str(SCRIPT)], stdin=subprocess.DEVNULL, env=env) for _ in range(4)]
    for p in ps:
        assert p.wait(timeout=60) == 0
    ds = _luot_gui(s)
    assert len(ds) == 300 and len(set(ds)) == 300, len(ds)


@_ca
def test_log_subagent_duoc_dem_va_danh_dau(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    m.ghi("ses-1/subagents/agent-abc.jsonl", [_dong_assistant("msg_SUB", sidechain=True)])
    m.chay(s.url)
    ds = {l["ma_tin"]: l for l in s.luot()}
    assert ds["msg_SUB"]["la_subagent"] is True and ds["msg_A"]["la_subagent"] is False


@_ca
def test_thu_muc_du_an_kieu_windows_va_ten_la(m, s):
    """Windows: Claude đặt tên thư mục dự án kiểu `C--Users-bach-Ứng dụng`; cấu hình ở CLAUDE_CONFIG_DIR."""
    cfg = m.goc / "cfg claude Ứng"
    p = cfg / "projects" / "C--Users-bach-Ứng dụng thêu" / "ses-9.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(_dong_assistant("msg_W")) + "\r\n", encoding="utf-8")  # xuống dòng CRLF
    (cfg / ".claude.json").write_text(json.dumps({"oauthAccount": {"emailAddress": "tkwin@gmail.com"}}))
    m.chay(s.url, them_env={"CLAUDE_CONFIG_DIR": str(cfg)})
    p.open("a", encoding="utf-8").write(json.dumps(_dong_assistant("msg_W2")) + "\r\n")
    m.chay(s.url, them_env={"CLAUDE_CONFIG_DIR": str(cfg)})
    assert _luot_gui(s) == ["msg_W", "msg_W2"]
    assert s.nhan[-1]["json"]["email_tk"] == "tkwin@gmail.com"


@_ca
def test_email_doi_giua_hai_lo_moi_lo_dung_email_luc_do(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_0")])
    m.chay(s.url)                                   # lần đầu = đếm bù
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    m.chay(s.url)
    m.dat_email("tk2@gmail.com")
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_B")])
    m.chay(s.url)
    theo = {l["ma_tin"]: r["json"]["email_tk"] for r in s.nhan if r["json"] for l in r["json"]["luot"]}
    assert theo == {"msg_0": "", "msg_A": "tk1@gmail.com", "msg_B": "tk2@gmail.com"}


@_ca
def test_lan_dau_chi_bu_tu_moc_va_mang_co_khong_ro_tai_khoan(m, s):
    m.ghi("cu.jsonl", [_dong_assistant("msg_CU", luc="2026-10-31T16:59:59.000Z"),   # 23:59:59 31/10 giờ VN
                       _dong_assistant("msg_MOC", luc="2026-10-31T17:00:00.000Z")])  # 00:00 01/11 giờ VN
    m.chay(s.url)
    assert _luot_gui(s) == ["msg_MOC"]
    assert s.nhan[0]["json"]["email_tk"] == ""
    m.ghi("cu.jsonl", [_dong_assistant("msg_SAU_CU", luc="2026-10-30T00:00:00.000Z")])  # sau lần đầu: không lọc mốc
    m.chay(s.url)
    assert _luot_gui(s) == ["msg_MOC", "msg_SAU_CU"]


# ============================================================ ca — ticket 05 (phía máy: % tài khoản)
@_ca
def test_do_pt_tai_khoan_gui_ket_qua_khong_gui_token(m, s):
    m.dat_token()
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    m.chay(s.url)
    assert len(s.hoi_usage) == 1
    assert s.hoi_usage[0].get("Authorization") == f"Bearer {TOKEN}"
    tat_ca = b"".join(r["raw"] for r in s.nhan) + json.dumps([r["headers"] for r in s.nhan]).encode()
    for bi_mat in (TOKEN, "REFRESH_", "uuid-bi-mat", "TOKEN_BI_MAT"):
        assert bi_mat.encode() not in tat_ca, bi_mat
    tk = s.nhan[-1]["json"]["tai_khoan"]
    assert tk["email"] == "tk1@gmail.com" and tk["subscription_created_at"] == "2026-05-12T03:04:05.000Z"
    do = tk["do"]
    assert do["trang_thai"] == "ok" and do["ly_do"] is None and do["luc"].endswith("Z")
    assert (do["pt_5h"], do["reset_5h"], do["pt_tuan"], do["reset_tuan"]) == (
        12.0, "2026-11-03T08:00:00+00:00", 53.0, "2026-11-04T06:00:00.818775+00:00")
    assert set(tk) == {"email", "subscription_created_at", "do"}


@_ca
def test_do_gian_cach_10_phut(m, s):
    m.dat_token()
    for i in range(3):
        m.ghi("ses-1.jsonl", [_dong_assistant(f"msg_{i}")])
        m.chay(s.url)
    assert len(s.hoi_usage) == 1
    assert "do" in s.nhan[0]["json"]["tai_khoan"] and "do" not in s.nhan[-1]["json"]["tai_khoan"]


@_ca
def test_do_khong_co_luot_moi_van_gui_ket_qua(m, s):
    m.dat_token()
    m.chay(s.url)
    assert s.nhan and s.nhan[-1]["json"]["luot"] == [] and s.nhan[-1]["json"]["tai_khoan"]["do"]["trang_thai"] == "ok"


@_ca
def test_do_hong_bao_khong_lay_duoc_khong_so_doan(m, s):
    m.dat_token()
    s.usage_ma = 401
    m.chay(s.url)
    do = s.nhan[-1]["json"]["tai_khoan"]["do"]
    assert do["trang_thai"] == "khong_lay_duoc" and do["ly_do"] == "HTTP 401"
    assert do["pt_tuan"] is None and do["pt_5h"] is None


@_ca
def test_do_shape_la_bao_khong_lay_duoc(m, s):
    m.dat_token()
    s.usage_tra = {"seven_day": {"utilization": "53%"}}
    m.chay(s.url)
    do = s.nhan[-1]["json"]["tai_khoan"]["do"]
    assert do["trang_thai"] == "khong_lay_duoc" and do["pt_tuan"] is None


@_ca
def test_token_het_han_khong_goi_khong_tu_lam_moi(m, s):
    m.dat_token(het_han_ms=int((time.time() - 60) * 1000))
    m.chay(s.url)
    assert s.hoi_usage == []
    do = s.nhan[-1]["json"]["tai_khoan"]["do"]
    assert do["trang_thai"] == "khong_lay_duoc" and "hết hạn" in do["ly_do"]


@_ca
def test_khong_co_token_van_gui_luot(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    m.chay(s.url)
    assert _luot_gui(s) == ["msg_A"]
    assert s.nhan[-1]["json"]["tai_khoan"]["do"]["trang_thai"] == "khong_lay_duoc"


# ============================================================ ca — ticket 07 (prompt cài đọc trạng thái)
@_ca
def test_trang_thai_sau_khi_hook_gui_duoc(m, s):
    r = m.chay(s.url, args=("--trang-thai",))
    assert r.returncode == 1 and "chưa chạy lần nào" in r.stdout
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    m.chay(s.url)
    r = m.chay(s.url, args=("--trang-thai",))
    assert r.returncode == 0, r.stdout
    assert "✅" in r.stdout and "lần gửi được cuối" in r.stdout and "còn 0 lô chờ" in r.stdout
    assert KHOA not in r.stdout


@_ca
def test_trang_thai_bao_loi_va_lo_cho(m, s):
    m.ghi("ses-1.jsonl", [_dong_assistant("msg_A")])
    s.ma_tra = 401
    m.chay(s.url)
    r = m.chay(s.url, args=("--trang-thai",))
    assert r.returncode == 1 and "còn 1 lô chờ" in r.stdout and "HTTP 401" in r.stdout, r.stdout


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
