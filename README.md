# Local Food Discovery Graph

Sistem rekomendasi kuliner berbasis **GraphRAG** (Retrieval-Augmented Generation dengan Knowledge Graph). Proyek ini menggunakan **Neo4j** sebagai graph database dan **LLM Qwen** (melalui DashScope API) untuk membangun pengetahuan kuliner dan melakukan interaksi tanya-jawab dengan pengguna.

---

## 🏗️ Arsitektur Sistem

Proyek ini dibangun menggunakan pendekatan arsitektur **GraphRAG** dengan komponen-komponen berikut:

1. **Knowledge Graph Database**: Menggunakan **Neo4j** untuk menyimpan entitas kuliner secara terstruktur beserta relasinya.
    - **Entitas (Nodes)**: `TempatMakan`, `Daerah`, `Kategori`, `PriceLevel`, `Menu`, `Fasilitas`, `Sentimen`.
    - **Relasi (Edges)**: `:BERLOKASI_DI`, `:BERJENIS`, `:MEMILIKI_HARGA`, `:MENYAJIKAN`, `:MEMILIKI_FASILITAS`, `:MENDAPAT_SENTIMEN`.
2. **LLM Engine**: Menggunakan model **Qwen-Max** dari Alibaba Cloud (via DashScope) untuk 2 fungsi utama:
    - **Information Extraction**: Mengekstrak data tidak terstruktur (teks ulasan restoran) menjadi entitas terstruktur (menu, fasilitas, sentimen).
    - **Text-to-Cypher**: Menerjemahkan bahasa manusia (pertanyaan user) menjadi query database Cypher.
3. **Orkestrasi AI**: Menggunakan framework **LangChain** (`Neo4jGraph`, `GraphCypherQAChain`) untuk merangkai alur sistem tanya jawab.
4. **Alur Data**:
    - `data_restoran.csv` -> Dibaca oleh Pandas -> Diekstrak oleh LLM -> Disimpan ke Neo4j sebagai graf -> Ditanya/diquery oleh pengguna melalui Chatbot.

---

## 🛠️ Instalasi

1. Pastikan Anda sudah menginstal **Python 3.8+** di sistem.
2. Clone atau buka direktori proyek ini.
3. Install semua dependensi Python yang dibutuhkan melalui file `requirements.txt` dengan menjalankan:
   ```bash
   pip install -r requirements.txt
   ```
4. Pastikan Anda memiliki **Neo4j Database** yang sedang berjalan (bisa menggunakan Neo4j Desktop, Neo4j Community Server, atau Neo4j Desktop via Docker).

---

## ⚙️ Konfigurasi

Semua konfigurasi menggunakan file `.env`. 
Pastikan Anda memiliki file `.env` di dalam folder proyek dengan format berikut:

```env
# API Key untuk LLM Qwen (DashScope API)
DASHSCOPE_API_KEY=sk-xxxxxx

# API Key Google Maps/Places API
GOOGLE_MAPS_API_KEY=AIzaSyxxxxxx

# Konfigurasi Koneksi Neo4j Database
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password_neo4j_anda
```

*Catatan: Pastikan kredensial di atas valid sesuai dengan akun DashScope dan server Neo4j lokal Anda.*

---

## 🚀 Cara Menjalankan (Run)

Ada 3 langkah utama dalam menggunakan sistem ini:

### Langkah 1: Mengekstrak Data Tempat dan Ulasan
Untuk menarik ulasan dari Google Maps dan menyimpannya di file CSV.
Jalankan script berikut:
```bash
python extract_places.py
```

### Langkah 2: Membangun Graph Database (ETL)
Sebelum bisa bertanya ke chatbot, kita harus mengekstrak data restoran dari file CSV ke dalam graph database Neo4j.
Jalankan script berikut:
```bash
python build_graph.py
```
*Tunggu beberapa saat. Script ini akan memproses teks ulasan menggunakan LLM untuk menemukan Menu, Fasilitas, dan Sentimen, lalu menginjeksikannya ke dalam Neo4j.*

### Langkah 3: Menjalankan Chatbot Interaktif
Setelah database graph berhasil dibangun, jalankan agen chatbot AI interaktif di terminal:
```bash
python chatbot.py
```
Anda bisa mulai memberikan pertanyaan secara natural menggunakan bahasa Indonesia. 
**Contoh pertanyaan:**
- *"Sebutkan tempat makan di Keputih yang murah dan ada wifi!"*
- *"Ada rekomendasi makanan yang enak tapi harganya sedang?"*

*(Ketik `exit`, `quit`, atau `keluar` untuk mematikan chatbot).*
