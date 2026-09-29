import streamlit as st
import pandas as pd
import sqlite3
import re
import io
from datetime import date, datetime

# ----------------- CẤU HÌNH TRANG -----------------
st.set_page_config(
    page_title="Hệ Thống Cân Hàng & Tính Tiền Online",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "can_hang_online.db"

# ----------------- KHỞI TẠO DATABASE -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS phieu_can (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ngay TEXT NOT NULL,
            ten_hang TEXT NOT NULL,
            so_bao INTEGER DEFAULT 0,
            danh_sach_can TEXT,
            khoi_luong REAL NOT NULL,
            ti_le_kh REAL NOT NULL,
            khau_hao REAL NOT NULL,
            kl_sau_kh REAL NOT NULL,
            don_gia REAL NOT NULL,
            thanh_tien REAL NOT NULL,
            ghi_chu TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------- TIỆN ÍCH TÍNH TOÁN -----------------
def parse_numbers(raw_text):
    """Trích xuất danh sách số thực/nguyên từ chuỗi nhập vào"""
    if not raw_text:
        return []
    found = re.findall(r"[-+]?\d*\.\d+|\d+", str(raw_text).replace(",", "."))
    nums = []
    for x in found:
        try:
            val = float(x)
            if val > 0:
                nums.append(val)
        except ValueError:
            pass
    return nums

# ----------------- GIAO DIỆN CHÍNH -----------------
st.title("⚖️ Quản Lý Cân Hàng & Tính Tiền")

menu = st.sidebar.radio(
    "📌 Chức năng",
    [
        "📝 Nhập Lượt Cân Mới", 
        "✏️ Sửa & Điều Chỉnh Phiếu", 
        "📅 Sổ Kê Chi Tiết Theo Ngày", 
        "📊 Tổng Hợp & Xuất Excel"
    ]
)

# ================= MENU 1: NHẬP LƯỢT CÂN MỚI =================
if menu == "📝 Nhập Lượt Cân Mới":
    st.subheader("Nhập Thông Tin Lượt Cân Mới")

    col_a, col_b = st.columns([1, 2])
    with col_a:
        ngay_can = st.date_input("Ngày cân", value=date.today())
    with col_b:
        ten_hang = st.text_input("Tên hàng / Đối tác", placeholder="VD: Chị May, Đội 6, Chị Dung...")

    col_c, col_d, col_e = st.columns([2, 1, 1])
    with col_c:
        ghi_chu = st.text_input("Ghi chú (Lô/Xe)", placeholder="VD: Lô 1 (4 tấn), Xe 3...")
    with col_d:
        ti_le_kh = st.number_input("Khấu hao (%)", min_value=0.0, max_value=100.0, value=7.0, step=0.5)
    with col_e:
        don_gia = st.number_input("Đơn giá", min_value=0.0, value=7.0, step=0.1, format="%.2f")

    st.markdown("#### 📦 Danh sách số cân chi tiết (từng bao/két)")
    st.caption("Dán hoặc gõ liên tiếp các số cân, cách nhau bằng dấu cách hoặc xuống dòng (VD: `53 56 53 56 53 54 55 54...`)")
    
    day_so_can = st.text_area("Nhập các số cân:", height=100, placeholder="53 56 53 56 53 54 55 54\n54 36 57 55 52 52 35 55...")

    list_nums = parse_numbers(day_so_can)
    so_bao = len(list_nums)
    tong_kl_tu_dong = sum(list_nums)

    if so_bao > 0:
        st.info(f"👉 **Đã nhận diện:** `{so_bao}` bao | **Tổng cân tự động:** `{tong_kl_tu_dong:,.1f}` kg")
        with st.expander("👁️ Xem trước bảng cân phân bố 8 cột"):
            cols_preview = st.columns(8)
            for idx, n in enumerate(list_nums):
                cols_preview[idx % 8].write(f"**#{idx+1}:** {n:g}")

    # Cho phép điều chỉnh tổng kg nếu không cân lẻ mà cân cả xe
    tong_kl_final = st.number_input(
        "Tổng khối lượng chốt (kg):", 
        min_value=0.0, 
        value=float(tong_kl_tu_dong), 
        step=1.0, 
        format="%.1f"
    )

    if tong_kl_final > 0:
        khau_hao = round(tong_kl_final * (ti_le_kh / 100.0))
        kl_sau_kh = tong_kl_final - khau_hao
        thanh_tien = round(kl_sau_kh * don_gia, 2)
        st.success(
            f"**Tóm tắt:** Trừ hao {ti_le_kh}%: `{khau_hao:,.0f}` kg  |  "
            f"KL sau trừ hao: `{kl_sau_kh:,.1f}` kg  |  "
            f"**Thành tiền: {thanh_tien:,.2f}**"
        )

    if st.button("💾 LƯU PHIẾU CÂN NÀY", type="primary", use_container_width=True):
        if not ten_hang.strip():
            st.error("Vui lòng nhập tên đối tác / tên hàng!")
        elif tong_kl_final <= 0:
            st.error("Tổng khối lượng phải lớn hơn 0!")
        else:
            khau_hao = round(tong_kl_final * (ti_le_kh / 100.0))
            kl_sau_kh = tong_kl_final - khau_hao
            thanh_tien = round(kl_sau_kh * don_gia, 2)
            chuoi_luu = ", ".join(f"{x:g}" for x in list_nums) if list_nums else ""

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                INSERT INTO phieu_can (ngay, ten_hang, so_bao, danh_sach_can, khoi_luong, ti_le_kh, khau_hao, kl_sau_kh, don_gia, thanh_tien, ghi_chu)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ngay_can.strftime("%Y-%m-%d"),
                ten_hang.strip(),
                so_bao,
                chuoi_luu,
                tong_kl_final,
                ti_le_kh,
                khau_hao,
                kl_sau_kh,
                don_gia,
                thanh_tien,
                ghi_chu.strip()
            ))
            conn.commit()
            conn.close()
            st.toast("✅ Đã lưu phiếu cân thành công!", icon="🎉")
            st.rerun()

