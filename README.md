# App Thêu — plugin Claude Code

Plugin này nối **Claude Code** (extension VS Code hoặc terminal) vào App Thêu, để bạn nhờ
Claude tìm mã, đọc lỗi nạp file, sửa content/giá/giờ, sắp ảnh, đẩy cập nhật lên sàn… bằng lời.

Claude dùng **khoá Claude của riêng bạn**, nên chỉ làm được đúng những việc tài khoản của bạn
làm được trên app, và mọi lệnh đều ghi tên bạn.

## 1. Lấy khoá

1. Đăng nhập App Thêu → menu **Kết nối Claude**.
2. Bấm **Tạo khoá**, đặt tên theo máy (vd `Laptop Lan`).
3. Chép khoá (bắt đầu bằng `atk_`) ngay — khoá **chỉ hiện một lần**.

Không gửi khoá cho ai, không dán vào file trong repo hay chat nhóm.

## 2. Cài (hai lệnh)

Trong ô chat Claude Code (VS Code) gõ lần lượt:

```
/plugin marketplace add quanghuydn8/app-theu-claude
/plugin install app-theu@app-theu-claude
```

Claude Code hỏi **Khoá Claude** → dán khoá vừa chép. Khoá được lưu trong kho bí mật của máy.

Khởi động lại phiên Claude Code, rồi thử: *"App thêu hôm nay còn bao nhiêu mã kẹt?"*

<details>
<summary>Cài bằng terminal thay vì ô chat</summary>

```bash
claude plugin marketplace add quanghuydn8/app-theu-claude
claude plugin install app-theu@app-theu-claude
```

Lệnh thứ hai hỏi khoá. Tránh truyền khoá thẳng trên dòng lệnh (`--config`) vì nó nằm lại
trong lịch sử shell.
</details>

### Cài bằng một prompt (máy mới, Windows, Mac)

Trong App Thêu → **Kết nối Claude** có nút **Chép prompt** (cùng nội dung dưới). Dán vào Claude Code của
máy cần cài: Claude tự kiểm và cài phần còn thiếu (Python, Git Bash trên Windows), chỉ chỗ bạn phải gõ
lệnh, rồi kiểm bộ đếm Claude chạy được chưa. Dán lại lần hai sau khi Reload Window.

````
Cài plugin App Thêu (kèm bộ đếm Claude) cho máy này. Làm lần lượt, mỗi bước báo tôi một dòng ngắn. KHÔNG được tự đọc, in ra hay ghi khoá Claude (atk_…) ở bất kỳ đâu.

1. Xem hệ điều hành (Windows / macOS / Linux).
2. Python 3 (cần ≥ 3.8):
   - Windows: chạy `py -3 --version`. Không có thì chạy `winget install -e --id Python.Python.3.12`, rồi kiểm lại bằng `py -3 --version`.
   - macOS: chạy `python3 --version`. Không có thì chạy `xcode-select --install`, bảo tôi bấm Cài trong hộp thoại, chờ xong rồi kiểm lại.
   - Linux: chạy `python3 --version`. Không có thì dừng và bảo tôi cài python3 bằng trình quản lý gói.
3. Riêng Windows: kiểm Git Bash (có file "C:\Program Files\Git\bin\bash.exe" hoặc lệnh `where bash` ra Git). Không có thì chạy `winget install -e --id Git.Git`.
4. Đọc file ~/.claude/plugins/installed_plugins.json (Windows: %USERPROFILE%\.claude\plugins\installed_plugins.json).
   - Nếu CHƯA có "app-theu@app-theu-claude": bảo tôi tự gõ vào ô chat 2 lệnh dưới, dán khoá Claude khi được hỏi, rồi chạy "Developer: Reload Window" và dán lại prompt này:
     /plugin marketplace add quanghuydn8/app-theu-claude
     /plugin install app-theu@app-theu-claude
   - Nếu CÓ nhưng phiên bản thấp hơn 1.1.0: bảo tôi tự gõ "/plugin marketplace update app-theu-claude", rồi "/plugin" → chọn app-theu → cập nhật, rồi Reload Window và dán lại prompt này.
   - Nếu CÓ bản 1.1.0 trở lên: sang bước 5.
