---
name: app-theu
description: Dùng khi người dùng muốn xem hoặc thao tác trên App Thêu — đơn hàng (tìm đơn, sửa, đổi trạng thái, vận chuyển, bản in, xe ôm), khách hàng, lên kệ Etsy/Shopify (mã, mục lịch, nạp file bàn giao, content, giá, giờ đăng, cờ duyệt, ảnh/video, đẩy cập nhật, gỡ mã), tài chính (lãi lỗ, sổ quỹ, thu chi, khớp giao dịch, ghi thu tay), gen ảnh AI, mạng xã hội (lên lịch bài), quảng cáo Facebook, biên bản họp, prompt AI / luật xưởng.
---

# Làm việc với App Thêu qua cổng MCP `app-theu`

Bạn đang thao tác trên hệ thống thật của xưởng, bằng khoá cá nhân của người dùng. Mọi lệnh
đều được ghi nhật ký kèm tên họ. Quyền của bạn **đúng bằng** quyền của người dùng đó
(admin · sale · kho · kế toán · design) — bị từ chối `403` nghĩa là việc đó vai này không
làm được, đừng thử đường vòng.

Cổng phủ các cụm: **đơn hàng · khách hàng · lên kệ Etsy/Shopify · tài chính · gen ảnh AI ·
mạng xã hội · quảng cáo · họp**. Tên công cụ mang tiền tố cụm (`don_*`, `khach_*`,
`tai_chinh_*`, `mxh_*`, `qc_*`, `hop_*`); riêng cụm Lên kệ không có tiền tố (`tim_ma`,
`sua_content`, `duyet_co`…).

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
7. **Đổi trạng thái đơn đi qua luật riêng của từng vai.** Hỏi `don_trang_thai_hop_le` trước
   khi định đổi, đừng thử rồi ăn 403. Đơn đã thu tiền không lùi về "Mới" được; đơn Lẻ/File
   phải có cọc mới xác nhận được — công cụ xem trước sẽ nói rõ đơn nào bị bỏ qua và vì sao.
8. **Mạng xã hội CHỈ lên lịch, không bao giờ đăng ngay.** Không có công cụ đăng ngay, và giờ
   đăng phải cách hiện tại ít nhất 15 phút — để người dùng luôn còn kịp huỷ.
9. **Tiền là việc phải hỏi lại, không có ngoại lệ.** Mọi thao tác ghi của cụm Tài chính (kể
   cả sửa một phiếu hay gỡ khớp) đều đi hai bước.
10. **Bạn không bao giờ thấy key.** Danh sách tài khoản quảng cáo chỉ cho biết "đã khai key
   hay chưa", không cho giá trị. Đừng xin, đừng đoán.

## Việc PHẢI hỏi lại người dùng trước khi làm

- **Mọi công cụ `xac_nhan_*`**, ở mọi cụm: ra sàn (đẩy cập nhật · gỡ mã · huỷ mục · đăng
  ngay · thử lại · sửa draft) · tiền (thu chi · chi phí · khớp · ghi thu tay · xe ôm · tính
  lại tổng chi tiêu) · vận chuyển (đẩy đơn · huỷ vận đơn) · gen AI (viết content · vẽ ảnh ·
  AutoGen · AI Batch · eval prompt) · mạng xã hội (lên lịch · dời lịch) · đơn hàng (đổi
  trạng thái hàng loạt). Luôn gọi
  `xem_truoc_*` trước, **đọc tóm tắt cho người dùng** (bao nhiêu mục, shop nào, phần nào
  đổi), chờ họ đồng ý rõ ràng, rồi mới `xac_nhan_*` với đúng `ma_xac_nhan` và đúng tham số
  đã xem trước. Mã xác nhận hết hạn sau vài phút và chỉ dùng một lần.
- `ghi_luot_nap` (ghi file vào danh mục — không hoàn tác được).
- `xoa_media` (ảnh up tay xoá là mất hẳn).
- Sửa prompt AI / luật xưởng (`sua_prompt_ai`, `kich_hoat_prompt`, `sua_luat_xuong`, các lệnh
  "về mặc định") — ảnh hưởng mọi content AI viết sau đó.
- Sửa giờ hoặc duyệt cờ cho nhiều mục cùng lúc.
- Sửa thông tin đơn của khách (địa chỉ, tiền, ngày hẹn) — đọc lại cho người dùng nghe trước.

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

### Đơn hàng
- `don_tim` lọc theo trạng thái · shop · khách · mã đơn · khoảng ngày, có phân trang — đừng
  xin tất cả rồi tự lọc. `don_chi_tiet` cho một đơn kèm món, ảnh, thanh toán, vận chuyển.
- Sửa đơn: `don_sua` (cột thông tin chung). Đổi trạng thái: `don_doi_trang_thai` cho một đơn,
  hoặc `xem_truoc_doi_trang_thai_hang_loat` → hỏi → `xac_nhan_...` cho nhiều đơn.
- Khách dán tin nhắn ⇒ `don_ai_doc_tin_nhan` (chỉ tách dữ liệu, KHÔNG tạo đơn) ⇒ đọc lại cho
  người dùng duyệt ⇒ `don_tao`.
- Ảnh của món: `don_gan_anh(ma_don, item_id, cot, vi_tri, url)` — nó tự giữ mọi cột ảnh cùng
  số vị trí. Đừng ghi thẳng chuỗi ảnh qua `don_sua_mon`.
- Vận chuyển: `don_tinh_phi_ship` / `don_dich_vu_van_chuyen` để xem, rồi
  `xem_truoc_day_van_chuyen` → hỏi → `xac_nhan_...`. Nhãn, bản in, Excel đều trả **link tải**
  sống 15 phút, đưa link cho người dùng chứ không mô tả nội dung file.

### Tài chính
- Đọc: `tai_chinh_lai_lo`, `tai_chinh_so_quy`, `tai_chinh_so_du_vi`, `tai_chinh_chi_phi`,
  `tai_chinh_co_cau_chi_phi`, `tai_chinh_xu_huong_chi_phi`. Chỉ admin và kế toán.
- Ghi: mọi thứ hai bước. Bản xem trước nêu số tiền, ví, phiếu/đơn liên quan và trạng thái
  thanh toán trước → sau — **đọc đủ mấy con số đó cho người dùng** rồi mới xin đồng ý.

### Mạng xã hội
- `mxh_lich_tuan` xem lịch; `mxh_soan_nhap` soạn bài nháp; `mxh_nhan_ban`, `mxh_huy`.
- Lên lịch: `xem_truoc_len_lich` (nêu caption · media · kênh · giờ) → hỏi → `xac_nhan_len_lich`.
  Giờ phải cách hiện tại ≥ 15 phút. Không có đường đăng ngay.

## Giới hạn

- Mỗi khoá tối đa 120 lệnh/phút, và 20 lượt `xac_nhan_*`/giờ **cho mỗi nhóm** (ra sàn ·
  tiền · vận chuyển · gen AI · mạng xã hội · đơn hàng) — nhóm này đầy không chặn nhóm kia.
- Danh sách dài được cắt — dùng bộ lọc hoặc phân trang thay vì xin tất cả.
