def is_blank(value):
    return value is None or str(value).strip() == ""


def is_blank_row(row):
    fields = [
        "setup_number",
        "from_point",
        "to_point",
        "angle_deg",
        "angle_min",
        "angle_sec",
        "distance",
    ]
    return all(is_blank(row.get(field, "")) for field in fields)


def validate_project_settings(settings):
    errors = []

    starting_point = settings.get("starting_point", None)
    az_deg = settings.get("starting_azimuth_deg", None)
    az_min = settings.get("starting_azimuth_min", None)
    az_sec = settings.get("starting_azimuth_sec", None)

    if starting_point in [None, ""]:
        errors.append("Starting point is required.")

    for field_label, value in [
        ("Starting Azimuth Degrees", az_deg),
        ("Starting Azimuth Minutes", az_min),
        ("Starting Azimuth Seconds", az_sec),
    ]:
        if value in [None, ""]:
            errors.append(f"{field_label} is required.")

    try:
        if az_deg not in [None, ""]:
            float(az_deg)
    except ValueError:
        errors.append("Starting Azimuth Degrees must be numeric.")

    try:
        if az_min not in [None, ""]:
            az_min_num = float(az_min)
            if az_min_num < 0 or az_min_num > 59:
                errors.append("Starting Azimuth Minutes must be between 0 and 59.")
    except ValueError:
        errors.append("Starting Azimuth Minutes must be numeric.")

    try:
        if az_sec not in [None, ""]:
            az_sec_num = float(az_sec)
            if az_sec_num < 0 or az_sec_num >= 60:
                errors.append("Starting Azimuth Seconds must be between 0 and less than 60.")
    except ValueError:
        errors.append("Starting Azimuth Seconds must be numeric.")

    for field_name in ["starting_northing", "starting_easting"]:
        value = settings.get(field_name, 0)
        if value not in [None, ""]:
            try:
                float(value)
            except ValueError:
                errors.append(f"{field_name.replace('_', ' ').title()} must be numeric.")

    return errors


def validate_traverse_rows(rows):
    errors = []
    active_rows = []

    for idx, row in enumerate(rows, start=1):
        if is_blank_row(row):
            continue

        active_rows.append(row)

        setup_number = row.get("setup_number", "")
        from_point = row.get("from_point", "")
        to_point = row.get("to_point", "")
        angle_deg = row.get("angle_deg", "")
        angle_min = row.get("angle_min", "")
        angle_sec = row.get("angle_sec", "")
        distance = row.get("distance", "")

        if is_blank(setup_number):
            errors.append(f"Row {idx}: Setup Number is required.")

        if is_blank(from_point):
            errors.append(f"Row {idx}: From Point is required.")

        if is_blank(to_point):
            errors.append(f"Row {idx}: To Point is required.")

        if is_blank(distance):
            errors.append(f"Row {idx}: Distance is required.")

        try:
            if not is_blank(setup_number):
                float(setup_number)
        except ValueError:
            errors.append(f"Row {idx}: Setup Number must be numeric.")

        is_first_setup = False
        try:
            if not is_blank(setup_number):
                is_first_setup = float(setup_number) == 1
        except Exception:
            pass

        if not is_first_setup:
            for field_label, value in [
                ("Angle Degrees", angle_deg),
                ("Angle Minutes", angle_min),
                ("Angle Seconds", angle_sec),
            ]:
                if is_blank(value):
                    errors.append(f"Row {idx}: {field_label} is required for Setup 2 and higher.")

        try:
            if not is_blank(angle_deg):
                float(angle_deg)
        except ValueError:
            errors.append(f"Row {idx}: Angle Degrees must be numeric.")

        try:
            if not is_blank(angle_min):
                angle_min_num = float(angle_min)
                if angle_min_num < 0 or angle_min_num > 59:
                    errors.append(f"Row {idx}: Angle Minutes must be between 0 and 59.")
        except ValueError:
            if not is_first_setup:
                errors.append(f"Row {idx}: Angle Minutes must be numeric.")

        try:
            if not is_blank(angle_sec):
                angle_sec_num = float(angle_sec)
                if angle_sec_num < 0 or angle_sec_num >= 60:
                    errors.append(f"Row {idx}: Angle Seconds must be between 0 and less than 60.")
        except ValueError:
            if not is_first_setup:
                errors.append(f"Row {idx}: Angle Seconds must be numeric.")

        try:
            if not is_blank(distance):
                distance_num = float(distance)
                if distance_num <= 0:
                    errors.append(f"Row {idx}: Distance must be greater than zero.")
        except ValueError:
            errors.append(f"Row {idx}: Distance must be numeric.")

    if len(active_rows) < 2:
        errors.append("At least 2 active traverse setups are required.")

    return errors, active_rows

