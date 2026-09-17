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

## Lưu ý

- App là bản chuẩn: sửa thẳng trên Etsy/Shopify sẽ bị đè ở lần đẩy sau.
- Sửa giờ đăng = cho phép máy đăng đúng giờ đó (nếu mục đã đủ cờ).
