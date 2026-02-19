import os
import math
import httpx
import boto3
import matplotlib.pyplot as plt
import metpy.calc as mpcalc
from metpy.plots import SkewT, Hodograph
from metpy.units import units
from fastmcp import FastMCP
from io import BytesIO

# Initialize FastMCP with SSE for Cloud Deployment
mcp = FastMCP("RAOB-Severe-Weather-Suite")

# --- Configuration (Set these as Environment Variables in Railway) ---
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")

try:
    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
except Exception as e:
    print(f"Warning: S3 Client failed to initialize. Check Env Vars. Error: {e}")
    s3_client = None

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
    if s3_client is None:
        return "Error: S3 client is not configured. Check environment variables."
    
    img_buffer = BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    file_name = f"{file_prefix}_{station}_{timestamp}.png".replace(":", "")
    s3_client.upload_fileobj(
        img_buffer, S3_BUCKET, file_name,
        ExtraArgs={'ContentType': 'image/png'}
    )
    return f"{S3_ENDPOINT}/{S3_BUCKET}/{file_name}"

# --- MCP Tools ---

@mcp.tool()
async def find_raob_station(query: str = None, lat: float = None, lon: float = None):
    """Finds the nearest RAOB launch site by name or coordinates."""
    all_stns_url = "https://mesonet.agron.iastate.edu/api/1/network/RAOB.json"
    async with httpx.AsyncClient() as client:
        res = await client.get(all_stns_url)
        stns_data = res.json()["data"]

    if query:
        matches = [s for s in stns_data if query.lower() in s['name'].lower() or query.upper() == s['id']]
        return {"matches": matches[:5]}

    if lat is not None and lon is not None:
        closest = min(stns_data, key=lambda s: math.sqrt((lat - s['lat'])**2 + (lon - s['lon'])**2))
        return {"closest_station": closest}
    
    return "Please provide a query or coordinates."

@mcp.tool()
async def get_sounding_indices(station: str, timestamp: str):
    """Calculates thermodynamic indices (CAPE, CIN, LCL) for a sounding."""
    levels = await fetch_sounding_data(station, timestamp)
    if not levels: return "No data found."
    
    p = [l['pres'] for l in levels if l['pres'] is not None] * units.hPa
    t = [l['tmpc'] for l in levels if l['tmpc'] is not None] * units.degC
    td = [l['dwpc'] for l in levels if l['dwpc'] is not None] * units.degC
    
    sbcape, sbcin = mpcalc.surface_based_cape_cin(p, t, td)
    lcl_press, _ = mpcalc.lcl(p[0], t[0], td[0])
    
    return {
        "sbcape": round(float(sbcape.magnitude), 1),
        "sbcin": round(float(sbcin.magnitude), 1),
        "lcl_hpa": round(float(lcl_press.magnitude), 1)
    }

@mcp.tool()
async def generate_skewt(station: str, timestamp: str):
    """Generates a Skew-T with robust None filtering."""
    levels = await fetch_sounding_data(station, timestamp)
    if not levels: return "No data found."

    # Filter for valid thermo data
    clean = [l for l in levels if all(k in l and l[k] is not None for k in ['pres', 'tmpc', 'dwpc'])]
    
    p = [l['pres'] for l in clean] * units.hPa
    t = [l['tmpc'] for l in clean] * units.degC
    td = [l['dwpc'] for l in clean] * units.degC
    
    fig = plt.figure(figsize=(9, 9))
    skew = SkewT(fig, rotation=45)
    skew.plot(p, t, 'r', linewidth=2)
    skew.plot(p, td, 'g', linewidth=2)
    
    # Check if we have surface data to calculate a parcel path
    if len(p) > 0:
        prof = mpcalc.parcel_profile(p, t[0], td[0]).to('degC')
        skew.shade_cape(p, t, prof)
    
    plt.title(f"Skew-T: {station} at {timestamp}")
    url = upload_to_cloud(fig, "skewt", station, timestamp)
    plt.close(fig)
    return {"url": url}

@mcp.tool()
async def generate_hodograph(station: str, timestamp: str):
    """Generates a Hodograph color-coded by altitude (MSL)."""
    levels = await fetch_sounding_data(station, timestamp)
    if not levels: return "No data found."

    # Filter out any levels where wind or height is missing
    clean = [l for l in levels if all(k in l and l[k] is not None for k in ['drct', 'sknt', 'hght'])]
    
    if not clean: return "Insufficient wind data for a hodograph."

    h = [l['hght'] for l in clean] * units.meters
    u, v = mpcalc.wind_components(
        [l['sknt'] for l in clean] * units.knots,
        [l['drct'] for l in clean] * units.degrees
    )

    fig, ax = plt.subplots(figsize=(7, 7))
    hodo = Hodograph(ax, component_range=80)
    hodo.add_grid(increment=20)
    
    # Use 'h' (height) for the colormap, not dewpoint!
    hodo.plot_colormapped(u, v, h) 
    
    plt.title(f"Hodograph: {station} at {timestamp}")
    url = upload_to_cloud(fig, "hodo", station, timestamp)
    plt.close(fig)
    return {"url": url}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
