import json
 
MULTIPLIER = 2.5  # basic -> medium -> premium

BASE_PRODUCTS = {
    "breakfast": {
        "ham": {
            "basic_name": "Regular Ham",
            "medium_name": "Black Forest Ham",
            "premium_name": "24-Month Aged Parma Ham",
            "base_price": 8.99,
            "calories": 150,
            "category": "meat",
        },
        "cheese": {
            "basic_name": "Gouda Cheese",
            "medium_name": "Aged Cheddar",
            "premium_name": "36-Month Aged Comte",
            "base_price": 12.99,
            "calories": 350,
            "category": "dairy",
        },
        "bread": {
            "basic_name": "White Bread Roll",
            "medium_name": "Multigrain Bread",
            "premium_name": "Freshly Baked Sourdough",
            "base_price": 2.99,
            "calories": 210,
            "category": "bread",
        },
    },
    "lunch": {
        "soup": {
            "basic_name": "Canned Tomato Soup",
            "medium_name": "Homemade Vegetable Soup",
            "premium_name": "Homestyle Lobster Bisque",
            "base_price": 2.99,
            "calories": 220,
            "category": "soup",
        },
        "sandwich": {
            "basic_name": "White Bread Sandwich with Margarine",
            "medium_name": "Whole Grain Turkey Sandwich",
            "premium_name": "Ciabatta with Prosciutto and Truffle Spread",
            "base_price": 3.99,
            "calories": 380,
            "category": "sandwich",
        },
        "drink": {
            "basic_name": "Tap Water Bottle",
            "medium_name": "Fresh Orange Juice",
            "premium_name": "Sparkling San Pellegrino with Lemon",
            "base_price": 1.49,
            "calories": 5,
            "category": "drink",
        },
    },
    "dinner": {
        "chicken": {
            "basic_name": "Chicken from Market",
            "medium_name": "Corn-Fed Chicken",
            "premium_name": "Free-Range Yellow Chicken",
            "base_price": 11.99,
            "calories": 500,
            "category": "meat",
        },
        "rice": {
            "basic_name": "White Rice",
            "medium_name": "Basmati Rice",
            "premium_name": "Kinmemai Premium Rice",
            "base_price": 4.99,
            "calories": 200,
            "category": "rice",
        },
        "vegetables": {
            "basic_name": "Frozen Vegetables Mix",
            "medium_name": "Fresh Local Vegetables",
            "premium_name": "Fresh Farm Vegetables (No Pesticides)",
            "base_price": 12.99,
            "calories": 100,
            "category": "vegetables",
        },
    },
}
 
TIERS = ["basic", "medium", "premium"]
def build_products():
    products = {}
    for meal_type, items in BASE_PRODUCTS.items():
        products[meal_type] = {}
        for item_key, spec in items.items():
            base_price = spec["base_price"]
            for i, tier in enumerate(TIERS):
                price = round(base_price * (MULTIPLIER ** i), 2)
                key = f"{item_key}_{tier}"
                products[meal_type][key] = {
                    "name": spec[f"{tier}_name"],
                    "price": price,
                    "quality": tier,
                    "calories": spec["calories"],
                    "category": spec["category"],
                    "meal_type": meal_type,
                }
    return products

if __name__ == "__main__":
   PRODUCTS = build_products()

   with open("data/exp_01/products.json", "w", encoding="utf-8") as f:
        json.dump(PRODUCTS, f, indent=4, ensure_ascii=False)
