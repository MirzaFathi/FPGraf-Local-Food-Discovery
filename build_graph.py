import os
import pandas as pd
import dashscope
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_community.llms import Tongyi
from langchain_core.prompts import PromptTemplate

# Load environment variables dari file .env
load_dotenv(override=True)

# ==========================================
# 1. KONEKSI KE NEO4J
# ==========================================
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"), 
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

# ==========================================
# 2. SETUP QWEN LLM (VIA DASHSCOPE)
# ==========================================
# Konfigurasi Custom API Host dari Model Studio
dashscope.base_http_api_url = 'https://ws-qhebnre9dgsdfa13.ap-southeast-1.maas.aliyuncs.com/api/v1'
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# Temperature diset rendah (0.1) agar AI fokus pada ekstraksi fakta, bukan berkreasi
llm = Tongyi(
    model="qwen-max", 
    temperature=0.1, 
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
)

# ==========================================
# 3. PROMPT TEMPLATE
# ==========================================
ekstraksi_prompt = PromptTemplate(
    input_variables=["review_text"],
    template="""Tugasmu adalah menganalisis ulasan restoran berikut dan mengekstrak entitas penting.
    
    Ulasan: {review_text}
    
    Ekstrak 4 hal berikut HANYA dari ulasan tersebut:
    1. Menu: Makanan/minuman yang disebutkan.
    2. Fasilitas: Fitur atau suasana tempat (contoh: nyaman, bersih, luas, wifi kencang, parkir luas, estetik, dll).
    3. Sentimen: Kesan keseluruhan ulasan. (Pilih salah satu: Positif, Negatif, Netral).
    4. Harga: Tebak tingkat harga (Pilih salah satu: Murah, Sedang, Mahal, Tidak Diketahui).
    
    Balas dengan format persis seperti ini (pisahkan item dengan koma, tulis 'Tidak ada' jika tidak disebutkan):
    Menu: [daftar menu]
    Fasilitas: [daftar fasilitas/suasana]
    Sentimen: [Positif/Negatif/Netral]
    Harga: [Murah/Sedang/Mahal/Tidak Diketahui]"""
)

# Gabungkan prompt dan LLM menjadi satu chain eksekusi
chain_ekstraksi = ekstraksi_prompt | llm

# ==========================================
# 4. FUNGSI UNTUK INSERT KE GRAPH DB
# ==========================================
def simpan_ke_neo4j(nama_tempat_makan, daerah, kategori, price_level, rating, rating_count, daftar_menu, daftar_fasilitas, sentimen):
    # Skip jika ini ulasan kosong
    if not nama_tempat_makan: return 
        
    query = """
    // 1. ENTITAS UTAMA (TEMPAT MAKAN)
    MERGE (w:TempatMakan {nama: $nama_tempat_makan})
    SET w.rating = toFloat($rating),
        w.rating_count = toInteger($rating_count)
    WITH w
    
    // 2. ENTITAS DAERAH
    MERGE (d:Daerah {nama: $daerah})
    MERGE (w)-[:BERLOKASI_DI]->(d)
    
    // 3. ENTITAS KATEGORI
    MERGE (k:Kategori {nama: $kategori})
    MERGE (w)-[:BERJENIS]->(k)
    
    // 4. ENTITAS PRICE LEVEL
    WITH w
    CALL {
        WITH w
        WITH w, $price_level AS new_price
        WHERE new_price <> 'Tidak Diketahui'
        MERGE (p:PriceLevel {nama: new_price})
        MERGE (w)-[:MEMILIKI_HARGA]->(p)
    }
    
    // 5. ENTITAS MENU
    WITH w
    UNWIND $daftar_menu AS nama_makanan
    WITH w, trim(nama_makanan) AS menu_bersih
    WHERE menu_bersih <> '' AND toLower(menu_bersih) <> 'tidak ada'
    MERGE (m:Menu {nama: menu_bersih})
    MERGE (w)-[:MENYAJIKAN]->(m)
    
    // 6. ENTITAS FASILITAS / SUASANA
    WITH w
    UNWIND $daftar_fasilitas AS nama_fasil
    WITH w, trim(nama_fasil) AS fasil_bersih
    WHERE fasil_bersih <> '' AND toLower(fasil_bersih) <> 'tidak ada'
    MERGE (f:Fasilitas {nama: fasil_bersih})
    MERGE (w)-[:MEMILIKI_FASILITAS]->(f)
    
    // 7. ENTITAS SENTIMEN
    WITH w
    WHERE $sentimen <> '' AND toLower($sentimen) <> 'tidak ada'
    MERGE (s:Sentimen {nama: $sentimen})
    MERGE (w)-[:MENDAPAT_SENTIMEN]->(s)
    """
    
    with driver.session() as session:
        session.run(query, 
                    nama_tempat_makan=nama_tempat_makan, daerah=daerah, kategori=kategori, 
                    price_level=price_level, rating=rating, rating_count=rating_count, 
                    daftar_menu=daftar_menu, daftar_fasilitas=daftar_fasilitas, sentimen=sentimen)
    print(f"[SUCCESS] Tersimpan ke Graph: {nama_tempat_makan}")