# ================= MENU 2: SỬA & ĐIỀU CHỈNH PHIẾU CÂN =================
elif menu == "✏️ Sửa & Điều Chỉnh Phiếu":
    st.subheader("Sửa / Điều Chỉnh Toàn Diện Thông Tin Phiếu")

    conn = sqlite3.connect(DB_FILE)
    df_all = pd.read_sql_query("SELECT id, ngay, ten_hang, so_bao, khoi_luong, don_gia, thanh_tien, ghi_chu FROM phieu_can ORDER BY id DESC", conn)
    conn.close()

    if df_all.empty:
        st.info("Chưa có phiếu cân nào trong hệ thống để chỉnh sửa.")
    else:
        # Chọn phiếu muốn sửa
        options_dict = {
            f"Phiếu #{row['id']} - {row['ngay']} - {row['ten_hang']} ({row['khoi_luong']:,.1f} kg)": row['id']
            for _, row in df_all.iterrows()
        }
        selected_label = st.selectbox("👉 Chọn phiếu cân cần sửa đổi:", list(options_dict.keys()))
        selected_id = options_dict[selected_label]

        # Lấy dữ liệu chi tiết của phiếu được chọn
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM phieu_can WHERE id = ?", (selected_id,))
        record = c.fetchone()
        conn.close()

        # record: (id, ngay, ten_hang, so_bao, danh_sach_can, khoi_luong, ti_le_kh, khau_hao, kl_sau_kh, don_gia, thanh_tien, ghi_chu)
        old_id, old_ngay, old_ten, old_sobao, old_ds, old_kl, old_tikh, old_kh, old_saukh, old_gia, old_tien, old_note = record

        try:
            val_date = datetime.strptime(old_ngay, "%Y-%m-%d").date()
        except Exception:
            val_date = date.today()

        with st.form("form_chinh_sua"):
            st.markdown(f"### Đang chỉnh sửa: **Phiếu #{old_id}**")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                edit_ngay = st.date_input("Ngày cân", value=val_date)
            with c2:
                edit_ten = st.text_input("Tên hàng / Đối tác", value=old_ten)

            c3, c4, c5 = st.columns([2, 1, 1])
            with c3:
                edit_ghichu = st.text_input("Ghi chú (Lô/Xe)", value=old_note or "")
            with c4:
                edit_tikh = st.number_input("Tỷ lệ khấu hao (%)", min_value=0.0, max_value=100.0, value=float(old_tikh), step=0.5)
            with c5:
                edit_gia = st.number_input("Đơn giá", min_value=0.0, value=float(old_gia), step=0.1, format="%.2f")

            st.markdown("##### Danh sách số cân chi tiết từng bao (có thể sửa/thêm/xóa từng số):")
            # Hiển thị lại chuỗi cân cũ cách nhau bởi khoảng trắng cho dễ sửa
            old_str_display = old_ds.replace(", ", " ") if old_ds else ""
            edit_ds = st.text_area("Các số cân (cách nhau bởi dấu cách hoặc dòng):", value=old_str_display, height=110)

            # Phân tích chuỗi số mới
            new_list_nums = parse_numbers(edit_ds)
            calc_new_sobao = len(new_list_nums)
            calc_new_kl = sum(new_list_nums)

            if calc_new_sobao > 0:
                st.caption(f"Đã nhận diện: **{calc_new_sobao} bao** | Tổng tính tự động: **{calc_new_kl:,.1f} kg**")
                default_kl_input = float(calc_new_kl)
            else:
                default_kl_input = float(old_kl)

            edit_kl_final = st.number_input("Tổng khối lượng chốt (kg):", min_value=0.0, value=default_kl_input, step=1.0, format="%.1f")

            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                btn_update = st.form_submit_button("💾 LƯU CÁC THAY ĐỔI", type="primary", use_container_width=True)
            with col_btn2:
                btn_cancel = st.form_submit_button("Hủy bỏ", use_container_width=True)

            if btn_update:
                if not edit_ten.strip():
                    st.error("Tên đối tác không được để trống!")
                elif edit_kl_final <= 0:
                    st.error("Tổng khối lượng phải lớn hơn 0!")
                else:
                    new_khau_hao = round(edit_kl_final * (edit_tikh / 100.0))
                    new_kl_sau_kh = edit_kl_final - new_khau_hao
                    new_thanh_tien = round(new_kl_sau_kh * edit_gia, 2)
                    new_chuoi_luu = ", ".join(f"{x:g}" for x in new_list_nums) if new_list_nums else ""

                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute('''
                        UPDATE phieu_can
                        SET ngay = ?, ten_hang = ?, so_bao = ?, danh_sach_can = ?, khoi_luong = ?, 
                            ti_le_kh = ?, khau_hao = ?, kl_sau_kh = ?, don_gia = ?, thanh_tien = ?, ghi_chu = ?
                        WHERE id = ?
                    ''', (
                        edit_ngay.strftime("%Y-%m-%d"),
                        edit_ten.strip(),
                        calc_new_sobao,
                        new_chuoi_luu,
                        edit_kl_final,
                        edit_tikh,
                        new_khau_hao,
                        new_kl_sau_kh,
                        edit_gia,
                        new_thanh_tien,
                        edit_ghichu.strip(),
                        old_id
                    ))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Đã cập nhật thành công Phiếu #{old_id}!")
                    st.rerun()

        # Nút xóa riêng biệt phiếu đang chọn
        st.markdown("---")
        with st.expander("🗑️ XÓA PHIẾU NÀY"):
            st.warning(f"Bạn có chắc chắn muốn xóa vĩnh viễn **Phiếu #{old_id} - {old_ten}** không?")
            if st.button("XÁC NHẬN XÓA PHIẾU NÀY", type="secondary"):
                conn = sqlite3.connect(DB_FILE)
                conn.execute("DELETE FROM phieu_can WHERE id = ?", (old_id,))
                conn.commit()
                conn.close()
                st.toast(f"Đã xóa phiếu #{old_id} thành công!", icon="🗑️")
                st.rerun()

