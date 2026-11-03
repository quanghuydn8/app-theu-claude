# -*- coding: utf-8 -*-
"""Bộ đếm Claude — hook Stop/SubagentStop của plugin app-theu.

Sau mỗi lượt Claude trả lời, đọc PHẦN MỚI của log Claude Code trên máy này và gửi CON SỐ dùng
(token theo loại, model, giờ) về App Thêu bằng khoá Claude của máy (`userConfig.khoa_claude`,
Claude Code xuất ra env `CLAUDE_PLUGIN_OPTION_KHOA_CLAUDE`).

RIÊNG TƯ — luật cứng của file này:
  * Chỉ gửi các trường trong danh sách trắng `_trich_luot` — KHÔNG BAO GIỜ gửi nội dung chat,
    `cwd`, đường dẫn, tên dự án, tên file.
  * Token đăng nhập Claude của máy KHÔNG BAO GIỜ nằm trong dữ liệu gửi đi.

KHÔNG CHẶN CLAUDE CODE — luật cứng thứ hai:
  * Process hook tách một process con chạy nền rồi thoát ngay, mã 0, không in gì.
  * Mọi lỗi nuốt vào nhật ký cục bộ (`nhat_ky.log` trong thư mục dữ liệu plugin).
  * Không bao giờ thoát mã 2 (mã 2 ở hook Stop = bắt Claude chạy tiếp).

Chỉ dùng thư viện chuẩn Python 3 — chạy y nhau trên Windows / macOS / Linux.

Chế độ:
  (không tham số)  hook — tách nền rồi thoát (APP_THEU_DEM_DONG_BO=1: chạy luôn, cho test)
  --chay           process nền: quét log + gửi
  --thu            chạy luôn và IN kết quả (cần env khoá — dùng khi phát triển)
  --trang-thai     prompt cài đọc: hook đã chạy/gửi được chưa, còn bao nhiêu lô chờ (không cần khoá)
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

PHIEN_BAN_SCRIPT = "1"
URL_MAC_DINH = "https://app.lanhcanh.com/api/v2/dem-claude/lo"
# Đường NỘI BỘ của Anthropic (Claude Code dùng cho /usage) — có thể đổi bất kỳ lúc nào ⇒ hỏng
# thì báo "không lấy được", tuyệt đối không đoán số.
URL_USAGE_MAC_DINH = "https://api.anthropic.com/api/oauth/usage"
GIAN_CACH_DO_GIAY = 600             # mỗi máy hỏi % tài khoản tối đa 10 phút một lần
KEYCHAIN_MAC = "Claude Code-credentials"
MOC_BU_MAC_DINH = "2026-11-01"      # lần chạy đầu: đếm bù log từ ngày này (giờ VN)
LO_TOI_DA = 500                     # lượt mỗi request (máy chủ nhận tối đa 1000)
HANG_DOI_TOI_DA = 400               # số lô chờ gửi giữ lại tối đa (~200k lượt)
KHOA_CHAY_CU_GIAY = 600             # khoá chạy cũ hơn mức này coi như process chết để lại
CHO_KHOA_GIAY = 30
NHAT_KY_TOI_DA = 256 * 1024
_VN = _dt.timezone(_dt.timedelta(hours=7))


# ------------------------------------------------------------------ đường dẫn
def _thu_muc_claude() -> pathlib.Path:
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    return pathlib.Path(cfg) if cfg else pathlib.Path.home() / ".claude"


def _file_cau_hinh_claude() -> pathlib.Path:
    cfg = os.environ.get("CLAUDE_CONFIG_DIR")
    return pathlib.Path(cfg) / ".claude.json" if cfg else pathlib.Path.home() / ".claude.json"


def _thu_muc_du_lieu() -> pathlib.Path:
    d = os.environ.get("CLAUDE_PLUGIN_DATA")
    p = pathlib.Path(d) if d else _thu_muc_claude() / "plugins" / "data" / "app-theu-app-theu-claude"
    return p / "dem_claude"


# ------------------------------------------------------------------ nhật ký cục bộ
def _ghi_nhat_ky(dl: pathlib.Path | None, chu: str) -> None:
    try:
        if dl is None:
            return
        dl.mkdir(parents=True, exist_ok=True)
        p = dl / "nhat_ky.log"
        if p.exists() and p.stat().st_size > NHAT_KY_TOI_DA:
            os.replace(p, dl / "nhat_ky.cu.log")
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{_dt.datetime.now(_VN).isoformat(timespec='seconds')} {chu}\n")
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ file trạng thái (ghi nguyên tử)
def _doc_json(p: pathlib.Path, mac_dinh):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return mac_dinh


def _ghi_json(p: pathlib.Path, du_lieu) -> None:
    tam = p.with_name(p.name + ".tam")
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False)
    os.replace(tam, p)


# ------------------------------------------------------------------ khoá chạy (chống chạy chồng)
class _KhoaChay:
    def __init__(self, dl: pathlib.Path):
        self.p = dl / "dang_chay.lock"
        self.co = False

    def __enter__(self):
        han = time.monotonic() + CHO_KHOA_GIAY
        while True:
            try:
                fd = os.open(self.p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                self.co = True
                return self
            except FileExistsError:
                try:
                    if time.time() - self.p.stat().st_mtime > KHOA_CHAY_CU_GIAY:
                        self.p.unlink()
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= han:
                    return self  # process khác đang chạy lâu — lần sau quét tiếp
                time.sleep(0.3)

    def __exit__(self, *a):
        if self.co:
            try:
                self.p.unlink()
            except FileNotFoundError:
                pass


# ------------------------------------------------------------------ trích con số (DANH SÁCH TRẮNG)
def _so(v) -> int:
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else 0


def _trich_luot(d: dict, *, la_subagent: bool) -> dict | None:
    """Một dòng log → một lượt CHỈ gồm trường danh sách trắng, hoặc None (không phải lượt có usage)."""
    if not isinstance(d, dict) or d.get("type") != "assistant":
        return None
    m = d.get("message")
    if not isinstance(m, dict):
        return None
    u = m.get("usage")
    ma, model, luc = m.get("id"), m.get("model"), d.get("timestamp")
    if not (isinstance(u, dict) and isinstance(ma, str) and ma and isinstance(model, str)
            and isinstance(luc, str)):
        return None
    if model.startswith("<"):  # "<synthetic>" — tin Claude Code tự sinh, không gọi API
        return None
    cc = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else None
    if cc is not None:
        c5, c1 = _so(cc.get("ephemeral_5m_input_tokens")), _so(cc.get("ephemeral_1h_input_tokens"))
    else:
        c5, c1 = _so(u.get("cache_creation_input_tokens")), 0
    stu = u.get("server_tool_use") if isinstance(u.get("server_tool_use"), dict) else {}

    def _chuoi(v):
        return v if isinstance(v, str) else None

    return {
        "ma_tin": ma,
        "request_id": _chuoi(d.get("requestId")),
        "session_id": _chuoi(d.get("sessionId")),
        "luc": luc,
        "model": model,
        "entrypoint": _chuoi(d.get("entrypoint")),
        "phien_ban": _chuoi(d.get("version")),
        "la_subagent": bool(la_subagent or d.get("isSidechain") is True),
        "usage": {
            "input_tokens": _so(u.get("input_tokens")),
            "cache_creation_5m": c5,
            "cache_creation_1h": c1,
            "cache_read_input_tokens": _so(u.get("cache_read_input_tokens")),
            "output_tokens": _so(u.get("output_tokens")),
            "web_search_requests": _so(stu.get("web_search_requests")),
            "web_fetch_requests": _so(stu.get("web_fetch_requests")),
        },
    }


def _moc_bu() -> _dt.datetime:
    s = os.environ.get("APP_THEU_DEM_TU") or MOC_BU_MAC_DINH
    d = _dt.date.fromisoformat(s)
    return _dt.datetime(d.year, d.month, d.day, tzinfo=_VN)


def _sau_moc(luc: str, moc: _dt.datetime) -> bool:
    try:
        t = _dt.datetime.fromisoformat(luc.replace("Z", "+00:00"))
        return t.tzinfo is not None and t >= moc
    except ValueError:
        return False


# ------------------------------------------------------------------ quét log
def _dau_file(f, pos: int) -> str:
    """Vân tay đoạn đầu file (tối đa 4 KB, không quá `pos`) — nhận ra file bị ghi lại."""
    f.seek(0)
    return hashlib.sha256(f.read(min(pos, 4096))).hexdigest()[:16]


def _quet(tt: dict, *, lan_dau: bool) -> list[dict]:
    """Đọc phần mới của mọi file log, cập nhật `tt["vi_tri"]` tại chỗ. Trả các lượt mới."""
    goc = _thu_muc_claude() / "projects"
    vi_tri: dict = tt.setdefault("vi_tri", {})
    moc = _moc_bu() if lan_dau else None
    ra: list[dict] = []
    if not goc.is_dir():
        return ra
    for p in sorted(goc.rglob("*.jsonl")):
        try:
            khoa = p.relative_to(goc).as_posix()
            co = p.stat().st_size
            cu = vi_tri.get(khoa) or {}
            pos = cu.get("pos", 0) if isinstance(cu, dict) else 0
            if not isinstance(pos, int) or pos > co:
                pos = 0  # file bị cắt ⇒ đọc lại từ đầu, máy chủ lọc trùng
            la_sub = "subagents" in p.relative_to(goc).parts
            with open(p, "rb") as f:
                if pos and _dau_file(f, pos) != cu.get("dau"):
                    pos = 0  # file bị GHI LẠI (cùng/lớn hơn cỡ cũ) ⇒ đọc lại từ đầu
                if pos == co:
                    continue
                f.seek(pos)
                du_lieu = f.read()
            het = du_lieu.rfind(b"\n")
            if het < 0:
                continue  # chưa có dòng nào trọn — Claude đang ghi dở
            for dong in du_lieu[: het + 1].splitlines():
                try:
                    d = json.loads(dong)
                except Exception:  # noqa: BLE001
                    continue
                l = _trich_luot(d, la_subagent=la_sub)
                if l is None or (moc is not None and not _sau_moc(l["luc"], moc)):
                    continue
                ra.append(l)
            moi = pos + het + 1
            with open(p, "rb") as f:
                vi_tri[khoa] = {"pos": moi, "dau": _dau_file(f, moi)}
        except OSError:
            continue
    return ra



# ------------------------------------------------------------------ % giới hạn tài khoản (ticket 05)
def _doc_oauth() -> dict | None:
    """Khối `claudeAiOauth` của Claude Code trên máy này. Token CHỈ dùng tại máy để hỏi Anthropic —
    không bao giờ ghi ra file, nhật ký hay dữ liệu gửi App Thêu. Không bao giờ tự làm mới token
    (làm mới xoay refresh-token ⇒ có thể đăng xuất Claude Code của máy)."""
    if sys.platform == "darwin" and not os.environ.get("CLAUDE_CONFIG_DIR"):
        try:
            r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_MAC, "-w"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                d = json.loads(r.stdout)
                if isinstance(d, dict) and isinstance(d.get("claudeAiOauth"), dict):
                    return d["claudeAiOauth"]
        except Exception:  # noqa: BLE001
            pass
    d = _doc_json(_thu_muc_claude() / ".credentials.json", {})
    o = d.get("claudeAiOauth") if isinstance(d, dict) else None
    return o if isinstance(o, dict) else None


def _cua_so(o) -> tuple[float | None, str | None] | None:
    """Một khối `five_hour`/`seven_day`: (utilization, resets_at). `None` khối ⇒ (None, None).
    Sai kiểu ⇒ trả None (= shape lạ)."""
    if o is None:
        return None, None
    if not isinstance(o, dict):
        return None
    u, r = o.get("utilization"), o.get("resets_at")
    if isinstance(u, bool) or not isinstance(u, (int, float)) or not isinstance(r, str):
        return None
    return float(u), r


def _do_tai_khoan() -> dict:
    luc = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    hong = {"trang_thai": "khong_lay_duoc", "luc": luc, "pt_5h": None, "reset_5h": None,
            "pt_tuan": None, "reset_tuan": None}
    o = _doc_oauth()
    tok = o.get("accessToken") if o else None
    if not isinstance(tok, str) or not tok:
        return {**hong, "ly_do": "không đọc được đăng nhập Claude của máy"}
    het = o.get("expiresAt")
    if isinstance(het, (int, float)) and het / 1000 <= time.time():
        return {**hong, "ly_do": "token đăng nhập đã hết hạn"}
    req = urllib.request.Request(os.environ.get("APP_THEU_DEM_URL_USAGE") or URL_USAGE_MAC_DINH, headers={
        "Authorization": f"Bearer {tok}", "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": f"app-theu-dem-claude/{PHIEN_BAN_SCRIPT}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return {**hong, "ly_do": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {**hong, "ly_do": f"không nối được ({type(e).__name__})"}
    if not isinstance(d, dict):
        return {**hong, "ly_do": "shape lạ"}
    c5, c7 = _cua_so(d.get("five_hour")), _cua_so(d.get("seven_day"))
    if c5 is None or c7 is None or c7[0] is None:
        return {**hong, "ly_do": "shape lạ"}
    return {"trang_thai": "ok", "luc": luc, "pt_5h": c5[0], "reset_5h": c5[1],
            "pt_tuan": c7[0], "reset_tuan": c7[1], "ly_do": None}


def _thong_tin_tk() -> dict | None:
    cfg = _doc_json(_file_cau_hinh_claude(), {})
    acc = cfg.get("oauthAccount") if isinstance(cfg, dict) else None
    if not isinstance(acc, dict):
        return None
    e, sub = acc.get("emailAddress"), acc.get("subscriptionCreatedAt")
    if not (isinstance(e, str) and e):
        return None
    return {"email": e, "subscription_created_at": sub if isinstance(sub, str) else None}


# ------------------------------------------------------------------ hàng đợi gửi bù
def _xep_hang(dl: pathlib.Path, luot: list[dict], *, email: str | None, tk: dict | None,
              do: dict | None) -> None:
    hd = dl / "cho_gui"
    hd.mkdir(parents=True, exist_ok=True)
    goc = f"{time.time_ns():020d}"
    for so, i in enumerate(range(0, max(len(luot), 1), LO_TOI_DA)):
        lo: dict = {"email_tk": email or "", "luot": luot[i:i + LO_TOI_DA]}
        if tk:
            lo["tai_khoan"] = {**tk, **({"do": do} if do and so == 0 else {})}
        _ghi_json(hd / f"{goc}_{so:05d}.json", lo)
    ds = sorted(hd.glob("*.json"))
    for p in ds[: max(0, len(ds) - HANG_DOI_TOI_DA)]:  # trần: bỏ lô CŨ nhất
        p.unlink(missing_ok=True)
        _ghi_nhat_ky(dl, f"hàng đợi đầy — bỏ lô cũ {p.name}")


def _gui_hang(dl: pathlib.Path, khoa: str) -> dict:
    url = os.environ.get("APP_THEU_DEM_URL") or URL_MAC_DINH
    kq = {"lo_gui": 0, "moi": 0, "trung": 0, "loai": 0, "con_cho": 0, "loi": None}
    ds = sorted((dl / "cho_gui").glob("*.json")) if (dl / "cho_gui").is_dir() else []
    for i, p in enumerate(ds):
        lo = _doc_json(p, None)
        if not isinstance(lo, dict):
            p.unlink(missing_ok=True)
            continue
        than = json.dumps({**lo, "phien_ban_script": PHIEN_BAN_SCRIPT}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=than, method="POST", headers={
            "Authorization": f"Bearer {khoa}", "Content-Type": "application/json",
            "User-Agent": f"app-theu-dem-claude/{PHIEN_BAN_SCRIPT}"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                tra = json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            kq["loi"] = f"HTTP {e.code}" + (" — khoá Claude sai hoặc đã thu hồi" if e.code == 401 else "")
            kq["con_cho"] = len(ds) - i
            return kq
        except Exception as e:  # noqa: BLE001
            kq["loi"] = f"không nối được máy chủ ({type(e).__name__})"
            kq["con_cho"] = len(ds) - i
            return kq
        p.unlink(missing_ok=True)
        kq["lo_gui"] += 1
        for k in ("moi", "trung", "loai"):
            v = tra.get(k) if isinstance(tra, dict) else 0
            kq[k] += v if isinstance(v, int) else 0
    return kq


# ------------------------------------------------------------------ một lượt chạy
def chay_mot_luot() -> dict:
    khoa = (os.environ.get("CLAUDE_PLUGIN_OPTION_KHOA_CLAUDE") or "").strip()
    dl = _thu_muc_du_lieu()
    if not khoa:
        return {"loi": "chưa nhập khoá Claude cho plugin app-theu"}
    dl.mkdir(parents=True, exist_ok=True)
    with _KhoaChay(dl) as kc:
        if not kc.co:
            return {"loi": "một lượt khác đang chạy"}
        p_tt = dl / "trang_thai.json"
        tt = _doc_json(p_tt, {})
        if not isinstance(tt, dict):
            tt = {}
        lan_dau = not tt.get("da_khoi_tao")
        # Một tin = nhiều dòng log cùng message.id + cùng usage ⇒ gửi một lần (giữ bản gặp đầu).
        da_gap: set = set()
        luot = [l for l in _quet(tt, lan_dau=lan_dau)
                if not (l["ma_tin"] in da_gap or da_gap.add(l["ma_tin"]))]
        tk = _thong_tin_tk()
        # Lượt đếm bù lần đầu: không biết lúc đó máy đăng nhập tài khoản nào ⇒ email rỗng.
        email = None if lan_dau else (tk or {}).get("email")
        do = None
        if tk and time.time() - float(tt.get("do_cuoi") or 0) >= GIAN_CACH_DO_GIAY:
            tt["do_cuoi"] = time.time()  # ghi cả khi hỏng — không dồn dập hỏi lại
            do = _do_tai_khoan()
        if luot or do:
            _xep_hang(dl, luot, email=email, tk=tk, do=do)
        tt["da_khoi_tao"] = True
        _ghi_json(p_tt, tt)  # vị trí chỉ lưu SAU khi lượt đã nằm an toàn trong hàng đợi
        kq = _gui_hang(dl, khoa)
        kq["quet"] = len(luot)
        bay_gio = _dt.datetime.now(_VN).isoformat(timespec="seconds")
        tt["lan_chay_cuoi"] = bay_gio
        tt["loi_cuoi"] = kq.get("loi")
        if not kq.get("loi"):
            tt["gui_ok_luc"] = bay_gio
        _ghi_json(p_tt, tt)
        if kq.get("loi"):
            _ghi_nhat_ky(dl, f"gửi chưa được: {kq['loi']} (còn {kq['con_cho']} lô chờ)")
        return kq


def trang_thai() -> tuple[bool, str]:
    """Cho prompt cài đọc: hook đã chạy chưa, gửi được không, còn bao nhiêu lô chờ. Không cần khoá."""
    dl = _thu_muc_du_lieu()
    tt = _doc_json(dl / "trang_thai.json", {})
    if not isinstance(tt, dict) or not tt.get("da_khoi_tao"):
        return False, ("❌ Bộ đếm Claude: chưa chạy lần nào trên máy này — khởi động lại Claude Code "
                       "(Developer: Reload Window) rồi nhắn Claude một câu bất kỳ, chờ ~30 giây rồi kiểm lại.")
    cho = len(list((dl / "cho_gui").glob("*.json"))) if (dl / "cho_gui").is_dir() else 0
    if tt.get("loi_cuoi"):
        return False, (f"❌ Bộ đếm Claude: lần chạy cuối {tt.get('lan_chay_cuoi')} chưa gửi được — "
                       f"{tt['loi_cuoi']}; còn {cho} lô chờ (sẽ tự gửi bù).")
    return True, (f"✅ Bộ đếm Claude chạy được: lần gửi được cuối {tt.get('gui_ok_luc')}, còn {cho} lô chờ.")


def _tach_nen() -> None:
    kw: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                "close_fds": True}
    if os.name == "nt":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW — không bật cửa sổ console
        kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kw["start_new_session"] = True
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--chay"], **kw)


def main(argv: list[str]) -> int:
    che_do = argv[1] if len(argv) > 1 else ""
    if che_do == "--trang-thai":
        ok, chu = trang_thai()
        print(chu)
        return 0 if ok else 1
    if che_do == "--thu":
        kq = chay_mot_luot()
        if kq.get("loi"):
            print(f"❌ Bộ đếm Claude: {kq['loi']}")
            return 1
        print(f"✅ Bộ đếm Claude: đã gửi {kq['lo_gui']} lô — {kq['moi']} lượt mới, {kq['trung']} trùng"
              f" (quét được {kq['quet']} lượt).")
        return 0
    dl = None
    try:
        dl = _thu_muc_du_lieu()
        if che_do == "--chay" or os.environ.get("APP_THEU_DEM_DONG_BO") == "1":
            chay_mot_luot()
        else:
            try:
                sys.stdin.read()  # hook: nuốt stdin (có nội dung chat) — không dùng tới
            except Exception:  # noqa: BLE001
                pass
            _tach_nen()
    except BaseException as e:  # noqa: BLE001
        _ghi_nhat_ky(dl, f"lỗi: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    try:
        code = main(sys.argv)
    except BaseException:  # noqa: BLE001
        code = 0
    sys.exit(code)
