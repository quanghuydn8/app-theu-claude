---
name: app-theu
description: Dùng khi người dùng muốn xem hoặc thao tác trên App Thêu — cụm Lên kệ Etsy/Shopify (mã sản phẩm, mục lịch đăng, nạp file bàn giao, content, giá, giờ đăng, cờ duyệt, ảnh/video, đẩy cập nhật lên sàn, gỡ mã) hoặc prompt AI / luật xưởng.
---

# Làm việc với App Thêu qua cổng MCP `app-theu`

Bạn đang thao tác trên hệ thống thật của xưởng, bằng khoá cá nhân của người dùng. Mọi lệnh
đều được ghi nhật ký kèm tên họ. Quyền của bạn **đúng bằng** quyền của người dùng đó
(admin hoặc sale) — bị từ chối `403` nghĩa là việc đó vai này không làm được, đừng thử
đường vòng.

## Luật nền

1. **App là bản chuẩn.** Mọi sửa đổi nội dung listing (tiêu đề, mô tả, tag, giá, ảnh…) làm
   trên app rồi đẩy lên sàn. Sửa thẳng trên Etsy/Shopify sẽ bị đè ở lần đẩy sau — nếu người
   dùng kể họ vừa sửa trên sàn, nhắc họ sửa lại trên app.
2. **Người sửa là người duyệt.** Sửa content (không rỗng) hoặc sửa giờ đăng ⇒ cờ tương ứng
   tự "đã duyệt" với tên người dùng. Mục đủ 4 cờ và có giờ sẽ được **máy tự tạo nháp và đăng
   đúng giờ** — nên sửa giờ = cho phép đăng. Nói rõ điều này khi người dùng nhờ đổi giờ.
3. **Lịch nạp từ file luôn "chưa duyệt".** Phải có người bấm duyệt lịch (`duyet_co` /
   `duyet_co_hang_loat`, cờ lịch) thì máy mới đăng.
4. **Không đoán mã shop.** Mã shop (kênh) phải lấy từ dữ liệu app (`tim_muc`, `chi_tiet_ma`)
   hoặc người dùng nói rõ. Không tự bịa, không suy từ tên cửa hàng.
5. **Bạn không có quyền với kết nối shop và key API.** Không có công cụ nào cho việc đó —
   người dùng cần thì chỉ họ vào màn Kết nối shop trên app (chỉ admin).
6. Lỗi trả về dạng `<mã>: <lý do>` — đọc lý do và báo lại bằng lời thường. `409` thường là
   "người khác vừa sửa" ⇒ đọc lại rồi làm tiếp; `429` là chạm giới hạn tốc độ ⇒ chờ.

## Việc PHẢI hỏi lại người dùng trước khi làm

- Mọi công cụ `xac_nhan_*` (đẩy cập nhật lên sàn · gỡ mã · huỷ mục · đăng ngay). Luôn gọi
  `xem_truoc_*` trước, **đọc tóm tắt cho người dùng** (bao nhiêu mục, shop nào, phần nào
  đổi), chờ họ đồng ý rõ ràng, rồi mới `xac_nhan_*` với đúng `ma_xac_nhan` và đúng tham số
  đã xem trước. Mã xác nhận hết hạn sau vài phút và chỉ dùng một lần.
- `ghi_luot_nap` (ghi file vào danh mục — không hoàn tác được).
- `xoa_media` (ảnh up tay xoá là mất hẳn).
- Sửa prompt AI / luật xưởng (`sua_prompt_ai`, `kich_hoat_prompt`, `sua_luat_xuong`, các lệnh
  "về mặc định") — ảnh hưởng mọi content AI viết sau đó.
- Sửa giờ hoặc duyệt cờ cho nhiều mục cùng lúc.

## Luồng thường gặp

### Nạp file bàn giao
1. File là Google Sheet ⇒ `nap_bang_sheet(link)`. File trên máy ⇒ `xin_link_upload_nap(ten_file)`
   → PUT file lên `signed_url` (vd `curl -X PUT -H "Content-Type: <content_type>"
   --data-binary @file "<signed_url>"`) → `nap_file_da_upload(path)`.
2. `luot_nap(import_id)` ⇒ đọc `nhom_loi`: khối **chặn** (mã sẽ KHÔNG được ghi) và khối
   **cảnh báo** (vẫn ghi được). Mỗi nhóm có loại lỗi, số mã, danh sách mã kèm lý do; lỗi không
   gắn mã thì theo sheet + khoảng dòng (`5–120, 300`). Tóm tắt cho người dùng theo nhóm,
   không đọc từng dòng.
3. Luật nạp: mỗi mã phải có ít nhất một dòng lịch, và **mọi** dòng phải mang mã shop có thật
   trên app — một dòng sai shop là cả mã bị chặn. Shop đang tắt chỉ bỏ dòng đó (cảnh báo).
   Sửa file là việc của người làm file; đừng đề xuất đoán shop hộ.
4. Người dùng đồng ý ⇒ `ghi_luot_nap(import_id)`. Ảnh/video của các mã có folder Drive tự tải
   về ở nền — theo dõi bằng `tien_do_viec_nen`.

### Xem và sửa một mã
- `tim_ma` / `chi_tiet_ma` / `tim_muc` để tìm. `sua_content(listing_key, channel_code, patch)`,
  `sua_gia(...)` (chỉ admin), `sua_gio_dang(item_id, scheduled_at)` (giờ ISO có múi giờ;
  `scheduled_at=null` để xoá giờ).
- Ảnh/video: `xem_bo_media(listing_key, channel_code)` ⇒ mỗi shop một bộ riêng, ô đầu là ảnh
  đại diện. Sắp lại bằng `sap_media` (gửi TOÀN BỘ id theo thứ tự mới + `phien_ban`). Thêm file
  từ máy: `xin_link_upload_media` → PUT → `them_media_da_upload`. Lấy file mới trên Drive:
  `kiem_tra_lai_drive`.

### Đẩy thay đổi lên sàn
1. `muc_thay_doi` ⇒ các mục đã có listing trên sàn mà app khác bản đã đẩy, kèm phần đổi.
2. `xem_truoc_day_cap_nhat(item_ids)` ⇒ đọc tóm tắt cho người dùng, nhắc "sửa trực tiếp trên
   sàn sẽ bị ghi đè".
3. Đồng ý ⇒ `xac_nhan_day_cap_nhat(...)`. Việc chạy nền — theo dõi bằng `tien_do_viec_nen`;
   mục lỗi có lý do riêng.

## Giới hạn

- Mỗi khoá tối đa 120 lệnh/phút và 20 lượt `xac_nhan_*`/giờ.
- Danh sách dài được cắt — dùng bộ lọc hoặc phân trang thay vì xin tất cả.