# ==========================================
# 5. FUNGSI EKSEKUSI UTAMA (MAIN LOOP)
# ==========================================
def proses_data_ulasan():
    # Blok try-except ini mengantisipasi pembacaan data.
    # Jika menggunakan data CSV, pastikan script memanggil kolom 'contents'.
    try:
        df = pd.read_csv("data_restoran.csv")
        ulasan_list = df.to_dict('records')
        print(f"Membaca {len(ulasan_list)} baris dari CSV lokal.")
    except FileNotFoundError:
        print("File CSV tidak ditemukan. Menggunakan data simulasi/API...")
        # Simulasi struktur data (misal hasil mapping JSON dari API)
        ulasan_list = [
            {
                "nama_tempat_makan": "Nasgor Jawa 27", 
                "contents": "Porsinya brutal! Nasi goreng mawutnya juara, tapi antrenya panjang."
            },
            {
                "nama_tempat_makan": "Gepruk Geprek", 
                "contents": "Ayam penyet dan jamur krispinya enak banget, sambal bawangnya nendang."
            },
            {
                "nama_tempat_makan": "Warung Kane", 
                "contents": "Tempatnya asik buat nongkrong, mesen sei sapi sama es teh manis mantap."
            }
        ]

    # Looping setiap data restoran
    for item in ulasan_list:
        tempat_makan = item.get("nama_tempat_makan")
        # Ekstraksi string ulasan secara presisi dari key/kolom 'contents'
        teks_ulasan = item.get("contents", "") 
        
        # Ekstraksi field tambahan
        daerah = item.get("daerah", "Unknown")
        kategori = item.get("kategori", "Unknown")
        price_level = item.get("price_level", "Tidak Diketahui")
        
        # Ambil nilai rating dan rating_count
        import math
        raw_rating = item.get("rating", 0.0)
        rating = 0.0 if (raw_rating is None or (isinstance(raw_rating, float) and math.isnan(raw_rating))) else float(raw_rating)
        
        raw_rating_count = item.get("rating_count", 0)
        rating_count = 0 if (raw_rating_count is None or (isinstance(raw_rating_count, float) and math.isnan(raw_rating_count))) else int(raw_rating_count)
        
        if not teks_ulasan:
            continue
            
        print(f"\nMemproses: {tempat_makan}...")
        
        # 1. Masukkan teks ulasan ke LLM
        hasil_ekstraksi = chain_ekstraksi.invoke({"review_text": teks_ulasan})
        
        # 2. Parsing output teks Qwen
        lines = hasil_ekstraksi.strip().split('\n')
        daftar_menu = []
        daftar_fasilitas = []
        sentimen = "Netral"
        estimasi_harga = "Tidak Diketahui"
        
        for line in lines:
            line = line.strip()
            if line.startswith("Menu:"):
                menu_str = line.replace("Menu:", "").strip()
                if menu_str.lower() != "tidak ada":
                    daftar_menu = [m.strip() for m in menu_str.split(',')]
            elif line.startswith("Fasilitas:"):
                fasil_str = line.replace("Fasilitas:", "").strip()
                if fasil_str.lower() != "tidak ada":
                    daftar_fasilitas = [f.strip() for f in fasil_str.split(',')]
            elif line.startswith("Sentimen:"):
                sentimen = line.replace("Sentimen:", "").strip()
            elif line.startswith("Harga:"):
                estimasi_harga = line.replace("Harga:", "").strip()
                
        # Jika Google belum tahu harganya, pakai tebakan LLM
        if price_level == "Tidak Diketahui" and estimasi_harga in ["Murah", "Sedang", "Mahal"]:
            price_level = estimasi_harga
            
        # 3. Lempar datanya ke Neo4j
        simpan_ke_neo4j(tempat_makan, daerah, kategori, price_level, rating, rating_count, daftar_menu, daftar_fasilitas, sentimen)

if __name__ == "__main__":
    try:
        print("=== Memulai Pembangunan Graph ===")
        proses_data_ulasan()
        print("\n=== Proses Selesai ===")
    finally:
        # Selalu pastikan koneksi database ditutup pada akhir script
        driver.close()