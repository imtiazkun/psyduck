# Psyduck

```
        ⠀⠀⠀⠀⠀⠀⠀⠀⣤⡀⠀⣶⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠙⣿⣆⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠸⣷⣮⣿⣿⣄⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀                   Psyduck v0.1
        ⠀⠀⠀⠀⠀⢀⡠⠒⠉⠀⠀⠀⠀⠀⠀⠈⠁⠲⢖⠒⡀⠀⠀                   AI OSINT TOOL FOR YOU & I
        ⠀⠀⠀⡠⠴⣏⠀⢀⡀⠀⢀⡀⠀⠀⠀⡀⠀⠀⡀⠱⡈⢄⠀                   AUTHOR: @imtiazkun
        ⠀⠀⢠⠁⠀⢸⠐⠁⠀⠄⠀⢸⠀⠀⢎⠀⠂⠀⠈⡄⢡⠀⢣                   
        ⠀⢀⠂⠀⠀⢸⠈⠢⠤⠤⠐⢁⠄⠒⠢⢁⣂⡐⠊⠀⡄⠀⠸                   
        ⠀⡘⠀⠀⠀⢸⠀⢠⠐⠒⠈⠀⠀⠀⠀⠀⠀⠈⢆⠜⠀⠀⢸                   
        ⠀⡇⠀⠀⠀⠀⡗⢺⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠑⡄⢀⠎
        ⠀⢃⠀⠀⠀⢀⠃⢠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠷⡃⠀
        ⠀⠈⠢⣤⠀⠈⠀⠀⠑⠠⠤⣀⣀⣀⣀⣀⡀⠤⠒⠁⠀⢡⠀
        ⡀⣀⠀⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢘⠀
        ⠑⢄⠉⢳⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡸⠀
        ⠀⠀⠑⠢⢱⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡴⠁⠀                   "Uwuwu" 
        ⠀⠀⠀⠀⢀⠠⠓⠢⠤⣀⣀⡀⠀⠀⣀⣀⡀⠤⠒⠑⢄⠀⠀                   - imtiazkun
        ⠀⠀⠀⠰⠥⠤⢄⢀⡠⠄⡈⡀⠀⠀⣇⣀⠠⢄⠀⠒⠤⠣⠀
        ⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀
```


A modular CLI tool for AI-powered OSINT (Open Source Intelligence) and sentiment analysis. Features vision-enhanced web scraping, social media data extraction, and comprehensive data analysis capabilities.

## Features

- **Vision-Enhanced Scraping**: Uses OpenAI GPT-4o-mini vision to intelligently extract data from web pages
- **Multi-Engine Web Search**: Scrape search results from DuckDuckGo, Google, and Bing
- **OCR Text Extraction**: Extract text from images using Tesseract OCR
- **Plugin Architecture**: Modular system with dynamic plugin loading
- **Interactive CLI**: Styled command-line interface with visual effects
- **OpenAI Integration**: Built-in support for OpenAI API with model management
- **Persistent Sessions**: Save browser sessions to avoid repeated logins
- **CSV Export**: Structured data export with comprehensive metadata

## Installation

1. Clone or download the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your OpenAI API key:
   ```bash
   # Create .env file and add your OpenAI API key
   echo "OPENAI_API_KEY=your_actual_api_key_here" > .env
   ```
4. Install browser dependencies:
   ```bash
   python -m playwright install chromium
   ```
5. Make the script executable:
   ```bash
   chmod +x psyduck.py
   ```

## Usage

### DeepScrape (Vision-Enhanced, Depth-Controlled)

Depth-configurable cross-platform scraping and analysis. Uses OpenAI to interpret platforms and depth intent, then performs vision-assisted scraping.

Command:
```bash
python psyduck.py deepscrape "<TOPIC or SEARCH TERM>" --results=<NUMBER> --platforms="<STRING>" --depth=<0|1|2|3> --timeout=<NUMBER>
```

Example:
```bash
python psyduck.py deepscrape "ocean diversity" --results=10 --platforms="blogs & social media" --depth=0 --timeout=3600
```

Depth semantics:
- 0: collect links only
- 1: add page title/author/date/summary
- 2: if present, include comments/discussion text
- 3: include comment metadata (author/time/likes) when visible

Output CSV (superset): `search_term, url, title, author, date, publisher, rank, excerpt, summary, has_comments, comments, scraped_at`

Natural-language instruction support:
- The first quoted argument can be a plain term or an instruction.
- Example:
```bash
python psyduck.py deepscrape "Collect everything you can find about Imtiaz Al Shariar" \
  --results=10 --platforms="any" --depth=1 --timeout=3600
```
This will aim for 10 mentions across any platforms (social/blog/video, etc.) and output a descriptive list (depth 1) about that person.

