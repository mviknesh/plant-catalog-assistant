from google.cloud import firestore

FIRESTORE_PROJECT = "qwiklabs-gcp-01-9657f097aca6"

def seed_database():
    db = firestore.Client(project=FIRESTORE_PROJECT)
    items = [
        {
            "id": "monstera-deliciosa",
            "name": "Monstera Deliciosa",
            "category": "Indoor Plants",
            "price": 29.99,
            "stock": 15,
            "description": "Popular tropical plant with striking split leaves."
        },
        {
            "id": "fiddle-leaf-fig",
            "name": "Fiddle Leaf Fig",
            "category": "Indoor Plants",
            "price": 45.00,
            "stock": 8,
            "description": "Elegant indoor tree featuring large violin-shaped leaves."
        },
        {
            "id": "snake-plant",
            "name": "Snake Plant",
            "category": "Low Maintenance",
            "price": 19.99,
            "stock": 25,
            "description": "Hardy air-purifying plant tolerant of low light."
        },
        {
            "id": "peace-lily",
            "name": "Peace Lily",
            "category": "Flowering Plants",
            "price": 24.50,
            "stock": 10,
            "description": "Beautiful indoor plant with lush leaves and white blooms."
        }
    ]

    for item in items:
        db.collection("items").document(item["id"]).set(item)
        print(f"Seeded document: {item['id']}")

if __name__ == "__main__":
    seed_database()
