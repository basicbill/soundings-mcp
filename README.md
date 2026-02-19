
# soundings-mcp 🛰️

A Model Context Protocol (MCP) server for fetching, analyzing, and visualizing RAOB (Rawinsonde Observation) upper-air sounding data.

## Features
- **Station Search**: Find the nearest balloon launch site by city name or GPS coordinates.
- **Thermodynamic Analysis**: Automated calculation of SBCAPE, SBCIN, and LCL heights using MetPy.
- **Skew-T Visuals**: Generates full Log-P diagrams with temperature, dewpoint, and parcel paths.
- **Wind Analysis**: Generates Hodographs color-coded by height to analyze vertical wind shear.
- **Cloud Integration**: Automatically uploads plots to S3-compatible storage for easy sharing with LLMs.

## Prerequisites
- **Python 3.10+**
- **S3-Compatible Storage**: AWS S3, Cloudflare R2, or Backblaze B2.
- **Railway Account**: For cloud hosting (supports SSE transport).

## Environment Variables
Configure these in your Railway dashboard:
- `S3_BUCKET_NAME`: Your bucket name.
- `S3_ENDPOINT_URL`: Your S3 endpoint (e.g., https://s3.amazonaws.com).
- `AWS_ACCESS_KEY_ID`: Your access key.
- `AWS_SECRET_ACCESS_KEY`: Your secret key.

## Installation (Local Development)
1. Clone the repo: `git clone https://github.com/your-username/soundings-mcp.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run locally: `python main.py`

## Usage with Claude Desktop
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "soundings": {
      "type": "sse",
      "url": "[https://your-railway-app-url.up.railway.app/sse](https://your-railway-app-url.up.railway.app/sse)"
    }
  }
}# soundings-mcp 🛰️

A Model Context Protocol (MCP) server for fetching, analyzing, and visualizing RAOB (Rawinsonde Observation) upper-air sounding data.

## Features
- **Station Search**: Find the nearest balloon launch site by city name or GPS coordinates.
- **Thermodynamic Analysis**: Automated calculation of SBCAPE, SBCIN, and LCL heights using MetPy.
- **Skew-T Visuals**: Generates full Log-P diagrams with temperature, dewpoint, and parcel paths.
- **Wind Analysis**: Generates Hodographs color-coded by height to analyze vertical wind shear.
- **Cloud Integration**: Automatically uploads plots to S3-compatible storage for easy sharing with LLMs.

## Prerequisites
- **Python 3.10+**
- **S3-Compatible Storage**: AWS S3, Cloudflare R2, or Backblaze B2.
- **Railway Account**: For cloud hosting (supports SSE transport).

## Environment Variables
Configure these in your Railway dashboard:
- `S3_BUCKET_NAME`: Your bucket name.
- `S3_ENDPOINT_URL`: Your S3 endpoint (e.g., https://s3.amazonaws.com).
- `AWS_ACCESS_KEY_ID`: Your access key.
- `AWS_SECRET_ACCESS_KEY`: Your secret key.

## Installation (Local Development)
1. Clone the repo: `git clone https://github.com/your-username/soundings-mcp.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run locally: `python main.py`

## Usage with Claude Desktop
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "soundings": {
      "type": "sse",
      "url": "[https://your-railway-app-url.up.railway.app/sse](https://your-railway-app-url.up.railway.app/sse)"
    }
  }
}
