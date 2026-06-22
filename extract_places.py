import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def get_restaurants():
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        # FieldMask untuk mengambil variabel tambahan
        "X-Goog-FieldMask": "places.displayName,places.rating,places.reviews,places.priceLevel,places.primaryType,places.userRatingCount,places.addressComponents"
    }
    
    queries = [
        "Tempat makan di Kampus ITS Surabaya",
        "Tempat makan di Keputih Surabaya",
        "Cafe Kampus ITS Surabaya",
        "Restoran daerah ITS Surabaya",
        "Tempat Makan daerah ITS Surabaya",
        "Tempat makan di Gebang Surabaya",
        "Tempat makan di Mulyosari Surabaya",
        "Tempat makan di Kejawan Surabaya",
        "Tempat makan di Sukolilo Surabaya" 
    ]
    
    places_data = []
    
    for q in queries:
        print(f"Mencari: {q}")
        next_page_token = None
        # Loop maksimal 3 halaman per query (karena batas API Google adalah ~60 hasil per query)
        for page in range(3):
            payload = {
                "textQuery": q,
                "languageCode": "id"  # Ekstrak dalam bahasa Indonesia
            }
            if next_page_token:
                payload["pageToken"] = next_page_token
                
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"Error {response.status_code}: {response.text}")
                break
                
            data = response.json()
            places = data.get("places", [])
            places_data.extend(places)
            
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
                
    # Hapus duplikat berdasarkan nama tempat makan
    unique_places = {}
    for p in places_data:
        nama = p.get("displayName", {}).get("text", "")
        if nama and nama not in unique_places:
            unique_places[nama] = p
            
    final_places = list(unique_places.values())
    
    # Batasi hingga 100 tempat unik
    if len(final_places) > 100:
        final_places = final_places[:100]
        
    print(f"\nBerhasil mendapatkan {len(final_places)} tempat makan unik.")
    return final_places

def extract_and_save_data(places_data, output_file="data_restoran.csv"):
    extracted_data = []
    
    price_map = {
        "PRICE_LEVEL_FREE": "Gratis",
        "PRICE_LEVEL_INEXPENSIVE": "Murah",
        "PRICE_LEVEL_MODERATE": "Sedang",
        "PRICE_LEVEL_EXPENSIVE": "Mahal",
        "PRICE_LEVEL_VERY_EXPENSIVE": "Sangat Mahal"
    }
    
    for place in places_data:
        nama_tempat_makan = place.get("displayName", {}).get("text", "Unknown")
        rating = place.get("rating", 0.0)
        rating_count = place.get("userRatingCount", 0)
        kategori = place.get("primaryType", "Unknown")
        
        price_level_raw = place.get("priceLevel", "")
        price_level = price_map.get(price_level_raw, "Tidak Diketahui")
        
        # --- FILTERING KETAT UNTUK TEMPAT MAKAN ---
        kategori_lower = kategori.lower()
        nama_tempat_makan_lower = nama_tempat_makan.lower()
        
        # 1. Pastikan membuang yang jelas BUKAN tempat makan
        exclude_types = [
            "university", "mosque", "school", "hospital", "doctor", "dentist",
            "government_office", "local_government_office", "bank", "atm",
            "lodging", "hotel", "motel", "museum", "park", "tourist_attraction",
            "car_repair", "car_wash", "gas_station", "parking", "service",
            "hair_care", "beauty_salon", "pharmacy", "gym", "laundry",
            "book_store", "clothing_store", "furniture_store", "electronics_store",
            "hardware_store", "jewelry_store", "shoe_store", "place_of_worship",
            "church", "hindu_temple", "synagogue", "transit_station", "bus_station",
            "train_station", "airport", "subway_station", "post_office",
            "lawyer", "accounting", "real_estate_agency", "travel_agency",
            "police", "fire_station", "cemetery", "court", "auditorium", "library",
            "supermarket", "convenience_store", "grocery_store"
        ]
        
        if kategori_lower in exclude_types:
            continue
            
        # 2. Cek apakah ini benar-benar tempat makan via Tipe Kategori
        valid_types = [
            "restaurant", "cafe", "coffee_shop", "bakery", "food_court", 
            "meal_takeaway", "meal_delivery", "ice_cream_shop", "juice_shop",
            "indonesian_restaurant", "diner", "fast_food_restaurant"
        ]
        is_valid_type = kategori_lower in valid_types
        
        # 3. Atau cek dari namanya (jika kategorinya "store" atau "point_of_interest")
        food_keywords = ["warung", "resto", "makan", "kopi", "cafe", "kedai", "bakso", "mie", "soto", "penyet", "nasi", "ayam", "bebek", "seafood", "depot", "satay", "sate"]
        has_food_keyword = any(kw in nama_tempat_makan_lower for kw in food_keywords)
        
        if not (is_valid_type or has_food_keyword):
            continue
            
        # --- EKSTRAKSI DAERAH / KELURAHAN ---
        daerah = "Unknown"
        address_components = place.get("addressComponents", [])
        
        # Prioritas: Kelurahan (level_4 / sublocality_1) -> Kecamatan (level_3) -> Neighborhood -> Locality
        for comp in address_components:
            types = comp.get("types", [])
            if "administrative_area_level_4" in types or "sublocality_level_1" in types:
                daerah = comp.get("longText", "")
                break # Kelurahan adalah tingkat paling relevan, langsung stop
            elif "administrative_area_level_3" in types and daerah == "Unknown":
                daerah = comp.get("longText", "")
            elif "neighborhood" in types and daerah == "Unknown":
                daerah = comp.get("longText", "")
            elif "locality" in types and daerah == "Unknown":
                daerah = comp.get("longText", "")
        
        reviews = place.get("reviews", [])
        
        for review in reviews:
            review_text = review.get("text", {}).get("text", "").strip()
            if not review_text:
                continue
                
            extracted_data.append({
                "nama_tempat_makan": nama_tempat_makan,
                "daerah": daerah,
                "kategori": kategori,
                "price_level": price_level,
                "rating": rating,
                "rating_count": rating_count,
                "contents": review_text
            })
            
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"[SUCCESS] Data berhasil disimpan ke {output_file}.")
        print(f"Total: {len(extracted_data)} ulasan diekstrak.")
    else:
        print("[WARNING] Tidak ada ulasan yang bisa diekstrak.")

if __name__ == "__main__":
    print("Mulai ekstraksi data yang diperluas...")
    places = get_restaurants()
    if places:
        extract_and_save_data(places)