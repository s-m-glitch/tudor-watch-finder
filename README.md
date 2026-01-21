# Tudor Watch Finder

A Python tool to find the **Tudor Ranger 36mm with beige domed dial** (ref: M79930-0007) at nearby retailers. It scrapes Tudor's official retailer list, filters by distance from your zip code, and uses Bland AI to make automated phone calls to check inventory.

## Features

- 🔍 Scrapes all 230+ Tudor retailers in the United States
- 📍 Filters retailers by distance from any US zip code
- 📞 Makes automated phone calls via Bland AI to check inventory
- 📊 Generates detailed inventory reports
- 🌐 Web interface for easy use

## Quick Start

### Option 1: Command Line

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/tudor-watch-finder.git
cd tudor-watch-finder

# Install dependencies
pip install -r requirements.txt

# List nearby retailers (no phone calls)
python main.py --zip 94117 --radius 50 --no-call

# Check inventory with phone calls
export BLAND_API_KEY='your-api-key-here'
python main.py --zip 94117 --radius 50 --max-calls 5
```

### Option 2: Web Interface (Local)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the web server
python api.py

# Open http://localhost:8000 in your browser
```

### Option 3: Deploy to Cloud

See [Deployment](#deployment) section below.

---

## Deployment

### Deploy to Railway (Recommended)

Railway offers better Python support than Vercel for this type of application.

1. Push code to GitHub (see below)
2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variable: `BLAND_API_KEY` = your key
6. Deploy!

```bash
# Push to GitHub first
git init
git add .
git commit -m "Initial commit"
gh repo create tudor-watch-finder --public --source=. --push
```

### Deploy to Vercel

Vercel has limited Python support, but can work for this app:

1. Install Vercel CLI: `npm i -g vercel`
2. Add your API key as a secret:
   ```bash
   vercel secrets add bland_api_key "your-api-key-here"
   ```
3. Deploy:
   ```bash
   vercel
   ```

### Deploy to Render

1. Push to GitHub
2. Go to [render.com](https://render.com)
3. New → Web Service → Connect your repo
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
6. Add env var: `BLAND_API_KEY`

---

## Push to GitHub

```bash
# Initialize git (if not already done)
cd tudor-watch-finder
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Tudor Watch Finder"

# Create GitHub repo and push (using GitHub CLI)
gh repo create tudor-watch-finder --public --source=. --push

# Or manually:
# 1. Create repo at github.com
# 2. Then run:
git remote add origin https://github.com/YOUR_USERNAME/tudor-watch-finder.git
git branch -M main
git push -u origin main
```

---

## CLI Usage

```
python main.py [OPTIONS]

Options:
  --zip, -z      Center zip code for search (default: 94117)
  --radius, -r   Search radius in miles (default: 50)
  --api-key, -k  Bland AI API key (or set BLAND_API_KEY env var)
  --no-call      Just list retailers, don't make phone calls
  --max-calls    Maximum number of calls to make
  --delay, -d    Delay between calls in seconds (default: 30)
  --refresh      Force refresh of retailer data from Tudor website
  --show-all     Show all retailers (not just first 10)
```

---

## File Structure

```
tudor-watch-finder/
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── config.py          # Configuration settings
├── scraper.py         # Tudor website scraper
├── filter.py          # Zip code distance filtering
├── phone_caller.py    # Bland AI integration
├── main.py            # CLI entry point
├── api.py             # FastAPI web server
├── static/
│   └── index.html     # Web interface
├── vercel.json        # Vercel deployment config
├── railway.json       # Railway deployment config
├── Procfile           # Heroku/Render config
├── .gitignore         # Git ignore patterns
├── retailers.json     # Cached retailer data (generated)
└── inventory_results.json  # Call results (generated)
```

---

## How It Works

1. **Scraping** (`scraper.py`): Fetches all US Tudor retailers from tudorwatch.com, extracting names, addresses, phone numbers, and coordinates.

2. **Filtering** (`filter.py`): Uses the Haversine formula to calculate distances from your zip code and filters to retailers within your specified radius.

3. **Calling** (`phone_caller.py`): Uses Bland AI to make phone calls asking about the specific watch. The AI:
   - Greets the store politely
   - Asks about the Tudor Ranger 36mm with beige dial
   - Inquires about waitlists or special orders if not in stock
   - Thanks them and ends the call

4. **Results**: Analyzes call transcripts to determine inventory status:
   - ✅ **In Stock** - Watch is available
   - ❌ **Out of Stock** - Watch not available
   - 📦 **Can Order** - Can be special ordered
   - 📋 **Waitlist** - Waitlist available
   - 📵 **No Answer** - Call not answered
   - ⚠️ **Failed** - Call failed

---

## Watch Details

- **Model**: Tudor Ranger
- **Reference**: M79930-0007
- **Case**: 36mm steel
- **Dial**: Beige domed
- **Price**: $3,775

---

## Bland AI Setup

1. Sign up at [bland.ai](https://bland.ai)
2. Get your API key from the dashboard
3. Set the environment variable:
   ```bash
   export BLAND_API_KEY='org_xxxxx'
   ```

---

## API Endpoints

When running the web server (`python api.py`):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/watch` | GET | Get watch info |
| `/api/search` | POST | Search retailers by zip |
| `/api/call` | POST | Start phone calls |
| `/api/call/{job_id}` | GET | Get call job status |
| `/api/health` | GET | Health check |

---

## Troubleshooting

**"Could not geocode zip code"**
- Make sure the zip code is a valid 5-digit US zip code

**"No retailers with phone numbers found"**
- Try increasing the search radius
- Some retailer pages may not have phone numbers listed

**Bland AI errors**
- Verify your API key is correct
- Check your Bland AI account has sufficient credits
- Ensure phone numbers are in correct format

**Vercel deployment issues**
- Vercel has a 10-second function timeout on free tier
- Consider Railway or Render for better Python support

---

## Legal Notice

This tool is for personal use only. Be respectful when making calls - don't spam stores. The 30-second delay between calls helps prevent overwhelming store staff.

## License

MIT License - Use at your own risk.
