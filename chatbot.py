import os
import dashscope
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_community.llms import Tongyi
from langchain_core.prompts import PromptTemplate

# Load environment variables
load_dotenv(override=True)

class GraphRAGPipeline:
    def __init__(self):
        # 1. Hubungkan ke Neo4j via LangChain Neo4jGraph
        self.graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USER"),
            password=os.getenv("NEO4J_PASSWORD"),
            enhanced_schema=False
        )
        
        # Refresh schema agar LangChain tahu tentang 7 Entitas (TempatMakan, Menu, Daerah, Fasilitas, dll)
        self.graph.refresh_schema()
        
        # 2. Inisialisasi LLM
        dashscope.base_http_api_url = 'https://ws-qhebnre9dgsdfa13.ap-southeast-1.maas.aliyuncs.com/api/v1'
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
        
        # LLM untuk generate Cypher (temperature=0 agar logis dan tidak berhalusinasi sintaks)
        self.cypher_llm = Tongyi(
            model="qwen-max", 
            temperature=0.0, 
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        
        self.qa_llm = Tongyi(
            model="qwen-max", 
            temperature=0.1, 
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        
        # 3. Custom Prompt untuk Cypher Generation
        cypher_template = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Schema:
{schema}

Note:
- The graph has TempatMakan, Daerah, Kategori, PriceLevel, Menu, Fasilitas, Sentimen.
- If asking about 'murah' or 'mahal', check (w:TempatMakan)-[:MEMILIKI_HARGA]->(p:PriceLevel).
- If asking about 'wifi', 'nyaman', check (w:TempatMakan)-[:MEMILIKI_FASILITAS]->(f:Fasilitas).
- If asking about location, check (w:TempatMakan)-[:BERLOKASI_DI]->(d:Daerah).
- If asking about 'enak' or 'lezat', do NOT search for 'enak' in Sentimen. Just rely on ORDER BY Rating DESC.
- Sentimen ONLY contains 'Positif', 'Negatif', or 'Netral'. If needed, check (w:TempatMakan)-[:MENDAPAT_SENTIMEN]->(s:Sentimen) WHERE s.nama = 'Positif'.
- CRITICAL: Always use case-insensitive CONTAINS for text search instead of exact equals (e.g. WHERE toLower(m.nama) CONTAINS 'ayam').
- CRITICAL: NEVER use pattern matching inside functions like toLower() or in WHERE conditions directly. Always MATCH the node first and check its property (e.g. `MATCH (w)-[:MENDAPAT_SENTIMEN]->(s:Sentimen) WHERE toLower(s.nama) CONTAINS 'positif'`).
- CRITICAL: DO NOT just return the TempatMakan name! You MUST return rich details so the AI can answer nicely. 
  Always end your query with something like:
  OPTIONAL MATCH (w)-[:MENYAJIKAN]->(m:Menu)
  OPTIONAL MATCH (w)-[:MEMILIKI_FASILITAS]->(f:Fasilitas)
  RETURN w.nama AS Nama, w.rating AS Rating, w.rating_count AS Ulasan, collect(DISTINCT m.nama)[..5] AS Menu, collect(DISTINCT f.nama)[..5] AS Fasilitas
  ORDER BY Rating DESC LIMIT 5
- CRITICAL: In ORDER BY, you MUST use the exact alias from RETURN (e.g., `ORDER BY Rating DESC LIMIT 5`). DO NOT use `w.Rating` or `w.rating`.
- Be flexible! If multiple conditions are too strict, use OR.

Question: {question}
Cypher query:"""
        
        cypher_prompt = PromptTemplate(
            input_variables=["schema", "question"],
            template=cypher_template
        )
        
        # Custom Prompt untuk Answering (Agar bahasa Indonesia)
        qa_template = """Kamu adalah 'Local Food Discovery Graph', asisten AI rekomendasi kuliner yang sangat ramah.
Gunakan informasi dari database kuliner berikut untuk menjawab pertanyaan pengguna HANYA dalam Bahasa Indonesia yang luwes dan natural (hindari bahasa baku kaku).
Jika data/konteks kosong, katakan dengan sopan bahwa kamu tidak menemukan kriteria yang persis seperti itu di database saat ini. Jangan pernah menjawab menggunakan Bahasa Inggris.

Data dari Database:
{context}

Pertanyaan Pengguna: {question}
Jawaban (Bahasa Indonesia):"""
        
        qa_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=qa_template
        )
        
        # 4. Inisialisasi GraphCypherQAChain (Text-to-Cypher)
        self.qa_chain = GraphCypherQAChain.from_llm(
            cypher_llm=self.cypher_llm,
            qa_llm=self.qa_llm,
            graph=self.graph,
            verbose=True, # Agar kita bisa lihat Cypher yang di-generate di terminal
            cypher_prompt=cypher_prompt,
            qa_prompt=qa_prompt,
            return_intermediate_steps=False,
            allow_dangerous_requests=True # Wajib ada di LangChain terbaru untuk mengeksekusi Cypher otomatis
        )

    def ask(self, question):
        print("\n[Local Food Discovery Graph] Menerjemahkan ke Cypher & mencari data...")
        try:
            # invoke dari GraphCypherQAChain menerima dict dengan key 'query'
            response = self.qa_chain.invoke({"query": question})
            return response.get("result", "Maaf, saya tidak menemukan jawabannya.")
        except Exception as e:
            return f"Maaf, terjadi kesalahan saat memproses query ke database: {str(e)}"

if __name__ == "__main__":
    print("=== Menginisialisasi Local Food Discovery Graph (Text-to-Cypher) ===")
    chatbot = GraphRAGPipeline()
    print("Sistem siap! Silakan tanya seputar kuliner (contoh: 'Tempat makan di Keputih yang murah dan ada wifi').")
    
    try:
        while True:
            user_input = input("\nAnda: ")
            if user_input.lower() in ['exit', 'quit', 'keluar']:
                print("Terima kasih telah menggunakan Local Food Discovery Graph!")
                break
                
            jawaban = chatbot.ask(user_input)
            print(f"Bot : {jawaban}")
    except KeyboardInterrupt:
        print("\nTerima kasih telah menggunakan Local Food Discovery Graph!")
