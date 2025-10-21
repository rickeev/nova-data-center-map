# Northern Virginia Data Centers Map

An interactive web map showcasing the massive concentration of data center infrastructure across Northern Virginia, particularly in Loudoun County. This project visualizes hundreds of data facilities operated by major cloud providers and colocation companies. Northern Virginia has become one of the world's largest data center hubs, largely due to its proximity to Washington D.C. and exceptional fiber infrastructure.

## What You Get

- **Interactive map** centered on Northern Virginia showing every data center location
- **Company-based filtering** – click a company name to see only their facilities
- **Search functionality** to quickly find specific providers
- **Live statistics** showing total data centers, companies, and currently visible markers
- **Popup details** with facility names, operators, and coordinates

## How It Works

The whole project breaks down into a few straightforward parts:

**Data Collection**: I manually gathered addresses from datacentermap.com, a widely-used data center directory. These are public, general locations – nothing proprietary.

**Geocoding**: A Python script takes those raw addresses and converts them to latitude/longitude coordinates using the Nominatim API (which powers OpenStreetMap). The script handles messy real-world data like address ranges, intersections, and inconsistent formatting.

**Web Map**: The coordinates get packaged into a GeoJSON file and displayed using Leaflet.js, a lightweight mapping library. The whole interface is vanilla JavaScript, HTML, and CSS – no heavy frameworks needed.

## Tech Stack

- **Frontend**: Leaflet.js (mapping), JavaScript, HTML, CSS
- **Scripting**: Python with geopy for geocoding
- **Data**: GeoJSON format, OpenStreetMap/Nominatim

## Known Limitations

Here's the honest part: not every address geocodes perfectly. Some reasons why:

- OpenStreetMap data varies in quality and completeness
- A few facilities are at intersections rather than fixed addresses, which are harder to pinpoint
- Some addresses are new or don't exist in OSM yet

You'll see empty coordinates for about 15-20 facilities. There's a `failed_geocodes.txt` file documenting these, and a `still_failed_geocodes.txt` showing addresses that couldn't be recovered even after retries.

## Running It Locally

**Important**: If you face CORS restrictions, you need to run a local web server.

### Option 1: Python HTTP Server (Recommended)

```bash
# Navigate to your project directory
cd path/to/DataCentersMap

# Python 3.6+
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

### Option 2: Node.js HTTP Server

```bash
# Navigate to your project directory
cd path/to/DataCentersMap

# Install http-server globally (one-time)
npm install -g http-server

# Run the server
http-server
```

Then open the URL shown in the terminal (usually `http://localhost:8080`).

### Option 3: VS Code Live Server

1. Install the "Live Server" extension in VS Code
2. Right-click on `index.html`
3. Select "Open with Live Server"

### Regenerating the Data

To regenerate the GeoJSON file from the source addresses:

```bash
# Requires Python 3.6+
pip install geopy

# Regenerate the GeoJSON file
python script.py
```

Then refresh your browser to load the updated map.

## Fair Warning

This data is based on publicly available information and should be treated accordingly. Exact coordinates may not be perfectly precise, especially for large campuses. If you need production-grade facility location data, you'll want to cross-reference with official sources.