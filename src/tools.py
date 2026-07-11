tools = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Browse available products in the store for a specific meal. Always call this first before making any purchases.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meal_type": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner"],
                        "description": "The meal to shop for"
                    }
                },
                "required": ["meal_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get full details including price for a specific product. Call this before deciding to add to cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID from search results, e.g. ham_basic, cheese_premium"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_purchase_history",
            "description": "Get customer's previous purchases. Call this to understand customer preferences, use this first.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "Add a product to the shopping cart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID to add"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of units to add, usually 1"
                    }
                },
                "required": ["product_id", "quantity"]
            }
        }
        }
]