### Web Search Scraper (Vision-Enhanced)

Scrape search results from DuckDuckGo, Google, or Bing using AI vision analysis.

**Command:**
```bash
python psyduck.py webscrape "<SEARCH TERM>" <LIMIT> --location=<duckduckgo|google|bing>
```

**Examples:**
```bash
# Search DuckDuckGo
python psyduck.py webscrape "AI is getting scary" 10 --location=duckduckgo

# Search Google News
python psyduck.py webscrape "climate change" 20 --location=google

# Search Bing
python psyduck.py webscrape "tech news" 15 --location=bing
```

**Features:**
- **Multi-Engine Support**: DuckDuckGo, Google, Bing
- **Vision Analysis**: Uses GPT-4o-mini to extract structured data
- **Rich Metadata**: Title, URL, excerpt, publisher, date, rank
- **Persistent Sessions**: Saves browser state

**Output CSV columns:**
- `search_term`, `engine`, `rank`, `title`, `url`, `excerpt`, `publisher`, `date`, `scraped_at`

## Data Storage

All scraped data is saved to the `data/` directory:
- `data/webscrape_<engine>_<term>.csv` - Web search results
- `data/webscrape_user/` - Persistent web scraping browser session

## Cost Tracking

The tool tracks OpenAI API usage and displays:
- Token usage per operation (prompt + completion tokens)
- Estimated cost based on GPT-4o-mini pricing ($0.00015 per 1K tokens)
- Running totals during scraping sessions
- Average cost per post/result

### Interactive Mode (Default)
```bash
python3 psyduck.py
# or
./psyduck.py
```

### Direct Commands
```bash
# System commands
python3 psyduck.py version           # Show version information
python3 psyduck.py --help           # Show help

# Plugin commands (require OpenAI API key)
python3 psyduck.py models           # List available OpenAI models
python3 psyduck.py test-openai      # Test OpenAI API connection
python3 psyduck.py model-info gpt-4 # Get info about specific model

# Scraping commands (require OpenAI API key + browser)
python3 psyduck.py webscrape "AI news" 10 --location=duckduckgo
```

## Available Commands (Interactive Mode)

### System Commands
- `help` - Show command menu
- `exit` - Exit the application

### Plugin Commands

#### Version Plugin
- `version` - Show version information

#### Models Plugin (OpenAI)
- `models` - List all available OpenAI models
- `test-openai` - Test OpenAI API connection
- `model-info [model_name]` - Get detailed information about a specific model

#### DeepScrape Plugin
- `deepscrape "<TOPIC>" --results=<N> --platforms="<STRING>" --depth=<0|1|2|3> --timeout=<S>` - Depth-controlled scraping

#### Webscrape Plugin  
- `webscrape "<SEARCH TERM>" <LIMIT> --location=<duckduckgo|google|bing>` - Scrape search results

## Plugin System

### Creating Plugins
Plugins are located in the `plugin/` directory. Each plugin should have:
- A folder with the plugin name
- `main.py` file containing the plugin logic
- `PLUGIN_INFO` dictionary defining commands and metadata

### Plugin Structure
```python
PLUGIN_INFO = {
    'name': 'plugin_name',
    'description': 'Plugin description',
    'version': '1.0.0',
    'commands': {
        'command_name': {
            'handler': command_function,
            'description': 'Command description',
            'usage': 'command_name [args]'
        }
    }
}
```

### OpenAI Integration
The models plugin provides comprehensive OpenAI API integration:
- **Model Discovery**: Browse all available models
- **Model Information**: Get detailed specs for specific models
- **Connection Testing**: Verify API key and connectivity
- **Categorized Display**: Separate GPT, embedding, and other models

## Requirements

- Python 3.6+
- OpenAI API key
- Chromium browser (installed via Playwright)
- Dependencies: `openai>=1.0.0`, `python-dotenv>=1.0.0`, `playwright>=1.46.0`, `pillow>=10.0.0`, `pytesseract>=0.3.10`

## Examples

### Testing OpenAI Connection
```bash
python3 psyduck.py test-openai
```

### Listing Available Models
```bash
python3 psyduck.py models
```

### Getting Model Information
```bash
python3 psyduck.py model-info gpt-4
python3 psyduck.py model-info gpt-4o-mini
```

### Web Search Scraping
```bash
# Search DuckDuckGo
python3 psyduck.py webscrape "AI news" 10 --location=duckduckgo

# Search Google News
python3 psyduck.py webscrape "climate change" 15 --location=google
```

### Interactive Session
```bash
python3 psyduck.py
psyduck> models
psyduck> test-openai
psyduck> version
psyduck> fb-scrape "https://web.facebook.com/hashtag/python" 10
psyduck> exit
```

## License

This project is open source and available under the GPL3 License.