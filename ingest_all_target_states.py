"""
Batch Ingestion Script for Requested States from NWIC / CGWB:
Rajasthan, Punjab, Andhra Pradesh, Delhi, Kerala, Tamil Nadu, Uttar Pradesh, Bihar.
"""
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingres.schema.db_setup import get_connection
from ingres.data.nwic_loader import ingest_state_data, NWIC_RESOURCES

target_states = [
    "rajasthan",
    "punjab",
    "andhra",
    "delhi",
    "kerala",
    "tamil nadu",
    "uttar pradesh",
    "bihar"
]

print("================================================================")
print("💧 NWIC Real CGWB Data Ingestion Pipeline")
print(f"Target States: {', '.join(s.title() for s in target_states)}")
print("================================================================\n")

con = get_connection()
summary = []

for s in target_states:
    print(f"--> Processing {s.upper()}...")
    try:
        res = ingest_state_data(s, con, max_rows=1500)
        print(f"    ✓ {res['state']}: {res['stations']} stations, {res['levels']} level logs, {res['quality']} quality logs.")
        summary.append(res)
    except Exception as e:
        print(f"    ❌ Error on {s}: {e}")

# Overall Stats
total_wells = con.execute("SELECT COUNT(*) FROM wells").fetchone()[0]
total_levels = con.execute("SELECT COUNT(*) FROM gw_levels").fetchone()[0]
total_quality = con.execute("SELECT COUNT(*) FROM gw_quality").fetchone()[0]
live_wells = con.execute("SELECT COUNT(*) FROM wells WHERE data_source='CGWB-NWIC-Live'").fetchone()[0]

print("\n================================================================")
print("🎉 Ingestion Pipeline Finished Successfully!")
print(f"Total Stations in Database:       {total_wells:,} (Live CGWB: {live_wells:,})")
print(f"Total Water Level Observations:   {total_levels:,}")
print(f"Total Chemical Quality Samples:   {total_quality:,}")
print("================================================================")

con.close()

