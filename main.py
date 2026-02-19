import os
import math
import httpx
import boto3
import matplotlib.pyplot as plt
import metpy.calc as mpcalc
from metpy.plots import SkewT
from metpy.units import units
from fastmcp import FastMCP
from io import BytesIO

mcp = FastMCP("RAOB-Severe-Weather-Suite")

# --- Optional S3 Configuration ---
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")
AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")

# Only initialize S3 if all keys are present
s3_enabled = all([S3_BUCKET, S3_ENDPOINT, AWS_KEY, AWS_SECRET])
s3_client = None

if s3_enabled:
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=AWS_KEY,
            aws_secret_access_key=AWS_SECRET
        )
    except Exception as e:
        print(f"S3 Initialization failed: {e}")
        s3_enabled = False

# --- Helper Functions ---

async def fetch_sounding_data(station, timestamp):
    url = f"https://mesonet.agron.iastate.edu/json/raob.py?station={station.upper()}&ts={timestamp}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(url)
        res.raise_for_status()
        data = res.json()
        if not data.get("profiles"):
            return None
        return data["profiles"][0]["data"]

def upload_to_cloud(fig, file_prefix, station, timestamp):
    if not s3_enabled:
        return None
    
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    file_name = f"{file_prefix}_{station}_{timestamp}.png".replace(":", "")
    s3_client.upload_fileobj(
        img_buffer, S3_BUCKET, file_name,
        ExtraArgs={'ContentType': 'image/png'}
    )
    return f"{S3_ENDPOINT}/{S3_BUCKET}/{file_name}"

# --- Tools (Always Work) ---

@mcp.tool()
async def find_raob_station(query: str = None, lat: float = None, lon: float = None):
    """Finds the nearest RAOB launch site."""
    url = "https://mesonet.agron.iastate.edu/api/1/network/RAOB.json"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        stns_data = res.json()["data"]

    if query:
        matches = [s for s in stns_data if query.lower() in s['name'].lower() or query.upper() == s['id']]
        return {"matches": matches[:5]}

    if lat is not None and lon is not None:
        closest = min(stns_data, key=lambda s: math.sqrt((lat - s['lat'])**2 + (lon - s['lon'])**2))
        return {"closest_station": closest}
    return "Provide a query or coordinates."

@mcp.tool()
async def get_sounding_indices(station: str, timestamp: str):
    """Calculates thermodynamic indices (CAPE, CIN, LCL)."""
    levels = await fetch_sounding_data(station, timestamp)
    if not levels: return "No data found."
    
    # Filter for valid data points
    clean = [l for l in levels if all(l.get(k) is not None for k in ['pres', 'tmpc', 'dwpc'])]
    if not clean: return "Insufficient data for calculations."

    p = [l['pres'] for l in clean] * units.hPa
    t = [l['tmpc'] for l in clean] * units.degC
    td = [l['dwpc'] for l in clean] * units.degC
    
    sbcape, sbcin = mpcalc.surface_based_cape_cin(p, t, td)
    lcl_press, _ = mpcalc.lcl(p[0], t[0], td[0])
    
    return {
        "sbcape_jkg": round(float(sbcape.magnitude), 1),
        "sbcin_jkg": round(float(sbcin.magnitude), 1),
        "lcl_hpa": round(float(lcl_press.magnitude), 1)
    }

# --- Tools (Require S3) ---

@mcp.tool()
async def generate_skewt(station: str, timestamp: str):
    """Generates a Skew-T (Requires S3 configuration)."""
    if not s3_enabled:
        return "Plotting is disabled. Please configure S3 environment variables on Railway."
    
    levels = await fetch_sounding_data(station, timestamp)
    if not levels: return "No data found."

    clean = [l for l in levels if all(l.get(k) is not None for k in ['pres', 'tmpc', 'dwpc'])]
    
    p = [l['pres'] for l in clean] * units.hPa
    t = [l['tmpc'] for l in clean] * units.degC
    td = [l['dwpc'] for l in clean] * units.degC
    
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)
    skew.plot(p, t, 'r', linewidth=2)
    skew.plot(p, td, 'g', linewidth=2)
    
    url = upload_to_cloud(fig, "skewt", station, timestamp)
    plt.close(fig)
    return {"url": url}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