5. Kiểm bộ đếm: tìm thư mục bản mới nhất trong ~/.claude/plugins/cache/app-theu-claude/app-theu/ và chạy file scripts/dem_claude.py --trang-thai trong đó (Windows: `py -3 <đường dẫn>\scripts\dem_claude.py --trang-thai`; macOS/Linux: `python3 <đường dẫn>/scripts/dem_claude.py --trang-thai`).
   - Ra "✅": báo tôi "đã cài xong" kèm dòng đó.
   - Ra "chưa chạy lần nào": hook chỉ chạy khi một lượt trả lời KẾT THÚC — bảo tôi nhắn thêm "kiểm lại", rồi ở lượt đó chạy lại đúng lệnh trên một lần.
   - Vẫn "❌": báo nguyên văn dòng lỗi cho tôi, không tự sửa file của plugin.
````

## 3. Cập nhật

```
/plugin marketplace update app-theu-claude
```

## 4. Đổi khoá / mất máy

- **Đổi khoá trên máy này:** `/plugin` → chọn `app-theu` → cấu hình lại, dán khoá mới.
- **Mất máy hoặc lộ khoá:** vào App Thêu → **Kết nối Claude** → **Thu hồi** khoá của máy đó.
  Khoá mất hiệu lực ngay. (Admin thu hồi được khoá của mọi người.)
- **Nghỉ việc / đổi vai:** khoá tự mất hiệu lực khi tài khoản bị khoá hoặc mất vai.

## Claude làm được gì

- **Xem:** tìm mã, mục lịch, tổng quan, lỗi nạp file (gộp theo nhóm), mục có thay đổi chưa
  đẩy, nhật ký gọi sàn, tiến độ việc nền, bộ ảnh/video, prompt AI và luật xưởng.
- **Sửa trên app:** nạp file (link Google Sheet hoặc file trên máy), ghi lượt nạp, sửa
  content, giá, giờ đăng, duyệt cờ, sắp/thêm/xoá ảnh-video, kiểm tra lại Drive, sửa prompt AI
  và luật xưởng (tuỳ vai).
- **Ra sàn** (đẩy cập nhật, gỡ mã, huỷ mục, đăng ngay): luôn **xem trước rồi mới xác nhận**,
  và Claude phải hỏi lại bạn trước khi xác nhận.
- **Không làm được:** kết nối shop, key API sàn.

## Bộ đếm Claude (từ bản 1.1.0)

Sau mỗi lượt Claude trả lời, plugin gửi về App Thêu **con số dùng** của máy này: mã tin, giờ, model,
số token từng loại, phiên bản Claude Code, email tài khoản Claude đang đăng nhập, và % giới hạn tài khoản
(đo tại máy, tối đa 10 phút một lần). App gộp theo người và báo cáo lúc 20:59 vào nhóm Telegram.

- **Không bao giờ gửi:** nội dung chat, mã nguồn, đường dẫn, tên dự án, token đăng nhập Claude.
- Chạy ngầm, không làm chậm Claude. Mất mạng thì để dành, lần sau gửi bù. Lỗi gì cũng không chặn Claude Code.
- Cần Python 3 (Windows: `py`; Mac/Linux: `python3`) và trên Windows cần Git Bash. Prompt cài ở trên tự lo.
- Kiểm trên máy: `python3 <thư mục plugin>/scripts/dem_claude.py --trang-thai`.

## Lưu ý

- App là bản chuẩn: sửa thẳng trên Etsy/Shopify sẽ bị đè ở lần đẩy sau.
- Sửa giờ đăng = cho phép máy đăng đúng giờ đó (nếu mục đã đủ cờ).
