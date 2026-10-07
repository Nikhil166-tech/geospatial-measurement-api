import os
from pathlib import Path
import zipfile
import shapefile

def generate_samples():
    sample_dir = Path(__file__).resolve().parent

    wkt_wgs84 = (
        'GEOGCS["GCS_WGS_1984",'
        'DATUM["D_WGS_1984",'
        'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],'
        'UNIT["Degree",0.0174532925199433]]'
    )

    # 1. Parcels Shapefile (Polygons)
    parcels_base = str(sample_dir / "parcels")
    w = shapefile.Writer(parcels_base, shapeType=shapefile.POLYGON)
    w.field("name", "C", size=50)
    w.field("crop", "C", size=30)
    w.field("parcel_id", "N", size=10)

    # Parcel 1 (Clockwise)
    w.poly([[[77.580, 12.970], [77.580, 12.975], [77.585, 12.975], [77.585, 12.970], [77.580, 12.970]]])
    w.record("Parcel Alpha", "Soybean", 101)

    # Parcel 2 (Clockwise)
    w.poly([[[77.590, 12.980], [77.590, 12.986], [77.598, 12.986], [77.598, 12.980], [77.590, 12.980]]])
    w.record("Parcel Beta", "Cotton", 102)
    w.close()

    prj_file = sample_dir / "parcels.prj"
    prj_file.write_text(wkt_wgs84, encoding="utf-8")

    zip_path = sample_dir / "parcels.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for ext in ["shp", "shx", "dbf", "prj"]:
            f = sample_dir / f"parcels.{ext}"
            if f.exists():
                z.write(f, arcname=f"parcels.{ext}")
                f.unlink()

    print(f"Generated: {zip_path}")

    # 2. Flight Paths Shapefile (Lines)
    lines_base = str(sample_dir / "flight_paths")
    wl = shapefile.Writer(lines_base, shapeType=shapefile.POLYLINE)
    wl.field("flight_id", "C", size=30)
    wl.field("altitude", "N", size=5)

    wl.line([[[77.580, 12.970], [77.584, 12.974], [77.588, 12.978]]])
    wl.record("Flight_TR_01", 120)

    wl.line([[[77.590, 12.980], [77.595, 12.985]]])
    wl.record("Flight_TR_02", 150)
    wl.close()

    prj_lines = sample_dir / "flight_paths.prj"
    prj_lines.write_text(wkt_wgs84, encoding="utf-8")

    zip_lines = sample_dir / "flight_paths.zip"
    with zipfile.ZipFile(zip_lines, "w") as z:
        for ext in ["shp", "shx", "dbf", "prj"]:
            f = sample_dir / f"flight_paths.{ext}"
            if f.exists():
                z.write(f, arcname=f"flight_paths.{ext}")
                f.unlink()

    print(f"Generated: {zip_lines}")

if __name__ == "__main__":
    generate_samples()