# ================= MENU 3: SỔ KÊ CHI TIẾT THEO NGÀY =================
elif menu == "📅 Sổ Kê Chi Tiết Theo Ngày":
    st.subheader("Tra Cứu Chi Tiết Theo Ngày")
    ngay_tra = st.date_input("Chọn ngày muốn xem:", value=date.today())

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(
        "SELECT id, ngay, ten_hang, so_bao, khoi_luong, khau_hao, kl_sau_kh, don_gia, thanh_tien, ghi_chu, danh_sach_can FROM phieu_can WHERE ngay = ? ORDER BY id ASC",
        conn,
        params=[ngay_tra.strftime("%Y-%m-%d")]
    )
    conn.close()

    if not df.empty:
        t_bao = df["so_bao"].sum()
        t_kl = df["khoi_luong"].sum()
        t_sau_kh = df["kl_sau_kh"].sum()
        t_tien = df["thanh_tien"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng số bao", f"{t_bao:,} bao")
        m2.metric("Tổng khối lượng", f"{t_kl:,.1f} kg")
        m3.metric("KL sau trừ hao", f"{t_sau_kh:,.1f} kg")
        m4.metric("Tổng tiền", f"{t_tien:,.2f}")

        st.markdown("---")
        for _, row in df.iterrows():
            with st.container():
                st.markdown(f"#### 📍 Phiếu #{row['id']}: **{row['ten_hang']}** ({row['ghi_chu'] or 'Không ghi chú'})")
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"- **Số bao:** {row['so_bao']} bao")
                c2.write(f"- **Tổng KL:** {row['khoi_luong']:,.1f} kg")
                c3.write(f"- **Đơn giá:** {row['don_gia']:,.2f}")
                c4.write(f"- **Thành tiền:** `{row['thanh_tien']:,.2f}`")

                if row["danh_sach_can"]:
                    with st.expander(f"🔍 Bảng chi tiết từng bao của phiếu #{row['id']}"):
                        ds = [float(x) for x in row["danh_sach_can"].split(", ")]
                        sub_cols = st.columns(8)
                        for i, val in enumerate(ds):
                            sub_cols[i % 8].caption(f"#{i+1}: **{val:g}**")

                st.divider()
    else:
        st.info("Chưa có lượt cân nào trong ngày được chọn.")

