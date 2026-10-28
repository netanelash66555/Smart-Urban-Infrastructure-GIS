from pathlib import Path
import os
import json

from dotenv import load_dotenv
from openai import OpenAI


# ==================================================
# Configuration
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MODEL_NAME = "gpt-6-luna"

ALLOWED_ASSET_TYPES = [
    "buildings",
    "hydrants",
    "street_lights",
    "catchbasins",
]

ASSET_LABELS = {
    "buildings": "Buildings",
    "hydrants": "Hydrants",
    "street_lights": "Street Lights",
    "catchbasins": "Catchbasins",
}


# ==================================================
# OpenAI client
# ==================================================

def get_openai_client():

    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY was not found in the .env file."
        )

    return OpenAI(
        api_key=OPENAI_API_KEY
    )


# ==================================================
# Validate extracted AI parameters
# ==================================================

def validate_analysis_parameters(parameters):

    distance_m = parameters.get("distance_m")
    asset_types = parameters.get("asset_types")

    if distance_m is not None:

        if not isinstance(distance_m, (int, float)):
            raise ValueError(
                "AI returned an invalid distance."
            )

        if distance_m <= 0 or distance_m > 5000:
            raise ValueError(
                "Distance must be between 1 and 5000 meters."
            )

        distance_m = int(distance_m)

    if not isinstance(asset_types, list):
        raise ValueError(
            "AI returned an invalid asset type list."
        )

    invalid_assets = [
        asset
        for asset in asset_types
        if asset not in ALLOWED_ASSET_TYPES
    ]

    if invalid_assets:
        raise ValueError(
            f"Unsupported asset types: {invalid_assets}"
        )

    if not asset_types:
        asset_types = ALLOWED_ASSET_TYPES.copy()

    return {
        "distance_m": distance_m,
        "asset_types": asset_types,
    }


# ==================================================
# Natural language -> structured parameters
# ==================================================

def parse_analysis_request(user_request):

    if not isinstance(user_request, str):
        raise ValueError(
            "User request must be text."
        )

    if not user_request.strip():
        raise ValueError(
            "User request cannot be empty."
        )

    client = get_openai_client()

    instructions = """
You are a parameter-extraction component for a municipal
infrastructure GIS analysis system.

The user may write in English or Hebrew.

Convert the user's request into structured JSON.

Return ONLY valid JSON with exactly these keys:

{
  "distance_m": number or null,
  "asset_types": []
}

The internal system supports ONLY:

- buildings
- hydrants
- street_lights
- catchbasins

Rules:

1. Never generate SQL.
2. Never invent database results.
3. Extract the requested distance in meters.
4. If no distance is specified, return null.
5. If no specific asset types are requested,
   return all four supported asset types.
6. Always return internal English asset values,
   even when the user writes in Hebrew.

Examples of terminology:

"buildings" -> buildings
"מבנים" -> buildings
"בניינים" -> buildings

"hydrants" -> hydrants
"fire hydrants" -> hydrants
"הידרנטים" -> hydrants
"ברזי כיבוי" -> hydrants
"ברזי שריפה" -> hydrants

"street lights" -> street_lights
"lights" -> street_lights
"פנסי רחוב" -> street_lights
"תאורת רחוב" -> street_lights
"פנסים" -> street_lights

"catch basins" -> catchbasins
"drainage" -> catchbasins
"קולטני ניקוז" -> catchbasins
"פתחי ניקוז" -> catchbasins
"ניקוז" -> catchbasins

Example:

User:
"בדוק הידרנטים ופנסי רחוב בטווח של 200 מטר"

Return:
{
  "distance_m": 200,
  "asset_types": ["hydrants", "street_lights"]
}
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=user_request,
    )

    raw_output = response.output_text.strip()

    if raw_output.startswith("```"):

        raw_output = (
            raw_output
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    try:

        parameters = json.loads(
            raw_output
        )

    except json.JSONDecodeError as error:

        raise ValueError(
            "AI response was not valid JSON."
        ) from error

    return validate_analysis_parameters(
        parameters
    )


# ==================================================
# Grounded AI business summary
# ==================================================

def generate_analysis_summary(
    road_name,
    distance_m,
    requested_results,
):

    if not isinstance(requested_results, dict):
        raise ValueError(
            "requested_results must be a dictionary."
        )

    if not requested_results:
        raise ValueError(
            "No analysis results were provided."
        )

    clean_results = {}

    for asset_type, count in requested_results.items():

        if asset_type not in ALLOWED_ASSET_TYPES:
            raise ValueError(
                f"Unsupported asset type: {asset_type}"
            )

        if not isinstance(count, (int, float)):
            raise ValueError(
                f"Invalid count for {asset_type}."
            )

        clean_results[asset_type] = int(count)

    total_assets = sum(
        clean_results.values()
    )

    result_lines = "\n".join(
        (
            f"{ASSET_LABELS[asset_type]}: "
            f"{count}"
        )
        for asset_type, count
        in clean_results.items()
    )

    client = get_openai_client()

    verified_data = f"""
Selected road segment: {road_name}
Analysis distance: {distance_m} meters

Requested asset results:
{result_lines}

Verified requested total: {total_assets}
"""

    instructions = """
You are a business-summary component for a municipal
infrastructure GIS decision-support system.

The application has already completed the spatial analysis
in PostGIS. The data supplied to you is verified application
output.

Write a concise professional summary of the analysis.

Requirements:

- Use ONLY the provided results.
- Preserve all numbers exactly.
- Discuss only the requested asset types.
- Do not generate or mention SQL.
- Do not invent additional infrastructure.
- Do not claim that any asset is damaged.
- Do not claim that an emergency exists.
- Do not describe a concentration as high or low because
  no historical baseline has been provided.
- "Affected" means only that an asset falls within the
  configured spatial analysis distance.
- You may identify which requested asset category has the
  largest count when there is more than one category.
- End with one neutral operational observation, such as
  reviewing the detailed asset list before planning work.
- Use clear professional English.
- Write approximately 2 to 4 sentences.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=verified_data,
    )

    summary = response.output_text.strip()

    if not summary:
        raise ValueError(
            "AI returned an empty business summary."
        )

    return summary