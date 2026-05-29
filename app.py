import streamlit as st
import duckdb
import pandas as pd
import datetime
import os
import random
import string

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
if 'cart' not in st.session_state:
    st.session_state.cart = []


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

def generate_product_id():
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"PROD-{suffix}"

# Pastikan new_product_id diinisialisasi dalam session state
if 'new_product_id' not in st.session_state:
    st.session_state.new_product_id = generate_product_id()

def get_column_mapping(df):
    mapping = {
        'id': 'product_id',
        'name': 'product_name',
        'category': 'category',
        'created_at': 'created_at'
    }
    
    # Deteksi setiap kolom dalam dataframe dan petakan secara dinamis
    for col in df.columns:
        c_low = col.lower()
        if 'id' in c_low:
            mapping['id'] = col
        elif 'nama' in c_low or 'name' in c_low or 'barang' in c_low or 'produk' in c_low or 'title' in c_low:
            mapping['name'] = col
        elif 'kat' in c_low or 'cat' in c_low:
            mapping['category'] = col
        elif 'waktu' in c_low or 'created' in c_low or 'time' in c_low or 'date' in c_low or 'masuk' in c_low:
            mapping['created_at'] = col
            
    return mapping

def create_default_table(con, table_name="Product_catalog"):
    try:
        # Query pembuatan tabel Product_catalog dengan skema baru yang disederhanakan dan waktu WIB
        create_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            product_id VARCHAR PRIMARY KEY,
            product_name VARCHAR NOT NULL,
            category VARCHAR,
            created_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL 7 HOUR)
        );
        """
        con.execute(create_query)
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
    
    # 2. Menu Navigasi Utama
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧭 Menu ")
    st.sidebar.info("🛍️ Katalog Produk (Database Produk)")
    st.session_state.menu = "🛍️ Katalog Produk"
else:
    st.session_state.menu = "🛍️ Katalog Produk"

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
        # Dapatkan kolom-kolom tabel secara dinamis
        df_info = _conn.execute(f"PRAGMA table_info({table})").fetchdf()
        columns = df_info['name'].tolist() if not df_info.empty else []
        
        # Cari kolom waktu masuk secara cerdas untuk pengurutan
        order_col = None
        for col in columns:
            c_low = col.lower()
            if any(keyword in c_low for keyword in ['waktu', 'created', 'time', 'date', 'masuk']):
                order_col = col
                break
                
        if order_col:
            query = f"SELECT * FROM {table} ORDER BY {order_col} DESC"
        else:
            query = f"SELECT * FROM {table}"
            
        return _conn.execute(query).fetchdf()
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")
        return pd.DataFrame()

df_catalog = fetch_catalog_data(con, table_name)

# Ambil peta kolom dinamis dari database online milik pengguna
col_map = get_column_mapping(df_catalog)
id_col = col_map.get('id', 'product_id')
name_col = col_map.get('name', 'product_name')
category_col = col_map.get('category', 'category')
price_col = col_map.get('price', 'price')
desc_col = col_map.get('description', 'description')
status_col = col_map.get('status', 'status')
created_at_col = col_map.get('created_at', 'created_at')

# 7. Cabut Pembagian Menu (Navigation Router)
if st.session_state.menu == "🛍️ Katalog Produk":
    # ------------------ MENU KATALOG PRODUK ------------------
    # Menghitung Ringkasan Statistik Inventaris (Metrik Premium Dinamis)
    if not df_catalog.empty:
        total_products = len(df_catalog)
        
        metrics_data = []
        metrics_data.append({
            "title": "Total Produk",
            "value": f"{total_products}",
            "color": "#6366F1",
            "footer": "📈 Total Produk dalam Katalog Aktif"
        })
        
        if status_col in df_catalog.columns:
            active_products = len(df_catalog[df_catalog[status_col].astype(str).str.lower() == 'active'])
            metrics_data.append({
                "title": "Aktif di Katalog",
                "value": f"{active_products}",
                "color": "#10B981",
                "footer": "Dari keseluruhan produk"
            })
            
        if price_col in df_catalog.columns:
            avg_price = df_catalog[price_col].mean()
            metrics_data.append({
                "title": "Rata-rata Harga",
                "value": f"${avg_price:,.2f}",
                "color": "#A855F7",
                "footer": "Nilai Tengah Produk"
            })
            
        if category_col in df_catalog.columns:
            unique_cats = df_catalog[category_col].nunique()
            metrics_data.append({
                "title": "Kategori Produk",
                "value": f"{unique_cats}",
                "color": "#EC4899",
                "footer": "Variasi Jenis Kategori"
            })
            
        # Tampilkan Grid Metrik secara dinamis
        if metrics_data:
            m_cols = st.columns(len(metrics_data))
            for idx, m_info in enumerate(metrics_data):
                with m_cols[idx]:
                    st.markdown(f"""
                    <div class="premium-card">
                        <p style="color: #6B7280; font-size: 0.9rem; font-weight: 500; margin: 0;">{m_info['title']}</p>
                        <h2 style="color: {m_info['color']}; font-size: 2.2rem; font-weight: 700; margin: 5px 0 0 0;">{m_info['value']}</h2>
                        <p style="color: #6B7280; font-size: 0.8rem; margin: 5px 0 0 0;">{m_info['footer']}</p>
                    </div>
                    """, unsafe_allow_html=True)

    # Navigasi Tab Modern untuk Management
    tabs = st.tabs(["🔍 Lihat Katalog", "➕ Tambah Produk", "✏️ Ubah Produk", "❌ Hapus Produk"])

    # ----------------- TAB 1: LIHAT KATALOG (READ) -----------------
    with tabs[0]:
        st.subheader("Katalog Produk Aktif")
        
        if df_catalog.empty:
            st.info("Katalog produk kosong. Tambahkan beberapa produk di tab 'Tambah Produk'.")
        else:
            # Form Filter & Pencarian
            col_search, col_cat = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Cari Produk berdasarkan Nama atau ID", "", key="search_bar")
            with col_cat:
                categories = ["Semua Kategori"] + list(df_catalog[category_col].dropna().unique()) if category_col in df_catalog.columns else ["Semua Kategori"]
                selected_cat = st.selectbox("Kategori", categories)
                
            # Terapkan Filter
            df_filtered = df_catalog.copy()
            if search_query:
                id_search = df_filtered[id_col].astype(str).str.contains(search_query, case=False, na=False) if id_col in df_filtered.columns else False
                name_search = df_filtered[name_col].astype(str).str.contains(search_query, case=False, na=False) if name_col in df_filtered.columns else False
                df_filtered = df_filtered[id_search | name_search]
                
            if category_col in df_filtered.columns and selected_cat != "Semua Kategori":
                df_filtered = df_filtered[df_filtered[category_col] == selected_cat]
                
            # Perbaiki format tampilan DataFrame
            if not df_filtered.empty:
                col_config = {}
                if id_col in df_filtered.columns:
                    col_config[id_col] = st.column_config.TextColumn("Product ID", width="small", required=True)
                if name_col in df_filtered.columns:
                    col_config[name_col] = st.column_config.TextColumn("Product Name", width="medium")
                if category_col in df_filtered.columns:
                    col_config[category_col] = st.column_config.TextColumn("Category")
                if price_col in df_filtered.columns:
                    col_config[price_col] = st.column_config.NumberColumn("Price", format="$ %.2f")
                if desc_col in df_filtered.columns:
                    col_config[desc_col] = st.column_config.TextColumn("Description", width="large")
                if status_col in df_filtered.columns:
                    col_config[status_col] = st.column_config.SelectboxColumn("Status", options=["Active", "Out of Stock", "Draft"])
                if created_at_col in df_filtered.columns:
                    col_config[created_at_col] = st.column_config.DatetimeColumn("Date Added", format="DD/MM/YYYY HH:mm")

                # Pastikan kolom stock tidak ikut ditampilkan
                display_cols = [c for c in df_filtered.columns if 'stock' not in c.lower() and 'stok' not in c.lower()]
                
                st.dataframe(
                    df_filtered[display_cols],
                    column_config=col_config,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Tampilkan tombol download CSV
                csv = df_filtered[display_cols].to_csv(index=False).encode('utf-8')
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
        
        # Ambil kolom dan tipe data dari tabel yang ada
        columns_info = {}
        try:
            schema_query = f"PRAGMA table_info('{table_name}')"
            schema_rows = con.execute(schema_query).fetchall()
            for row in schema_rows:
                columns_info[row[1]] = row[2].upper()
        except Exception as e:
            st.warning(f"Gagal memverifikasi skema secara otomatis. Menggunakan skema standar: {e}")
            columns_info = {
                'product_id': 'VARCHAR', 'product_name': 'VARCHAR', 'category': 'VARCHAR',
                'price': 'DOUBLE', 'description': 'VARCHAR', 'status': 'VARCHAR'
            }
            
        # Form layout yang cantik dan dinamis berbasis kolom database asli
        with st.form("add_product_form", clear_on_submit=True):
            inputs = {}
            col_id, col_name = st.columns([1, 2])
            with col_id:
                # ID Product Auto-Generated & Stabilized!
                auto_id = st.session_state.new_product_id
                st.text_input("Product ID (Auto-Generated)", value=auto_id, disabled=True, key="rendered_auto_id")
                inputs[id_col] = auto_id
            with col_name:
                if name_col in columns_info:
                    inputs[name_col] = st.text_input("Product Name *", placeholder="Masukkan nama produk", help="Nama lengkap produk.")
                    
            # Tampilkan kolom lainnya jika ada di skema
            if category_col in columns_info:
                inputs[category_col] = st.text_input("Category", placeholder="Contoh: Electronics, Apparel")
                    
            if price_col in columns_info:
                inputs[price_col] = st.number_input("Price ($)", min_value=0.0, step=0.01, format="%.2f")
                    
            if desc_col in columns_info:
                inputs[desc_col] = st.text_area("Description", placeholder="Deskripsi lengkap produk...")
            if status_col in columns_info:
                inputs[status_col] = st.selectbox("Status", ["Active", "Out of Stock", "Draft"])
                
            submit_btn = st.form_submit_button("Simpan Produk ke MotherDuck 📥", use_container_width=True)
            
            if submit_btn:
                val_id = inputs.get(id_col, "")
                val_name = inputs.get(name_col, "")
                
                if (id_col in columns_info and not val_id) or (name_col in columns_info and not val_name):
                    st.error("Gagal! Kolom wajib (Nama) harus diisi.")
                else:
                    # Periksa apakah Product ID sudah terpakai
                    if not df_catalog.empty and id_col in df_catalog.columns and val_id in df_catalog[id_col].values:
                        st.error(f"Gagal! ID `{val_id}` sudah digunakan. Coba submit lagi untuk men-generate ID baru.")
                    else:
                        try:
                            # Masukkan data baru ke tabel secara dinamis
                            insert_cols = []
                            insert_vals = []
                            placeholders = []
                            
                            for col, val in inputs.items():
                                if 'stock' not in col.lower() and 'stok' not in col.lower():
                                    insert_cols.append(col)
                                    if col == price_col:
                                        insert_vals.append(float(val))
                                    else:
                                        insert_vals.append(val)
                                    placeholders.append("?")
                                
                            # Tambahkan kolom waktu masuk jika ada di tabel tapi tidak di input form (Sesuaikan ke WIB)
                            if created_at_col in columns_info and created_at_col not in insert_cols:
                                insert_cols.append(created_at_col)
                                placeholders.append("CURRENT_TIMESTAMP + INTERVAL 7 HOUR")
                                
                            cols_str = ", ".join(insert_cols)
                            placeholders_str = ", ".join(placeholders)
                            
                            insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders_str})"
                            con.execute(insert_query, insert_vals)
                            
                            st.toast(f"Sukses! Produk {val_name} ({val_id}) telah ditambahkan. 🎉", icon="✅")
                            st.success(f"Produk `{val_name}` berhasil disimpan ke database MotherDuck!")
                            
                            # Reset ID produk untuk input berikutnya
                            st.session_state.new_product_id = generate_product_id()
                            
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
            # Pilih produk untuk diedit secara dinamis
            product_list = [f"{row[id_col]} - {row[name_col]}" for _, row in df_catalog.iterrows()]
            selected_prod_str = st.selectbox("Pilih Produk yang Ingin Diubah", product_list)
            
            selected_id = selected_prod_str.split(" - ")[0]
            product_to_edit = df_catalog[df_catalog[id_col] == selected_id].iloc[0]
            
            # Form edit data
            with st.form("edit_product_form"):
                st.markdown(f"**Mengedit Produk ID:** `{selected_id}`")
                
                inputs_e = {}
                
                if name_col in columns_info:
                    inputs_e[name_col] = st.text_input("Product Name *", value=product_to_edit[name_col])
                    
                if category_col in columns_info:
                    inputs_e[category_col] = st.text_input("Category", value=product_to_edit.get(category_col, ''))
                
                if price_col in columns_info:
                    inputs_e[price_col] = st.number_input("Price ($)", min_value=0.0, step=0.01, format="%.2f", value=float(product_to_edit.get(price_col, 0.0)))
                        
                if desc_col in columns_info:
                    inputs_e[desc_col] = st.text_area("Description", value=product_to_edit.get(desc_col, ''))
                    
                if status_col in columns_info:
                    status_opts = ["Active", "Out of Stock", "Draft"]
                    curr_status = product_to_edit.get(status_col, 'Active')
                    default_status_idx = status_opts.index(curr_status) if curr_status in status_opts else 0
                    inputs_e[status_col] = st.selectbox("Status", status_opts, index=default_status_idx)
                    
                save_changes = st.form_submit_button("Simpan Perubahan 💾", use_container_width=True)
                
                if save_changes:
                    val_name_e = inputs_e.get(name_col, "")
                    if name_col in columns_info and not val_name_e:
                        st.error("Nama produk tidak boleh kosong!")
                    else:
                        try:
                            # Bangun kueri UPDATE secara dinamis
                            update_sets = []
                            update_vals = []
                            
                            for col, val in inputs_e.items():
                                if 'stock' not in col.lower() and 'stok' not in col.lower():
                                    update_sets.append(f"{col} = ?")
                                    if col == price_col:
                                        update_vals.append(float(val))
                                    else:
                                        update_vals.append(val)
                                    
                            update_vals.append(selected_id)
                            update_sets_str = ", ".join(update_sets)
                            
                            update_query = f"UPDATE {table_name} SET {update_sets_str} WHERE {id_col} = ?"
                            con.execute(update_query, update_vals)
                            
                            st.toast("Sukses! Produk berhasil diperbarui. 💫", icon="✅")
                            st.success("Informasi produk berhasil disimpan!")
                            
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
            # Pilih produk untuk dihapus secara dinamis
            del_product_list = [f"{row[id_col]} - {row[name_col]}" for _, row in df_catalog.iterrows()]
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
                        delete_query = f"DELETE FROM {table_name} WHERE {id_col} = ?"
                        con.execute(delete_query, (selected_del_id,))
                        
                        st.toast(f"Produk {prod_del_name} telah dihapus dari database. 🗑️", icon="⚠️")
                        st.success(f"Produk `{prod_del_name}` ({selected_del_id}) berhasil dihapus!")
                        
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data dari database: {e}")

else:
    # ------------------ MENU KERANJANG BELANJA ------------------
    st.subheader("🛒 Keranjang Belanja")
    st.markdown("Simulasi Pembelian & Pemesanan Barang dari Katalog Produk Cloud.")
    st.markdown("---")
    
    if df_catalog.empty:
        st.warning("Katalog produk kosong. Silakan tambahkan produk terlebih dahulu di menu Katalog Produk.")
    else:
        col_form, col_cart_view = st.columns([1, 2])
        
        with col_form:
            st.markdown("""
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 12px; margin-bottom:15px;">
                <h4 style="color: #6366F1; margin-top:0; margin-bottom:5px;">➕ Tambah Item</h4>
                <p style="color: #6B7280; font-size: 0.8rem; margin:0;">Pilih produk yang ada di katalog</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Form tambah item ke keranjang
            # Display: ID - Name - Price
            prod_select_list = []
            prod_detail_map = {}
            
            for _, row in df_catalog.iterrows():
                p_id = row[id_col]
                p_name = row[name_col]
                p_price = row.get(price_col, 0.0) if price_col in df_catalog.columns else 0.0
                display_str = f"{p_id} - {p_name} (${p_price:,.2f})"
                prod_select_list.append(display_str)
                prod_detail_map[display_str] = {
                    'id': p_id,
                    'name': p_name,
                    'price': float(p_price)
                }
                
            selected_item_str = st.selectbox("Pilih Barang", prod_select_list)
            qty = st.number_input("Jumlah Pembelian", min_value=1, value=1, step=1)
            
            add_to_cart_btn = st.button("Tambahkan ke Keranjang 📥", use_container_width=True)
            
            if add_to_cart_btn and selected_item_str:
                item_details = prod_detail_map[selected_item_str]
                
                # Cek apakah barang sudah ada di keranjang
                found = False
                for item in st.session_state.cart:
                    if item['id'] == item_details['id']:
                        item['qty'] += qty
                        item['total'] = item['qty'] * item['price']
                        found = True
                        break
                        
                if not found:
                    st.session_state.cart.append({
                        'id': item_details['id'],
                        'name': item_details['name'],
                        'price': item_details['price'],
                        'qty': qty,
                        'total': qty * item_details['price']
                    })
                    
                st.toast(f"{item_details['name']} berhasil ditambahkan ke keranjang! 🛒", icon="✅")
                st.rerun()
                
        with col_cart_view:
            st.markdown("#### 🛍️ Detail Belanjaan Anda")
            
            if not st.session_state.cart:
                st.info("Keranjang Anda saat ini kosong. Pilih produk di sebelah kiri untuk mulai berbelanja!")
            else:
                # Konversi keranjang ke DataFrame
                df_cart = pd.DataFrame(st.session_state.cart)
                
                # Tampilkan tabel keranjang belanja dengan style premium
                st.dataframe(
                    df_cart,
                    column_config={
                        "id": st.column_config.TextColumn("Product ID", width="small"),
                        "name": st.column_config.TextColumn("Nama Barang", width="medium"),
                        "price": st.column_config.NumberColumn("Harga Satuan", format="$ %.2f"),
                        "qty": st.column_config.NumberColumn("Jumlah", format="%d"),
                        "total": st.column_config.NumberColumn("Total Harga", format="$ %.2f")
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Hitung total belanja
                total_checkout = df_cart['total'].sum()
                
                col_clear, col_pay = st.columns(2)
                with col_clear:
                    if st.button("🗑️ Kosongkan Keranjang", use_container_width=True, type="secondary"):
                        st.session_state.cart = []
                        st.toast("Keranjang belanja dikosongkan.", icon="🗑️")
                        st.rerun()
                with col_pay:
                    if st.button(f"💳 Bayar Sekarang (${total_checkout:,.2f})", use_container_width=True, type="primary"):
                        st.session_state.cart = []
                        st.toast("Pembayaran Berhasil! Terima kasih telah berbelanja. 🎉", icon="✅")
                        st.success(f"Sukses! Pemesanan senilai **${total_checkout:,.2f}** telah berhasil diproses secara online.")