# ================= MENU 4: TỔNG HỢP & XUẤT EXCEL =================
elif menu == "📊 Tổng Hợp & Xuất Excel":
    st.subheader("Bảng Tổng Hợp Toàn Bộ & Xuất File Excel")

    conn = sqlite3.connect(DB_FILE)
    df_all = pd.read_sql_query("SELECT id, ngay, ten_hang, so_bao, khoi_luong, khau_hao, kl_sau_kh, don_gia, thanh_tien, ghi_chu, danh_sach_can FROM phieu_can ORDER BY ngay ASC, id ASC", conn)
    conn.close()

    if not df_all.empty:
        st.dataframe(df_all.drop(columns=["danh_sach_can"]), use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            export_df = df_all.copy()
            export_df.columns = [
                "STT", "Ngày", "Đối tác / Tên hàng", "Số bao", "Tổng KL (kg)", 
                "Khấu hao (kg)", "KL sau K/hao (kg)", "Đơn giá", 
                "Thành tiền", "Ghi chú (Lô/Xe)", "Chi tiết từng bao"
            ]
            export_df.to_excel(writer, index=False, sheet_name="Tong_Hop_Can_Hang")

        st.download_button(
            label="📥 TẢI FILE EXCEL (.XLSX) VỀ MÁY",
            data=buffer.getvalue(),
            file_name=f"Tong_Hop_Can_Hang_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.markdown("---")
        # Chức năng xóa toàn bộ hệ thống (dành cho đầu vụ mới)
        with st.expander("🚨 Vùng nguy hiểm: Xóa toàn bộ dữ liệu"):
            st.error("Thao tác này sẽ xóa sạch tất cả các phiếu cân trong cơ sở dữ liệu. Hãy tải file Excel sao lưu trước khi thực hiện!")
            xac_nhan = st.checkbox("Tôi hiểu và chắc chắn muốn xóa toàn bộ dữ liệu")
            if st.button("XÓA TOÀN BỘ HỆ THỐNG", type="secondary", disabled=not xac_nhan):
                conn = sqlite3.connect(DB_FILE)
                conn.execute("DELETE FROM phieu_can")
                conn.commit()
                conn.close()
                st.warning("Đã làm sạch toàn bộ dữ liệu!")
                st.rerun()
    else:
        st.info("Hệ thống chưa có dữ liệu nào.")
