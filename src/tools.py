import json 

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Browse available products in the store for a specific meal",
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
            "description": "Get customer's previous purchases.",
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
def load_products(path="data/exp_01/products.json"):
    """Call this ONCE at the start of your script, not inside handle_tool_call."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
 

def handle_tool(tool,cart,history,products):

    tool_name = tool["name"]
    tool_args = tool.get("arguments", {})

    if tool_name == "search_products":
        meal_type = tool_args.get("meal_type")
        if meal_type not in products:
            print(f"[WARN] search_products called with invalid meal_type, args={tool_args}")
            return {"error": f"invalid or missing meal_type, must be one of {list(products.keys())}"}
        meals = products[meal_type]
        available_list = []

        for product_id, product_desc in meals.items():
            available_list.append({"product_id": product_id, "product_name": product_desc["name"]})    

        return available_list
    
    elif tool_name == "get_product_details":
        product_id = tool_args.get("product_id")
        if not product_id:
            print(f"[WARN] get_product_details called with missing product_id, args={tool_args}")
            return {"error": "missing required argument 'product_id'"}
        
        for meal_type, meals in products.items():
            if product_id in meals:
                return meals[product_id]
        return {f"error: product {product_id} not found"}

    elif tool_name == "get_purchase_history":
        return history 

    elif tool_name == "add_to_cart":
        product_id = tool_args.get("product_id")
        if not product_id:
            print(f"[WARN] add_to_cart called with missing product_id, args={tool_args}")
            return {"error": "missing required argument 'product_id', item NOT added to cart"}
        
        quantity = tool_args.get("quantity", 1) 

        product_info = None
        for meal_type, meal_products in products.items():
            if product_id in meal_products:
                product_info = meal_products[product_id]
                break
 
        if product_info is None:
            return {"error": f"product_id '{product_id}' not found, not added to cart"}
 
        cart.append({
            "product_id": product_id,
            "name": product_info["name"],
            "quantity": quantity,
            "price": product_info["price"],
            "quality": product_info["quality"],
        })
        return {
            "status": "added",
            "product_id": product_id,
            "quantity": quantity,
            "price": product_info["price"],
        }

    else:
        return {"error": f"unknown tool {tool_name}"}