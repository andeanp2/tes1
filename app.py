import streamlit as st
import duckdb
import pandas as pd
import datetime
import os

# 1. Konfigurasi Halaman & Tema Premium
st.set_page_config(
    page_title="MotherDuck Product Catalog",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan premium, modern, dan interaktif
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Header styling */
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        padding-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    
    /* Card Glassmorphism */
    .premium-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 20px;
    }
    
    .premium-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(99, 102, 241, 0.1);
        border-color: rgba(99, 102, 241, 0.3);
    }
    
    /* Status Badge styling */
    .badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
        display: inline-block;
    }
    .badge-active {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-out {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .badge-draft {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    /* Custom Streamlit Input Styling Override */
    div[data-baseweb="input"] {
        border-radius: 8px !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #6366F1 !important;
    }
    
    /* Gradient line divider */
    .gradient-line {
        height: 4px;
        background: linear-gradient(90deg, #6366F1 0%, #A855F7 50%, #EC4899 100%);
        border-radius: 2px;
        margin-bottom: 2rem;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# 2. Inisialisasi Session State
if 'conn_connected' not in st.session_state:
    st.session_state.conn_connected = False
if 'db_error' not in st.session_state:
    st.session_state.db_error = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Lihat Katalog"


# 3. Helpers untuk Koneksi MotherDuck
@st.cache_resource
def init_connection():
    # 2. Ambil token dan bersihkan dari spasi/karakter tak terlihat (.strip())
    md_token = st.secrets["MOTHERDUCK_TOKEN"].strip()
    
    # 3. Set sebagai Environment Variable sistem
    os.environ["MOTHERDUCK_TOKEN"] = md_token
    
    # 4. Hubungkan langsung secara bersih tanpa f-string atau config dict
    con = duckdb.connect("md:New_db")
    
    # Pastikan ekstensi terinstal dan dimuat secara online
    con.execute("INSTALL motherduck;")
    con.execute("LOAD motherduck;")
    return con

# Inisialisasi koneksi secara otomatis saat aplikasi dimulai
try:
    con = init_connection()
    st.session_state.con = con
    st.session_state.conn_connected = True
    st.session_state.db_error = None
except Exception as e:
    st.session_state.conn_connected = False
    st.session_state.db_error = str(e)

def get_databases(con):
    try:
        df_dbs = con.execute("SHOW DATABASES").fetchdf()
        return df_dbs.iloc[:, 0].tolist()
    except Exception as e:
        return []
def check_table_exists(con, table_name="Product_catalog"):
    try:
        df_tables = con.execute("SHOW TABLES").fetchdf()
        if df_tables.empty:
            return False
        return table_name in df_tables.iloc[:, 0].values
    except Exception as e:
        return False

def create_default_table(con, table_name="Product_catalog"):
    try:
        # Query pembuatan tabel Product_catalog dengan skema standar lengkap
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            product_id VARCHAR PRIMARY KEY,
            product_name VARCHAR NOT NULL,
            category VARCHAR,
            price DOUBLE,
            stock INTEGER,
            description TEXT,
            status VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        con.execute(create_query)
        
        # Masukkan sampel data produk agar user langsung terpukau melihat data awal
        sample_data = [
            ("PROD-001", "AeroGlide Mechanical Keyboard", "Electronics", 129.99, 45, "Ultra-responsive mechanical keyboard with hot-swappable switches and dynamic RGB backlighting.", "Active"),
            ("PROD-002", "Zenith Noise Cancelling Headphones", "Electronics", 299.99, 20, "Premium over-ear headphones with hybrid active noise cancellation and 40-hour battery life.", "Active"),
            ("PROD-003", "HydroPeak Insulated Water Bottle", "Lifestyle", 34.99, 150, "Double-walled vacuum insulated stainless steel water bottle, keeps drinks cold for 24 hours.", "Active"),
            ("PROD-004", "TerraQuest Waterproof Backpack", "Apparel", 89.99, 0, "Rugged, weather-resistant outdoor backpack with a dedicated laptop compartment.", "Out of Stock"),
            ("PROD-005", "Solstice Smart Watch", "Electronics", 199.99, 15, "Sleek smartwatch featuring comprehensive health tracking and built-in GPS.", "Draft")
        ]
        
        for item in sample_data:
            con.execute(f"""
                INSERT INTO {table_name} (product_id, product_name, category, price, stock, description, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, item)
            
        return True
    except Exception as e:
        st.error(f"Gagal membuat tabel default: {e}")
        return False


# 4. Tampilan Sidebar (Konfigurasi & Koneksi)
st.sidebar.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <h2 style="color: #6366F1; font-weight: 700; margin-bottom: 0;">MD Control Panel</h2>
    <p style="color: #6B7280; font-size: 0.85rem;">Koneksi Database MotherDuck (Online Cloud)</p>
</div>
""", unsafe_allow_html=True)

# Parameter default
db_name = "New_db"
table_name = "Product_catalog"

if st.session_state.conn_connected and 'con' in st.session_state:
    con = st.session_state.con
    
    # 1. Menampilkan detail akun online
    try:
        user_info = con.execute("SELECT current_user()").fetchone()[0]
        st.sidebar.info(f"☁️ Akun: **{user_info}**")
    except:
        pass
        
    st.sidebar.markdown("### 🗄️ Lingkup Database Cloud")
    
    # Database default yang terhubung
    st.sidebar.text_input("Database Terkoneksi", value=db_name, disabled=True, help="Database target yang telah terhubung.")
    
    # Tentukan nama tabel
    table_name = st.sidebar.text_input("Table Name", value="Product_catalog")

# Tampilkan status koneksi di sidebar
if st.session_state.conn_connected:
    st.sidebar.markdown("""
    <div style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid #10B981; border-radius: 8px; padding: 12px; margin-top: 15px; text-align: center;">
        <span style="color: #10B981; font-weight: 600; font-size: 0.9rem;">🟢 Terkoneksi Cloud (New_db)</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.markdown("""
    <div style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid #EF4444; border-radius: 8px; padding: 12px; margin-top: 15px; text-align: center;">
        <span style="color: #EF4444; font-weight: 600; font-size: 0.9rem;">🔴 Terputus dari Cloud</span>
    </div>
    """, unsafe_allow_html=True)
    if st.session_state.db_error:
        st.sidebar.error(f"Error: {st.session_state.db_error}")


# 5. Dashboard Utama
st.markdown('<h1 class="main-title">MotherDuck Product Catalog Portal</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Manajemen Inventaris & Katalog Produk Cloud Real-time</p>', unsafe_allow_html=True)
st.markdown('<div class="gradient-line"></div>', unsafe_allow_html=True)

# Jika belum terhubung, tampilkan panduan kesalahan kredensial secrets.toml
if not st.session_state.conn_connected or 'con' not in st.session_state:
    st.error("🔴 Gagal terhubung secara aman ke MotherDuck Cloud.")
    
    if st.session_state.db_error:
        st.markdown(f"""
        <div style="background-color: rgba(239, 68, 68, 0.08); border-left: 5px solid #EF4444; padding: 15px; border-radius: 8px; margin-bottom: 25px;">
            <strong style="color: #EF4444; font-size: 1rem;">Detail Error Koneksi:</strong><br/>
            <code style="color: #EF4444; font-size: 0.9rem;">{st.session_state.db_error}</code>
        </div>
        """, unsafe_allow_html=True)
        
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 🔑 Cara Mengonfigurasi Token MotherDuck:
        Aplikasi ini menggunakan fitur **Streamlit Secrets** untuk mengamankan token Anda tanpa eksposur pada kode sumber.
        
        1. Buka file **`.streamlit/secrets.toml`** yang berada di root direktori proyek Anda.
        2. Masukkan token asli Anda:
           ```toml
           MOTHERDUCK_TOKEN = "md_token_anda_disini"
           ```
        3. Simpan file tersebut, lalu muat ulang (*refresh*) halaman browser ini.
        """)
    with col2:
        st.markdown("""
        ### 💡 Cara Mendapatkan Token:
        1. Masuk ke dashboard [MotherDuck](https://motherduck.com).
        2. Klik **foto profil** Anda di pojok kiri bawah layar.
        3. Pilih opsi **"Copy token"**.
        4. Salin dan tempelkan token tersebut di file `secrets.toml`.
        
        *Dengan menggunakan `st.secrets`, kredensial Anda disimpan secara lokal dan tidak akan pernah terunggah ke repositori publik.*
        """)
    st.stop()

# Jika sudah terhubung, lakukan inisialisasi pengecekan tabel
con = st.session_state.con

table_exists = check_table_exists(con, table_name)

if not table_exists:
    st.warning(f"⚠️ Tabel `{table_name}` tidak ditemukan di database `{db_name}`.")
    create_table_col = st.columns([1, 2])
    with create_table_col[0]:
        if st.button("Buat Tabel & Sampel Data Otomatis 🛠️", use_container_width=True):
            with st.spinner("Membuat tabel standar..."):
                if create_default_table(con, table_name):
                    st.success(f"Tabel `{table_name}` berhasil dibuat beserta data sampel! Refresh halaman...")
                    st.rerun()
    with create_table_col[1]:
        st.write("Tombol ini akan membuat tabel baru dengan skema produk lengkap (ID, nama, kategori, harga, stok, deskripsi, status) dan mengisi data awal agar Anda dapat langsung mencobanya.")
    st.stop()

# 6. Mengambil Data Terbaru dari MotherDuck
@st.cache_data(ttl=10) # Cache singkat agar tetap real-time tapi tidak terlalu membebani query
def fetch_catalog_data(_conn, table):
    try:
        df = _conn.execute(f"SELECT * FROM {table} ORDER BY created_at DESC").fetchdf()
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")
        return pd.DataFrame()

df_catalog = fetch_catalog_data(con, table_name)

# 7. Menghitung Ringkasan Statistik Inventaris (Metrik Premium)
if not df_catalog.empty:
    total_products = len(df_catalog)
    active_products = len(df_catalog[df_catalog['status'].str.lower() == 'active']) if 'status' in df_catalog.columns else 0
    
    if 'price' in df_catalog.columns and 'stock' in df_catalog.columns:
        total_value = (df_catalog['price'] * df_catalog['stock']).sum()
    else:
        total_value = 0
        
    out_of_stock = len(df_catalog[df_catalog['stock'] == 0]) if 'stock' in df_catalog.columns else 0
    
    # Tampilkan Grid Metrik Bergaya
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="premium-card">
            <p style="color: #6B7280; font-size: 0.9rem; font-weight: 500; margin: 0;">Total Produk</p>
            <h2 style="color: #6366F1; font-size: 2.2rem; font-weight: 700; margin: 5px 0 0 0;">{total_products}</h2>
            <p style="color: #10B981; font-size: 0.8rem; margin: 5px 0 0 0;">📈 Terkoneksi Real-time</p>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="premium-card">
            <p style="color: #6B7280; font-size: 0.9rem; font-weight: 500; margin: 0;">Aktif di Katalog</p>
            <h2 style="color: #10B981; font-size: 2.2rem; font-weight: 700; margin: 5px 0 0 0;">{active_products}</h2>
            <p style="color: #6B7280; font-size: 0.8rem; margin: 5px 0 0 0;">Dari keseluruhan produk</p>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="premium-card">
            <p style="color: #6B7280; font-size: 0.9rem; font-weight: 500; margin: 0;">Total Nilai Inventaris</p>
            <h2 style="color: #A855F7; font-size: 2.2rem; font-weight: 700; margin: 5px 0 0 0;">${total_value:,.2f}</h2>
            <p style="color: #6B7280; font-size: 0.8rem; margin: 5px 0 0 0;">Harga × Jumlah Stok</p>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="premium-card">
            <p style="color: #6B7280; font-size: 0.9rem; font-weight: 500; margin: 0;">Habis Stok (Out of Stock)</p>
            <h2 style="color: #EF4444; font-size: 2.2rem; font-weight: 700; margin: 5px 0 0 0;">{out_of_stock}</h2>
            <p style="color: #EF4444; font-size: 0.8rem; margin: 5px 0 0 0;">⚠️ Memerlukan Restock</p>
        </div>
        """, unsafe_allow_html=True)

# 8. Navigasi Tab Modern
tabs = st.tabs(["🔍 Lihat Katalog", "➕ Tambah Produk", "✏️ Ubah Produk", "❌ Hapus Produk"])

# ----------------- TAB 1: LIHAT KATALOG (READ) -----------------
with tabs[0]:
    st.subheader("Daftar Inventaris Product_catalog")
    
    if df_catalog.empty:
        st.info("Katalog produk kosong. Tambahkan beberapa produk di tab 'Tambah Produk'.")
    else:
        # Form Filter & Pencarian
        col_search, col_cat, col_status = st.columns([2, 1, 1])
        with col_search:
            search_query = st.text_input("🔍 Cari Produk berdasarkan Nama atau ID", "", key="search_bar")
        with col_cat:
            categories = ["Semua Kategori"] + list(df_catalog['category'].dropna().unique()) if 'category' in df_catalog.columns else ["Semua Kategori"]
            selected_cat = st.selectbox("Kategori", categories)
        with col_status:
            statuses = ["Semua Status"] + list(df_catalog['status'].dropna().unique()) if 'status' in df_catalog.columns else ["Semua Status"]
            selected_status = st.selectbox("Status", statuses)
            
        # Terapkan Filter
        df_filtered = df_catalog.copy()
        if search_query:
            df_filtered = df_filtered[
                df_filtered['product_name'].str.contains(search_query, case=False, na=False) |
                df_filtered['product_id'].str.contains(search_query, case=False, na=False)
            ]
        if selected_cat != "Semua Kategori":
            df_filtered = df_filtered[df_filtered['category'] == selected_cat]
        if selected_status != "Semua Status":
            df_filtered = df_filtered[df_filtered['status'] == selected_status]
            
        # Perbaiki format tampilan DataFrame
        if not df_filtered.empty:
            # Tampilkan data dengan tabel Streamlit premium
            st.dataframe(
                df_filtered,
                column_config={
                    "product_id": st.column_config.TextColumn("Product ID", width="small", required=True),
                    "product_name": st.column_config.TextColumn("Product Name", width="medium"),
                    "category": st.column_config.TextColumn("Category"),
                    "price": st.column_config.NumberColumn("Price", format="$ %.2f"),
                    "stock": st.column_config.NumberColumn("Stock", format="%d"),
                    "description": st.column_config.TextColumn("Description", width="large"),
                    "status": st.column_config.SelectboxColumn("Status", options=["Active", "Out of Stock", "Draft"]),
                    "created_at": st.column_config.DatetimeColumn("Date Added", format="DD/MM/YYYY HH:mm")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Tampilkan tombol download CSV
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Unduh Data sebagai CSV",
                data=csv,
                file_name=f"product_catalog_{datetime.date.today()}.csv",
                mime='text/csv',
            )
        else:
            st.warning("Tidak ada produk yang cocok dengan pencarian / filter Anda.")


# ----------------- TAB 2: TAMBAH PRODUK (CREATE) -----------------
with tabs[1]:
    st.subheader("Tambah Produk Baru")
    st.write("Silakan isi formulir di bawah ini untuk menambahkan produk baru ke katalog MotherDuck.")
    
    # Ambil kolom dan tipe data dari tabel yang ada untuk memvalidasi kolom input dinamis
    columns_info = {}
    try:
        schema_query = f"PRAGMA table_info('{table_name}')"
        schema_rows = con.execute(schema_query).fetchall()
        for row in schema_rows:
            # row format: (cid, name, type, notnull, dflt_value, pk)
            columns_info[row[1]] = row[2].upper()
    except Exception as e:
        st.warning(f"Gagal memverifikasi skema secara otomatis. Menggunakan skema standar: {e}")
        # Default fallback
        columns_info = {
            'product_id': 'VARCHAR', 'product_name': 'VARCHAR', 'category': 'VARCHAR',
            'price': 'DOUBLE', 'stock': 'INTEGER', 'description': 'VARCHAR', 'status': 'VARCHAR'
        }
        
    # Form layout yang cantik
    with st.form("add_product_form", clear_on_submit=True):
        col_id, col_name = st.columns([1, 2])
        with col_id:
            prod_id = st.text_input("Product ID *", placeholder="Contoh: PROD-101", help="ID unik produk, tidak boleh duplikat.")
        with col_name:
            prod_name = st.text_input("Product Name *", placeholder="Masukkan nama produk", help="Nama lengkap produk.")
            
        col_cat_in, col_price_in, col_stock_in = st.columns(3)
        with col_cat_in:
            prod_cat = st.text_input("Category", placeholder="Contoh: Electronics, Apparel, Lifestyle")
        with col_price_in:
            prod_price = st.number_input("Price ($)", min_value=0.0, step=0.01, format="%.2f")
        with col_stock_in:
            prod_stock = st.number_input("Stock", min_value=0, step=1)
            
        prod_desc = st.text_area("Description", placeholder="Deskripsi lengkap spesifikasi dan detail produk...")
        
        prod_status = st.selectbox("Status", ["Active", "Out of Stock", "Draft"])
        
        submit_btn = st.form_submit_button("Simpan Produk ke MotherDuck 📥", use_container_width=True)
        
        if submit_btn:
            # Validasi form
            if not prod_id or not prod_name:
                st.error("Gagal! Kolom **Product ID** dan **Product Name** wajib diisi.")
            else:
                # Periksa apakah Product ID sudah terpakai
                if not df_catalog.empty and prod_id in df_catalog['product_id'].values:
                    st.error(f"Gagal! Product ID `{prod_id}` sudah digunakan oleh produk lain. Silakan pilih ID yang unik.")
                else:
                    try:
                        # Masukkan data baru ke tabel
                        full_table_path = table_name
                        insert_query = f"""
                            INSERT INTO {full_table_path} (product_id, product_name, category, price, stock, description, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """
                        con.execute(insert_query, (prod_id, prod_name, prod_cat, prod_price, int(prod_stock), prod_desc, prod_status))
                        
                        st.toast(f"Sukses! Produk {prod_name} ({prod_id}) telah ditambahkan. 🎉", icon="✅")
                        st.success(f"Produk `{prod_name}` berhasil disimpan ke database MotherDuck!")
                        
                        # Hapus cache agar data terbaru langsung ter-fetch
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan data ke MotherDuck: {e}")


# ----------------- TAB 3: UBAH PRODUK (UPDATE) -----------------
with tabs[2]:
    st.subheader("Ubah Informasi Produk")
    
    if df_catalog.empty:
        st.info("Katalog kosong. Tidak ada produk yang bisa diubah.")
    else:
        # Pilih produk untuk diedit
        product_list = [f"{row['product_id']} - {row['product_name']}" for _, row in df_catalog.iterrows()]
        selected_prod_str = st.selectbox("Pilih Produk yang Ingin Diubah", product_list)
        
        selected_id = selected_prod_str.split(" - ")[0]
        product_to_edit = df_catalog[df_catalog['product_id'] == selected_id].iloc[0]
        
        # Form edit data
        with st.form("edit_product_form"):
            st.markdown(f"**Mengedit Produk ID:** `{selected_id}`")
            
            edit_name = st.text_input("Product Name *", value=product_to_edit['product_name'])
            
            col_cat_e, col_price_e, col_stock_e = st.columns(3)
            with col_cat_e:
                edit_cat = st.text_input("Category", value=product_to_edit.get('category', ''))
            with col_price_e:
                edit_price = st.number_input("Price ($)", min_value=0.0, step=0.01, format="%.2f", value=float(product_to_edit.get('price', 0.0)))
            with col_stock_e:
                edit_stock = st.number_input("Stock", min_value=0, step=1, value=int(product_to_edit.get('stock', 0)))
                
            edit_desc = st.text_area("Description", value=product_to_edit.get('description', ''))
            
            # Tentukan indeks default untuk dropdown status
            status_opts = ["Active", "Out of Stock", "Draft"]
            curr_status = product_to_edit.get('status', 'Active')
            default_status_idx = status_opts.index(curr_status) if curr_status in status_opts else 0
            edit_status = st.selectbox("Status", status_opts, index=default_status_idx)
            
            save_changes = st.form_submit_button("Simpan Perubahan 💾", use_container_width=True)
            
            if save_changes:
                if not edit_name:
                    st.error("Nama produk tidak boleh kosong!")
                else:
                    try:
                        full_table_path = table_name
                        update_query = f"""
                            UPDATE {full_table_path}
                            SET product_name = ?,
                                category = ?,
                                price = ?,
                                stock = ?,
                                description = ?,
                                status = ?
                            WHERE product_id = ?
                        """
                        con.execute(update_query, (edit_name, edit_cat, edit_price, int(edit_stock), edit_desc, edit_status, selected_id))
                        
                        st.toast(f"Sukses! Produk {edit_name} berhasil diperbarui. 💫", icon="✅")
                        st.success(f"Informasi produk `{edit_name}` berhasil disimpan!")
                        
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal memperbarui data: {e}")


# ----------------- TAB 4: HAPUS PRODUK (DELETE) -----------------
with tabs[3]:
    st.subheader("Hapus Produk dari Katalog")
    st.markdown("""
    <div style="background-color: rgba(239, 68, 68, 0.1); border-left: 5px solid #EF4444; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
        <strong style="color: #EF4444;">Peringatan Penting:</strong> Penghapusan produk bersifat permanen dan data yang dihapus akan langsung terhapus dari tabel database MotherDuck Cloud Anda.
    </div>
    """, unsafe_allow_html=True)
    
    if df_catalog.empty:
        st.info("Katalog kosong. Tidak ada produk yang bisa dihapus.")
    else:
        # Pilih produk untuk dihapus
        del_product_list = [f"{row['product_id']} - {row['product_name']}" for _, row in df_catalog.iterrows()]
        selected_del_str = st.selectbox("Pilih Produk yang Ingin Dihapus", del_product_list, key="del_select")
        
        selected_del_id = selected_del_str.split(" - ")[0]
        prod_del_name = selected_del_str.split(" - ")[1]
        
        # Konfirmasi penghapusan demi keamanan data
        st.markdown(f"Anda memilih untuk menghapus produk berikut:")
        st.code(f"ID: {selected_del_id}\nNama: {prod_del_name}")
        
        confirm_check = st.checkbox("Saya memahami bahwa tindakan ini tidak dapat dibatalkan.", value=False)
        
        delete_btn = st.button("Hapus Produk Secara Permanen 🗑️", type="primary", use_container_width=True)
        
        if delete_btn:
            if not confirm_check:
                st.error("Silakan centang kotak persetujuan konfirmasi di atas terlebih dahulu untuk melanjutkan.")
            else:
                try:
                    full_table_path = table_name
                    delete_query = f"DELETE FROM {full_table_path} WHERE product_id = ?"
                    con.execute(delete_query, (selected_del_id,))
                    
                    st.toast(f"Produk {prod_del_name} telah dihapus dari database. 🗑️", icon="⚠️")
                    st.success(f"Produk `{prod_del_name}` ({selected_del_id}) berhasil dihapus!")
                    
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menghapus data dari database: {e}")
