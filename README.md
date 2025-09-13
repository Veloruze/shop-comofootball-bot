# Como 1907 Football Shop Bot 🏟️

Telegram bot untuk monitoring Como 1907 football shop dengan automatic notifications untuk new products, size changes, dan discounts.

## Features ✨

### 🤖 Telegram Bot Commands
- `/start` - Welcome message + command overview
- `/help` - Detailed command explanations
- `/sizesequence` - Show products dengan size tidak urut
- `/sizetype` - Show products dengan size type "option"
- `/refresh` - Manual update data + detect changes
- `/subscribe` - Subscribe untuk auto-notifications
- `/unsubscribe` - Stop notifications

### 🔔 Auto-Notification System
- **Auto-refresh**: Setiap 1 jam
- **Change detection**: Compare dengan data sebelumnya
- **Smart notifications**: Hanya kirim kalau ada changes
- **Notification types**:
  - 🆕 New products added
  - 📐 Size sequence changes (fixed/broken)
  - 💰 New discounts available

### 📊 Advanced Size Sequence Detection
- **Smart parsing**: Handle berbagai format size
- **Clothing sizes**: XS, S, M, L, XL, XXL, 2XL, 3XL
- **Numeric ranges**: 36/37, 38/39, 40/41
- **Age formats**: 5-6A, 7-8A, 910A, 1314
- **Mixed formats**: S/46, M/48, L/50
- **Combinations**: S/M, M/L, L/XL

## Installation 🚀

### Requirements
```bash
pip install -r requirements.txt
```

### Setup
1. Clone repository
2. Install dependencies
3. Setup Telegram Bot Token
4. Run bot

### Telegram Bot Setup
1. Chat dengan @BotFather di Telegram
2. Create new bot: `/newbot`
3. Get bot token
4. Update token di `como_telegram_bot.py`

## Usage 📱

### Start Bot
```bash
python como_telegram_bot.py
```

### Manual Scraping
```bash
python scrape_como.py
```

## Data Structure 📋

### CSV Output (11 columns)
- `product_id` - Unique product identifier
- `title` - Product name
- `current_price` - Current selling price (€X.XX)
- `original_price` - Original price before discount
- `discount_amount` - Discount amount (€X.XX)
- `discount_percent` - Discount percentage (X.X%)
- `handle` - URL slug
- `size_type` - Size option type (Taglia/option/Default Title)
- `size` - Available sizes (comma-separated)
- `size_sequential` - Size sequence status (Yes/No/-)
- `description` - Cleaned product description

### Storage Management
- **History files**: Auto-delete, keep only 2 most recent
- **Subscriber data**: Persistent JSON storage
- **Main data**: Always fresh CSV export

## Architecture 🏗️

### Components
1. **Scraper** (`scrape_como.py`) - Data extraction engine
2. **Bot** (`como_telegram_bot.py`) - User interface + notifications
3. **Auto-refresh** - Background monitoring system
4. **Change detection** - Compare current vs previous data

### Data Flow
```
Como Shop API → Scraper → CSV Data → Change Detection → Notifications → Users
```

## Examples 📖

### Size Sequence Detection
```python
# Sequential
"XS,S,M,L,XL" → "Yes"
"36/37,38/39,40/41" → "Yes"
"5-6A,7-8A,910A" → "Yes"

# Non-sequential  
"XS,XXS,XXXS" → "No" (descending)
"S,L,M,XL" → "No" (wrong order)
"S/46,L/48" → "No" (missing M)

# Not applicable
"Default" → "-"
"Add name/number" → "-"
```

### Notification Example
```
🔔 Auto-Update Notification

🆕 New Products (2 found)
• Como 1907 Away Jersey - €75.00
• Training Shorts - €29.90

💰 New Discounts (1 found)  
• Como 1907 Home Jersey
  €39.95 (was €79.90) - 50.0%
```

## API Reference 🔗

**Data Source**: https://shop.comofootball.com/products.json
- Shopify JSON API
- Pagination support
- 343+ products total

## Contributing 🤝

1. Fork repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## License 📄

MIT License - Feel free to use and modify

---

**Built with ❤️ for Como 1907 fans**
