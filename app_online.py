import streamlit as st
import pandas as pd
import sqlite3
import re
import io
from datetime import date

# ----------------- CẤU HÌNH TRANG -----------------
st.set_page_config(
    page_title="Hệ Thống Cân Hàng & Tính Tiền",
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
    """Trích xuất danh sách số từ chuỗi nhập vào"""
    if not raw_text:
        return []
    # Tìm tất cả các số nguyên hoặc số thực
    found = re.findall(r"[-+]?\d*\.\d+|\d+", raw_text.replace(",", "."))
    nums = []
    for x in found:
        try:
            val = float(x)
            if val > 0:
                nums.append(val)
        except ValueError:
            pass
    return nums

# ----------------- GIAO DIỆN ỨNG DỤNG -----------------
st.title("⚖️ Quản Lý Cân Hàng & Tính Tiền Online")

menu = st.sidebar.radio(
    "📌 Chức năng",
    ["📝 Nhập Lượt Cân Mới", "📅 Sổ Kê Chi Tiết Theo Ngày", "📊 Tổng Hợp & Xuất Excel"]
)

# ================= MENU 1: NHẬP LƯỢT CÂN =================
if menu == "📝 Nhập Lượt Cân Mới":
    st.subheader("Nhập Thông Tin Đợt Cân")

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

    st.markdown("#### 📦 Nhập số cân chi tiết (từng bao/két)")
    st.caption("Cách dùng trên điện thoại/máy tính: Dán hoặc gõ liên tiếp các số cân, cách nhau bằng dấu cách hoặc xuống dòng (VD: `53 56 53 56 53 54 55 54...`)")
    
    day_so_can = st.text_area("Danh sách số cân từng bao:", height=120, placeholder="53 56 53 56 53 54 55 54\n54 36 57 55 52 52 35 55...")

    # Phân tích nhanh số liệu vừa gõ
    list_nums = parse_numbers(day_so_can)
    so_bao = len(list_nums)
    tong_kl_tu_dong = sum(list_nums)

    if so_bao > 0:
        st.info(f"👉 **Đã nhận diện:** `{so_bao}` bao | **Tổng cân:** `{tong_kl_tu_dong:,.1f}` kg")
        # Hiển thị xem trước dạng lưới
        with st.expander("👁️ Xem trước bảng cân phân bố theo cột"):
            cols_preview = st.columns(8)
            for idx, n in enumerate(list_nums):
                cols_preview[idx % 8].write(f"**#{idx+1}:** {n:g}")

    # Cho phép nhập đè nếu chỉ cân tổng (không cân lẻ)
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

# ================= MENU 2: SỔ KÊ THEO NGÀY =================
elif menu == "📅 Sổ Kê Chi Tiết Theo Ngày":
    st.subheader("Tra Cứu & Đối Chiếu Phiếu Cân Theo Ngày")
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
        m3.metric("KL sau khấu hao", f"{t_sau_kh:,.1f} kg")
        m4.metric("Tổng thành tiền", f"{t_tien:,.2f}")

        st.markdown("---")
        # Hiển thị danh sách các phiếu
        for _, row in df.iterrows():
            with st.container():
                st.markdown(f"### 📍 Phiếu #{row['id']}: **{row['ten_hang']}** ({row['ghi_chu'] or 'Không ghi chú'})")
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"- **Số bao:** {row['so_bao']} bao")
                c2.write(f"- **Tổng KL:** {row['khoi_luong']:,.1f} kg")
                c3.write(f"- **Đơn giá:** {row['don_gia']:,.2f}")
                c4.write(f"- **Thành tiền:** `{row['thanh_tien']:,.2f}`")

                if row["danh_sach_can"]:
                    with st.expander(f"🔍 Xem bảng từng bao của phiếu #{row['id']}"):
                        ds = [float(x) for x in row["danh_sach_can"].split(", ")]
                        sub_cols = st.columns(8)
                        for i, val in enumerate(ds):
                            sub_cols[i % 8].caption(f"#{i+1}: **{val:g}**")

                st.divider()

        # Tùy chọn xóa phiếu nhầm
        with st.expander("⚠️ Quản lý / Xóa phiếu cân nhầm"):
            id_xoa = st.selectbox("Chọn STT phiếu cần xóa:", df["id"].tolist())
            if st.button("Xóa phiếu này", type="secondary"):
                conn = sqlite3.connect(DB_FILE)
                conn.execute("DELETE FROM phieu_can WHERE id = ?", (id_xoa,))
                conn.commit()
                conn.close()
                st.warning(f"Đã xóa thành công phiếu #{id_xoa}!")
                st.rerun()
    else:
        st.info("Chưa có lượt cân nào trong ngày được chọn.")

# ================= MENU 3: TỔNG HỢP & XUẤT EXCEL =================
elif menu == "📊 Tổng Hợp & Xuất Excel":
    st.subheader("Bảng Tổng Hợp Toàn Bộ & Xuất Báo Cáo")

    conn = sqlite3.connect(DB_FILE)
    df_all = pd.read_sql_query("SELECT id, ngay, ten_hang, so_bao, khoi_luong, khau_hao, kl_sau_kh, don_gia, thanh_tien, ghi_chu, danh_sach_can FROM phieu_can ORDER BY ngay ASC, id ASC", conn)
    conn.close()

    if not df_all.empty:
        st.dataframe(df_all.drop(columns=["danh_sach_can"]), use_container_width=True)

        # Xuất file Excel
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
    else:
        st.info("Hệ thống chưa có dữ liệu.")