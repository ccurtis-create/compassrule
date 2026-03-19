import math
import pandas as pd


def dms_to_decimal(deg, minute, sec):
    return float(deg) + float(minute) / 60.0 + float(sec) / 3600.0


def normalize_azimuth(angle):
    angle = float(angle) % 360.0
    if angle < 0:
        angle += 360.0
    return angle


def degrees_to_radians(angle_deg):
    return math.radians(angle_deg)


def build_clean_setups(rows):
    setups = []

    for row in rows:
        setup_number = int(float(row.get("setup_number", 0)))
        angle_deg = row.get("angle_deg", None)
        angle_min = row.get("angle_min", None)
        angle_sec = row.get("angle_sec", None)

        setup = {
            "setup_number": setup_number,
            "from_point": str(row.get("from_point", "")).strip(),
            "to_point": str(row.get("to_point", "")).strip(),
            "distance": float(row.get("distance", 0)),
            "angle_deg": None if angle_deg in [None, ""] else float(angle_deg),
            "angle_min": None if angle_min in [None, ""] else float(angle_min),
            "angle_sec": None if angle_sec in [None, ""] else float(angle_sec),
        }

        if setup_number == 1:
            setup["angle_decimal"] = None
        else:
            setup["angle_decimal"] = dms_to_decimal(
                setup["angle_deg"],
                setup["angle_min"],
                setup["angle_sec"],
            )

        setups.append(setup)

    setups.sort(key=lambda x: x["setup_number"])
    return setups


def compute_azimuths(starting_azimuth, setups, traverse_direction="Clockwise"):
    azimuths = []

    if not setups:
        return azimuths

    for i, setup in enumerate(setups):
        if i == 0:
            azimuths.append(normalize_azimuth(starting_azimuth))
        else:
            angle = setups[i]["angle_decimal"]

            if traverse_direction == "Counterclockwise":
                next_az = azimuths[i - 1] - 180.0 + angle
            else:
                next_az = azimuths[i - 1] + 180.0 - angle

            azimuths.append(normalize_azimuth(next_az))

    return azimuths


def compute_lat_dep(distance, azimuth_deg):
    az_rad = degrees_to_radians(azimuth_deg)
    latitude = float(distance) * math.cos(az_rad)
    departure = float(distance) * math.sin(az_rad)
    return latitude, departure


def compute_raw_results(setups, starting_azimuth, traverse_direction="Clockwise"):
    azimuths = compute_azimuths(starting_azimuth, setups, traverse_direction)

    for i, setup in enumerate(setups):
        setup["azimuth"] = azimuths[i]
        latitude, departure = compute_lat_dep(setup["distance"], setup["azimuth"])
        setup["raw_latitude"] = latitude
        setup["raw_departure"] = departure

    return setups


def compute_closure(setups):
    total_distance = sum(setup["distance"] for setup in setups)
    sum_latitude = sum(setup["raw_latitude"] for setup in setups)
    sum_departure = sum(setup["raw_departure"] for setup in setups)
    linear_error = math.sqrt(sum_latitude**2 + sum_departure**2)

    if linear_error > 0:
        precision_ratio = total_distance / linear_error
        precision_display = f"1:{round(precision_ratio):,}"
    else:
        precision_ratio = None
        precision_display = "Perfect Closure"

    return {
        "number_of_setups": len(setups),
        "total_distance": total_distance,
        "sum_latitude": sum_latitude,
        "sum_departure": sum_departure,
        "linear_error": linear_error,
        "precision_ratio": precision_ratio,
        "precision_display": precision_display,
    }


def apply_compass_rule(setups, closure):
    total_distance = closure["total_distance"]
    sum_latitude = closure["sum_latitude"]
    sum_departure = closure["sum_departure"]

    if total_distance <= 0:
        raise ValueError("Total distance must be greater than zero.")

    for setup in setups:
        lat_corr = -sum_latitude * (setup["distance"] / total_distance)
        dep_corr = -sum_departure * (setup["distance"] / total_distance)

        setup["latitude_correction"] = lat_corr
        setup["departure_correction"] = dep_corr
        setup["adjusted_latitude"] = setup["raw_latitude"] + lat_corr
        setup["adjusted_departure"] = setup["raw_departure"] + dep_corr

    return setups


def compute_adjusted_coordinates(setups, starting_northing=0.0, starting_easting=0.0, starting_point="1"):
    coordinates = []

    current_n = float(starting_northing)
    current_e = float(starting_easting)

    coordinates.append({
        "point": str(starting_point),
        "northing": current_n,
        "easting": current_e,
    })

    for setup in setups:
        current_n += setup["adjusted_latitude"]
        current_e += setup["adjusted_departure"]

        point_name = setup["to_point"] if setup["to_point"] else f"P{setup['setup_number'] + 1}"

        coordinates.append({
            "point": point_name,
            "northing": current_n,
            "easting": current_e,
        })

    return coordinates


def calculate_traverse(settings, rows):
    starting_azimuth = dms_to_decimal(
        settings["starting_azimuth_deg"],
        settings["starting_azimuth_min"],
        settings["starting_azimuth_sec"],
    )

    setups = build_clean_setups(rows)
    setups = compute_raw_results(
        setups,
        starting_azimuth,
        settings.get("traverse_direction", "Clockwise"),
    )

    closure = compute_closure(setups)
    setups = apply_compass_rule(setups, closure)
    coordinates = compute_adjusted_coordinates(
        setups,
        settings.get("starting_northing", 0.0),
        settings.get("starting_easting", 0.0),
        settings.get("starting_point", "1"),
    )

    raw_df = pd.DataFrame([
        {
            "Setup Number": s["setup_number"],
            "From Point": s["from_point"],
            "To Point": s["to_point"],
            "Angle DD": s["angle_decimal"],
            "Azimuth": s["azimuth"],
            "Distance": s["distance"],
            "Latitude": s["raw_latitude"],
            "Departure": s["raw_departure"],
        }
        for s in setups
    ])

    adjusted_df = pd.DataFrame([
        {
            "Setup Number": s["setup_number"],
            "Distance": s["distance"],
            "Raw Latitude": s["raw_latitude"],
            "Lat Correction": s["latitude_correction"],
            "Adjusted Latitude": s["adjusted_latitude"],
            "Raw Departure": s["raw_departure"],
            "Dep Correction": s["departure_correction"],
            "Adjusted Departure": s["adjusted_departure"],
        }
        for s in setups
    ])

    coordinates_df = pd.DataFrame(coordinates)

    return {
        "setups": setups,
        "closure": closure,
        "raw_df": raw_df,
        "adjusted_df": adjusted_df,
        "coordinates_df": coordinates_df,
        "starting_azimuth_decimal": starting_azimuth,
    }

