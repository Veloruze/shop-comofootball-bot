import requests
import pandas as pd
import json
import re
from html import unescape

def clean_description(html_text):
    """Clean HTML description to readable text"""
    if not html_text:
        return ''
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    
    # Decode HTML entities
    text = unescape(text)
    
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text)
    
    # Remove style/script content if any
    text = re.sub(r'style\s*{[^}]*}', '', text)
    
    return text.strip()

def analyze_size_sequence(sizes):
    """Optimal size sequence detector"""
    return 'Yes' if is_sequential_optimal(sizes) else 'No'

def get_clothing_size_mapping():
    """Get standard clothing size to number mapping"""
    return {'XXXS': 1, 'XXS': 2, 'XS': 3, 'S': 4, 'M': 5, 'L': 6, 'XL': 7, 'XXL': 8, '2XL': 8, '3XL': 9, '4XL': 10}

def extract_number_from_size(size):
    """Extract comparable number from a single size string"""
    clothing_order = get_clothing_size_mapping()
    
    # Direct clothing size match
    if size in clothing_order:
        return clothing_order[size]
    
    # Handle slash formats
    if '/' in size:
        return _handle_slash_format(size, clothing_order)
    
    # Handle age ranges with 'A' suffix
    if size.endswith('A') and len(size) > 2:
        return _handle_age_format(size)
    
    # Extract first number from any other format
    matches = re.findall(r'\d+', size)
    if matches:
        return int(matches[0])
    
    return None

def _handle_slash_format(size, clothing_order):
    """Handle size formats like S/M, S/46, 36/37"""
    parts = size.split('/')
    if len(parts) != 2:
        return None
    
    clothing_part, number_part = parts
    
    # Both parts are clothing sizes (e.g., "S/M", "M/L")
    if clothing_part in clothing_order and number_part in clothing_order:
        return (clothing_order[clothing_part] + clothing_order[number_part]) / 2
    
    # Clothing + number format (e.g., "S/46")
    if clothing_part in clothing_order:
        matches = re.findall(r'\d+', number_part)
        return int(matches[0]) if matches else None
    
    # Regular slash format, take last number
    matches = re.findall(r'\d+', size)
    return int(matches[-1]) if matches else None

def _handle_age_format(size):
    """Handle age formats like 910A -> 9-10A, 1314 -> 13-14"""
    number_part = size[:-1]  # Remove 'A'
    
    if len(number_part) == 3 and number_part.isdigit():  # e.g., "910"
        return int(number_part[0])  # Return first digit (9)
    
    if len(number_part) == 4 and number_part.isdigit():  # e.g., "1314"
        return int(number_part[:2])  # Return first two digits (13)
    
    # Regular A format, extract first number
    matches = re.findall(r'\d+', size)
    return int(matches[0]) if matches else None

def is_sequential_optimal(sizes):
    """
    Optimized sequential detector - checks if sizes are in ascending order
    Returns True if sizes are sequential, False otherwise
    """
    if not sizes or len(sizes) <= 1:
        return False
    
    # Skip obvious non-sizes
    non_size_patterns = ['Default', 'Add Your Name/Number']
    if any(pattern in str(sizes) for pattern in non_size_patterns):
        return False
    
    # Clean and split sizes
    size_list = [s.strip() for s in sizes.split(',')] if isinstance(sizes, str) else sizes
    
    # Extract numbers from each size
    numbers = []
    for size in size_list:
        number = extract_number_from_size(size)
        if number is None:
            return False  # Unknown format
        numbers.append(number)
    
    # Check if all sizes were processed and are in ascending order
    return len(numbers) == len(size_list) and numbers == sorted(numbers)


def scrape_como_products(base_url):
    """Scrape ALL products from Como Football shop JSON API with pagination"""
    
    all_products = []
    page = 1
    
    while True:
        # Add pagination parameter
        url = f"{base_url}?page={page}&limit=250"
        print(f"Scraping page {page}...")
        
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Break if no more products
        if not data.get('products') or len(data['products']) == 0:
            break
        
        all_products.extend(data['products'])
        print(f"Found {len(data['products'])} products on page {page}")
        
        # Break if less than limit (last page)
        if len(data['products']) < 250:
            break
            
        page += 1
    
    print(f"Total products found: {len(all_products)}")
    
    # Extract product data
    products = []
    
    for product in all_products:
        # Get sizes from variants and detect size type
        sizes = []
        size_type = 'Default Title'  # Default value
        
        # Check product options to get size type
        for option in product.get('options', []):
            if option['name'] in ['Size', 'Taglia', 'Options', 'option']:
                size_type = option['name']
                break
        
        for variant in product['variants']:
            if variant['title'] != 'Default Title':
                sizes.append(variant['title'])
        
        # Join sizes with comma
        size_string = ','.join(sizes) if sizes else 'Default'
        
        # Analyze if sizes are sequential
        # If size is "Default" or customization product, set to "-"
        exclude_keywords = ['Add Your Name/Number', 'Add name/number', 'Choose a player', 'Choose a Patch']
        is_customization = any(keyword.lower() in product['title'].lower() for keyword in exclude_keywords)
        
        if size_string == 'Default' or is_customization:
            size_sequential = '-'
        else:
            size_sequential = analyze_size_sequence(sizes)
        
        # Get pricing info from first variant
        first_variant = product['variants'][0]
        current_price = float(first_variant['price'])
        compare_price_raw = first_variant.get('compare_at_price')
        compare_price = float(compare_price_raw) if compare_price_raw and compare_price_raw != "0.00" else 0
        
        # Calculate discount if compare_price exists
        has_discount = compare_price > current_price
        discount_amount = compare_price - current_price if has_discount else 0
        discount_percent = (discount_amount / compare_price * 100) if has_discount else 0
        
        # Extract product info
        product_data = {
            'product_id': product['id'],
            'title': product['title'],
            'current_price': f"€{current_price:.2f}",
            'original_price': f"€{compare_price:.2f}" if compare_price > 0 else "-",
            'discount_amount': f"€{discount_amount:.2f}" if has_discount else "-",
            'discount_percent': f"{discount_percent:.1f}%" if has_discount else "-",
            'handle': product['handle'],
            'size_type': size_type,
            'size': size_string,
            'size_sequential': size_sequential,
            'description': clean_description(product.get('body_html', ''))
        }
        
        products.append(product_data)
    
    return pd.DataFrame(products)


