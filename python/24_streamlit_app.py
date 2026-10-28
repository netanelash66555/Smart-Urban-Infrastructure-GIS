import html

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

from spatial_impact_engine import (
    find_nearest_road,
    run_spatial_impact_analysis,
    get_affected_assets,
    save_analysis_run,
    get_analysis_history,
    get_analysis_run_context,
)

from ai_analysis_service import (
    parse_analysis_request,
    generate_analysis_summary,
)


# ==================================================
# Configuration
# ==================================================

MAX_ROAD_SELECTION_DISTANCE_M = 50

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

ASSET_COUNT_COLUMNS = {
    "buildings": "buildings_count",
    "hydrants": "hydrants_count",
    "street_lights": "street_lights_count",
    "catchbasins": "catchbasins_count",
}


# ==================================================
# Page configuration
# ==================================================

st.set_page_config(
    page_title="Smart Urban Infrastructure GIS",
    layout="wide",
)


# ==================================================
# Styling
# ==================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }

    h2, h3 {
        font-weight: 750 !important;
        letter-spacing: -0.01em;
    }

    .helper-text {
        color: #475569;
        font-size: 15px;
        line-height: 1.6;
        margin-top: 4px;
        margin-bottom: 14px;
    }

    .meta-text {
        color: #596579;
        font-size: 14px;
        line-height: 1.5;
        margin-top: 5px;
        margin-bottom: 14px;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d8dee8;
        border-radius: 12px;
        padding: 17px;
    }

    div[data-testid="stMetricLabel"] p {
        color: #334155 !important;
        font-size: 15px !important;
        font-weight: 650 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 750 !important;
    }

    .result-summary {
        background: #ffffff;
        color: #17202a;
        border: 1px solid #cbd5e1;
        border-left: 5px solid #2563eb;
        border-radius: 10px;
        padding: 16px 19px;
        margin-top: 14px;
        margin-bottom: 22px;
        font-size: 16px;
        line-height: 1.6;
    }

    .ai-summary-card {
        background: #f8fafc;
        color: #17202a;
        border: 1px solid #cbd5e1;
        border-left: 5px solid #7c3aed;
        border-radius: 10px;
        padding: 17px 20px;
        margin-top: 12px;
        margin-bottom: 24px;
        font-size: 16px;
        line-height: 1.7;
    }

    .history-note {
        background: #f8fafc;
        color: #334155;
        border: 1px solid #d8dee8;
        border-radius: 10px;
        padding: 14px 17px;
        margin-top: 10px;
        margin-bottom: 18px;
        font-size: 15px;
        line-height: 1.55;
    }

    .stTabs [data-baseweb="tab"] p {
        font-size: 15px !important;
        font-weight: 650 !important;
        color: #334155 !important;
    }

    .stTabs [aria-selected="true"] p {
        color: #111827 !important;
        font-weight: 800 !important;
    }

    .professional-table-container {
        width: 100%;
        overflow: auto;
        border: 1px solid #d7dee7;
        border-radius: 10px;
        background: #ffffff;
        margin-top: 10px;
        margin-bottom: 20px;
    }

    .professional-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 15px;
        color: #111827;
    }

    .professional-table th {
        background: #eef2f7;
        color: #1f2937;
        font-size: 15px;
        font-weight: 700;
        padding: 13px 14px;
        border-bottom: 1px solid #cbd5e1;
        position: sticky;
        top: 0;
        z-index: 1;
        white-space: nowrap;
    }

    .professional-table td {
        padding: 11px 14px;
        border-bottom: 1px solid #e5e7eb;
        background: #ffffff;
        font-size: 15px;
    }

    .professional-table tr:nth-child(even) td {
        background: #fafcff;
    }

    .professional-table tr:hover td {
        background: #f3f6fa;
    }

    .professional-table tr:last-child td {
        border-bottom: none;
    }

    .table-center {
        text-align: center;
    }

    .table-left {
        text-align: left;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# Helper functions
# ==================================================

def helper_text(text):

    st.html(
        f"""
        <div class="helper-text">
            {html.escape(text)}
        </div>
        """
    )


def meta_text(text):

    st.html(
        f"""
        <div class="meta-text">
            {html.escape(text)}
        </div>
        """
    )


def normalize_asset_array(value):

    if isinstance(value, (list, tuple)):
        return list(value)

    if isinstance(value, str):

        cleaned = value.strip().strip("{}")

        if not cleaned:
            return []

        return [
            item.strip()
            for item in cleaned.split(",")
        ]

    return []


def format_identifier(value):

    if pd.isna(value):
        return "—"

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value)


def render_professional_table(
    dataframe,
    center_columns=None,
    max_height=430,
):

    if dataframe.empty:

        st.info(
            "No records are available for this selection."
        )

        return

    center_columns = set(
        center_columns or []
    )

    header_cells = []

    for column in dataframe.columns:

        css_class = (
            "table-center"
            if column in center_columns
            else "table-left"
        )

        header_cells.append(
            f"""
            <th class="{css_class}">
                {html.escape(str(column))}
            </th>
            """
        )

    rows_html = []

    for _, row in dataframe.iterrows():

        cells = []

        for column in dataframe.columns:

            value = row[column]

            display_value = (
                "—"
                if pd.isna(value)
                else str(value)
            )

            css_class = (
                "table-center"
                if column in center_columns
                else "table-left"
            )

            cells.append(
                f"""
                <td class="{css_class}">
                    {html.escape(display_value)}
                </td>
                """
            )

        rows_html.append(
            "<tr>"
            + "".join(cells)
            + "</tr>"
        )

    table_html = f"""
    <div
        class="professional-table-container"
        style="max-height:{max_height}px;"
    >
        <table class="professional-table">

            <thead>
                <tr>
                    {''.join(header_cells)}
                </tr>
            </thead>

            <tbody>
                {''.join(rows_html)}
            </tbody>

        </table>
    </div>
    """

    st.html(
        table_html
    )


def prepare_asset_display_table(rows):

    df = pd.DataFrame(rows)

    if df.empty:
        return df, []

    rename_map = {
        "building_id": "Building ID",
        "hydrant_id": "Hydrant ID",
        "light_id": "Light ID",
        "catchbasin_id": "Catchbasin ID",
        "source_id": "Source ID",
        "facility_id": "Facility ID",
        "building_type": "Building Type",
        "street_name": "Street Name",
        "address": "Address",
        "distance_m": "Distance (m)",
    }

    df = df.rename(
        columns=rename_map
    )

    identifier_columns = [
        "Building ID",
        "Hydrant ID",
        "Light ID",
        "Catchbasin ID",
        "Source ID",
        "Facility ID",
    ]

    for column in identifier_columns:

        if column in df.columns:

            df[column] = df[column].apply(
                format_identifier
            )

    if "Distance (m)" in df.columns:

        df["Distance (m)"] = df[
            "Distance (m)"
        ].apply(
            lambda value:
                "—"
                if pd.isna(value)
                else f"{float(value):.2f}"
        )

    center_columns = [
        column
        for column in identifier_columns
        if column in df.columns
    ]

    if "Street Name" in df.columns:

        center_columns.append(
            "Street Name"
        )

    if "Distance (m)" in df.columns:

        center_columns.append(
            "Distance (m)"
        )

    return df, center_columns


# ==================================================
# Header
# ==================================================

st.title(
    "Smart Urban Infrastructure GIS"
)

helper_text(
    "Select a road segment, describe the required analysis, "
    "review the interpreted parameters, and run the spatial analysis."
)


# ==================================================
# Session state
# ==================================================

if "selected_road" not in st.session_state:
    st.session_state.selected_road = None

if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None

if "affected_assets" not in st.session_state:
    st.session_state.affected_assets = None

if "last_selected_road_id" not in st.session_state:
    st.session_state.last_selected_road_id = None

if "ai_parameters" not in st.session_state:
    st.session_state.ai_parameters = None

if "business_summary" not in st.session_state:
    st.session_state.business_summary = None

if "historical_run_context" not in st.session_state:
    st.session_state.historical_run_context = None

if "historical_run_assets" not in st.session_state:
    st.session_state.historical_run_assets = None

if "review_distance_m" not in st.session_state:
    st.session_state.review_distance_m = None


# ==================================================
# Map
# ==================================================

cambridge_center = [
    42.3736,
    -71.1097,
]

m = folium.Map(
    location=cambridge_center,
    zoom_start=14,
)


# ==================================================
# 1. Select Road
# ==================================================

st.subheader(
    "1. Select Road Location"
)

map_data = st_folium(
    m,
    width=900,
    height=550,
)


# ==================================================
# Handle Map Click
# ==================================================

if map_data["last_clicked"]:

    latitude = map_data[
        "last_clicked"
    ]["lat"]

    longitude = map_data[
        "last_clicked"
    ]["lng"]

    try:

        road = find_nearest_road(
            latitude=latitude,
            longitude=longitude,
        )

        if road:

            road_distance = float(
                road["distance_m"]
            )

            if (
                road_distance
                <= MAX_ROAD_SELECTION_DISTANCE_M
            ):

                new_road_id = (
                    road["road_id"]
                )

                if (
                    st.session_state.last_selected_road_id
                    != new_road_id
                ):

                    st.session_state.analysis_results = None
                    st.session_state.affected_assets = None
                    st.session_state.ai_parameters = None
                    st.session_state.business_summary = None
                    st.session_state.review_distance_m = None

                    st.session_state.pop(
                        "distance_widget",
                        None,
                    )

                    st.session_state.pop(
                        "review_asset_types",
                        None,
                    )

                st.session_state.selected_road = dict(
                    road
                )

                st.session_state.last_selected_road_id = (
                    new_road_id
                )

            else:

                st.session_state.selected_road = None
                st.session_state.analysis_results = None
                st.session_state.affected_assets = None
                st.session_state.ai_parameters = None
                st.session_state.business_summary = None
                st.session_state.last_selected_road_id = None
                st.session_state.review_distance_m = None

                st.session_state.pop(
                    "distance_widget",
                    None,
                )

                st.session_state.pop(
                    "review_asset_types",
                    None,
                )

                st.warning(
                    "The selected location is too far from a road. "
                    "Please click closer to a road."
                )

    except Exception as error:

        st.error(
            f"Database error while selecting road: {error}"
        )


# ==================================================
# Selected Road Workflow
# ==================================================

road = st.session_state.selected_road

if road:

    # --------------------------------------------------
    # 2. Selected Road
    # --------------------------------------------------

    st.subheader(
        "2. Selected Road"
    )

    st.success(
        f"Selected road: {road['street_name']}"
    )

    st.write(
        f"Distance from clicked location to road: "
        f"{road['distance_m']} meters"
    )

    meta_text(
        f"Internal road segment ID: "
        f"{road['road_id']}"
    )


    # --------------------------------------------------
    # 3. AI Analysis Request
    # --------------------------------------------------

    st.subheader(
        "3. AI Analysis Request"
    )

    helper_text(
        "Describe the required infrastructure analysis "
        "in English or Hebrew."
    )

    ai_request = st.text_area(
        "Analysis request",
        placeholder=(
            "Examples:\n"
            "Analyze hydrants and street lights within 250 meters.\n"
            "בדוק הידרנטים ופנסי רחוב בטווח של 250 מטר."
        ),
    )

    if st.button(
        "Interpret Request"
    ):

        try:

            parsed_parameters = (
                parse_analysis_request(
                    ai_request
                )
            )

            st.session_state.ai_parameters = (
                parsed_parameters
            )

            parsed_distance = (
                parsed_parameters[
                    "distance_m"
                ]
            )

            if parsed_distance is not None:

                st.session_state.review_distance_m = int(
                    parsed_distance
                )

            else:

                st.session_state.review_distance_m = None

            # Force the distance input to rebuild from
            # the newly interpreted AI value.
            st.session_state.pop(
                "distance_widget",
                None,
            )

            st.session_state.review_asset_types = list(
                parsed_parameters["asset_types"]
            )

            st.session_state.analysis_results = None
            st.session_state.affected_assets = None
            st.session_state.business_summary = None

        except Exception as error:

            st.error(
                f"AI request error: {error}"
            )


    # --------------------------------------------------
    # 4. Review Analysis Parameters
    # --------------------------------------------------

    ai_parameters = (
        st.session_state.ai_parameters
    )

    if ai_parameters:

        st.success(
            "AI request interpreted successfully."
        )

        st.subheader(
            "4. Review Analysis Parameters"
        )

        helper_text(
            "Review or adjust the AI interpretation "
            "before running the spatial analysis."
        )

        if (
            ai_parameters["distance_m"]
            is None
        ):

            st.warning(
                "The request did not contain a distance. "
                "Please define one before running the analysis."
            )

        distance_m = st.number_input(
            "Impact distance (meters)",
            min_value=1,
            max_value=5000,
            value=(
                st.session_state.review_distance_m
            ),
            step=50,
            placeholder="Enter distance in meters",
            key="distance_widget",
        )

        selected_asset_types = (
            st.multiselect(
                "Asset types",
                options=ALLOWED_ASSET_TYPES,
                format_func=lambda asset:
                    ASSET_LABELS[asset],
                key="review_asset_types",
            )
        )

        if not selected_asset_types:

            st.warning(
                "Select at least one asset type."
            )

        if distance_m is None:

            st.info(
                "Enter an impact distance to enable the analysis."
            )


        # --------------------------------------------------
        # 5. Run Analysis
        # --------------------------------------------------

        st.subheader(
            "5. Run Analysis"
        )

        run_disabled = (
            distance_m is None
            or len(selected_asset_types) == 0
        )

        if st.button(
            "Run Impact Analysis",
            type="primary",
            disabled=run_disabled,
        ):

            try:

                full_analysis = (
                    run_spatial_impact_analysis(
                        geometry_wkt=road["geometry_wkt"],
                        distance_m=distance_m,
                    )
                )

                affected_assets = (
                    get_affected_assets(
                        geometry_wkt=road["geometry_wkt"],
                        distance_m=distance_m,
                        asset_types=selected_asset_types,
                    )
                )

                analysis_id = (
                    save_analysis_run(
                        road_id=road["road_id"],
                        distance_m=distance_m,
                        analysis=full_analysis,
                        requested_asset_types=(
                            selected_asset_types
                        ),
                    )
                )

                st.session_state.analysis_results = {
                    "analysis_id": analysis_id,
                    "distance_m": distance_m,
                    "road_name": road["street_name"],
                    "selected_asset_types": list(
                        selected_asset_types
                    ),
                    "buildings":
                        full_analysis["buildings"],
                    "hydrants":
                        full_analysis["hydrants"],
                    "street_lights":
                        full_analysis["street_lights"],
                    "catchbasins":
                        full_analysis["catchbasins"],
                }

                st.session_state.affected_assets = (
                    affected_assets
                )

                st.session_state.business_summary = None

            except Exception as error:

                st.error(
                    f"Analysis error: {error}"
                )


    # --------------------------------------------------
    # Current Results
    # --------------------------------------------------

    results = (
        st.session_state.analysis_results
    )

    if results:

        st.success(
            "Impact analysis completed and saved successfully."
        )

        meta_text(
            f"Analysis Run ID: "
            f"{results['analysis_id']}"
        )

        st.subheader(
            "Analysis Results"
        )

        selected_types = (
            results["selected_asset_types"]
        )

        count_lookup = {
            "buildings":
                results["buildings"],

            "hydrants":
                results["hydrants"],

            "street_lights":
                results["street_lights"],

            "catchbasins":
                results["catchbasins"],
        }

        result_columns = st.columns(
            len(selected_types)
        )

        for column, asset_type in zip(
            result_columns,
            selected_types,
        ):

            column.metric(
                ASSET_LABELS[asset_type],
                count_lookup[asset_type],
            )

        selected_total = sum(
            count_lookup[asset_type]
            for asset_type in selected_types
        )

        st.metric(
            "Total Requested Assets",
            selected_total,
        )

        road_name_safe = html.escape(
            results["road_name"]
        )

        st.html(
            f"""
            <div class="result-summary">
                The requested analysis identified
                <strong>{selected_total}</strong>
                infrastructure assets within
                <strong>{results['distance_m']} meters</strong>
                of
                <strong>{road_name_safe}</strong>.
            </div>
            """
        )


        # --------------------------------------------------
        # AI Business Summary
        # --------------------------------------------------

        st.markdown(
            "### AI Business Summary"
        )

        helper_text(
            "Generate a concise business-oriented explanation "
            "using only the verified PostGIS results."
        )

        if st.button(
            "Generate AI Business Summary"
        ):

            try:

                requested_results = {
                    asset_type:
                        int(
                            count_lookup[
                                asset_type
                            ]
                        )
                    for asset_type
                    in selected_types
                }

                summary = (
                    generate_analysis_summary(
                        road_name=results[
                            "road_name"
                        ],
                        distance_m=results[
                            "distance_m"
                        ],
                        requested_results=(
                            requested_results
                        ),
                    )
                )

                st.session_state.business_summary = (
                    summary
                )

            except Exception as error:

                st.error(
                    f"AI summary error: {error}"
                )

        if st.session_state.business_summary:

            summary_safe = html.escape(
                st.session_state.business_summary
            ).replace(
                "\n",
                "<br>"
            )

            st.html(
                f"""
                <div class="ai-summary-card">
                    {summary_safe}
                </div>
                """
            )


        # --------------------------------------------------
        # Current Asset Details
        # --------------------------------------------------

        assets = (
            st.session_state.affected_assets
        )

        if assets:

            st.subheader(
                "Affected Asset Details"
            )

            tabs = st.tabs(
                [
                    (
                        f"{ASSET_LABELS[asset_type]} "
                        f"({count_lookup[asset_type]})"
                    )
                    for asset_type
                    in selected_types
                ]
            )

            for tab, asset_type in zip(
                tabs,
                selected_types,
            ):

                with tab:

                    st.markdown(
                        f"### "
                        f"{ASSET_LABELS[asset_type]} Details"
                    )

                    helper_text(
                        "Assets are ordered from nearest "
                        "to farthest from the selected road segment."
                    )

                    (
                        asset_table,
                        center_columns,
                    ) = prepare_asset_display_table(
                        assets[asset_type]
                    )

                    render_professional_table(
                        dataframe=asset_table,
                        center_columns=center_columns,
                        max_height=430,
                    )


else:

    st.info(
        "Click close to a road before running the analysis."
    )


# ==================================================
# 6. Recent Analysis History
# ==================================================

st.divider()

st.subheader(
    "6. Recent Analysis History"
)

try:

    history = get_analysis_history(
        limit=100
    )

    if history:

        history_df = pd.DataFrame(
            history
        )

        history_df[
            "requested_asset_types"
        ] = history_df[
            "requested_asset_types"
        ].apply(
            normalize_asset_array
        )

        history_df[
            "requested_assets_display"
        ] = history_df[
            "requested_asset_types"
        ].apply(
            lambda assets:
                ", ".join(
                    ASSET_LABELS.get(
                        asset,
                        asset,
                    )
                    for asset in assets
                )
        )


        # --------------------------------------------------
        # History Filters
        # --------------------------------------------------

        st.markdown(
            "### Filter Analysis History"
        )

        helper_text(
            "Filter previously saved analysis runs. "
            "The filters affect only the displayed report "
            "and do not modify stored database history."
        )

        filter_col1, filter_col2 = (
            st.columns(2)
        )

        road_options = [
            "All Roads"
        ] + sorted(
            history_df[
                "street_name"
            ]
            .dropna()
            .unique()
            .tolist()
        )

        with filter_col1:

            history_road_filter = (
                st.selectbox(
                    "Road",
                    options=road_options,
                )
            )

        with filter_col2:

            history_asset_filter = (
                st.selectbox(
                    "Asset type",
                    options=[
                        "all"
                    ] + ALLOWED_ASSET_TYPES,
                    format_func=lambda asset:
                        (
                            "All Asset Types"
                            if asset == "all"
                            else ASSET_LABELS[asset]
                        ),
                )
            )


        filtered_history = (
            history_df.copy()
        )

        if (
            history_road_filter
            != "All Roads"
        ):

            filtered_history = (
                filtered_history[
                    filtered_history[
                        "street_name"
                    ]
                    == history_road_filter
                ]
            )

        if (
            history_asset_filter
            != "all"
        ):

            filtered_history = (
                filtered_history[
                    filtered_history[
                        "requested_asset_types"
                    ].apply(
                        lambda assets:
                            history_asset_filter
                            in assets
                    )
                ]
            )


        # --------------------------------------------------
        # Saved Analysis Runs
        # --------------------------------------------------

        if filtered_history.empty:

            st.info(
                "No analysis runs match the selected filters."
            )

        else:

            st.markdown(
                "### Saved Analysis Runs"
            )

            if (
                history_asset_filter
                == "all"
            ):

                display_history = pd.DataFrame(
                    {
                        "Run ID":
                            filtered_history[
                                "analysis_id"
                            ].apply(
                                format_identifier
                            ),

                        "Road":
                            filtered_history[
                                "street_name"
                            ],

                        "Distance (m)":
                            filtered_history[
                                "distance_m"
                            ].apply(
                                lambda value:
                                    f"{float(value):.0f}"
                            ),

                        "Requested Assets":
                            filtered_history[
                                "requested_assets_display"
                            ],

                        "Requested Total":
                            filtered_history[
                                "requested_total"
                            ].apply(
                                lambda value:
                                    str(int(value))
                            ),

                        "Created At":
                            pd.to_datetime(
                                filtered_history[
                                    "created_at"
                                ]
                            ).dt.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                    }
                )

                center_columns = [
                    "Run ID",
                    "Distance (m)",
                    "Requested Total",
                    "Created At",
                ]

            else:

                selected_count_column = (
                    ASSET_COUNT_COLUMNS[
                        history_asset_filter
                    ]
                )

                selected_asset_label = (
                    ASSET_LABELS[
                        history_asset_filter
                    ]
                )

                count_label = (
                    f"{selected_asset_label} Count"
                )

                display_history = pd.DataFrame(
                    {
                        "Run ID":
                            filtered_history[
                                "analysis_id"
                            ].apply(
                                format_identifier
                            ),

                        "Road":
                            filtered_history[
                                "street_name"
                            ],

                        "Distance (m)":
                            filtered_history[
                                "distance_m"
                            ].apply(
                                lambda value:
                                    f"{float(value):.0f}"
                            ),

                        "Requested Assets":
                            filtered_history[
                                "requested_assets_display"
                            ],

                        count_label:
                            filtered_history[
                                selected_count_column
                            ].apply(
                                lambda value:
                                    str(int(value))
                            ),

                        "Created At":
                            pd.to_datetime(
                                filtered_history[
                                    "created_at"
                                ]
                            ).dt.strftime(
                                "%Y-%m-%d %H:%M"
                            ),
                    }
                )

                center_columns = [
                    "Run ID",
                    "Distance (m)",
                    count_label,
                    "Created At",
                ]

            render_professional_table(
                dataframe=display_history,
                center_columns=center_columns,
                max_height=400,
            )


            # --------------------------------------------------
            # Full Spatial Calculation
            # --------------------------------------------------

            with st.expander(
                "View Full Spatial Calculation Details"
            ):

                helper_text(
                    "This section shows the complete background "
                    "spatial calculation for each run, including "
                    "asset types that were not requested by the user."
                )

                full_history = pd.DataFrame(
                    {
                        "Run ID":
                            filtered_history[
                                "analysis_id"
                            ].apply(
                                format_identifier
                            ),

                        "Road":
                            filtered_history[
                                "street_name"
                            ],

                        "Buildings":
                            filtered_history[
                                "buildings_count"
                            ].astype(int).astype(str),

                        "Hydrants":
                            filtered_history[
                                "hydrants_count"
                            ].astype(int).astype(str),

                        "Street Lights":
                            filtered_history[
                                "street_lights_count"
                            ].astype(int).astype(str),

                        "Catchbasins":
                            filtered_history[
                                "catchbasins_count"
                            ].astype(int).astype(str),
                    }
                )

                render_professional_table(
                    dataframe=full_history,
                    center_columns=[
                        "Run ID",
                        "Road",
                        "Buildings",
                        "Hydrants",
                        "Street Lights",
                        "Catchbasins",
                    ],
                    max_height=350,
                )


            # ==================================================
            # Historical Run Drill-down
            # ==================================================

            st.markdown(
                "### Historical Run Details"
            )

            helper_text(
                "Select a saved analysis run to reconstruct "
                "its requested asset details using the current "
                "PostGIS asset data."
            )

            run_options = (
                filtered_history[
                    "analysis_id"
                ].astype(int).tolist()
            )

            def format_run_option(
                analysis_id
            ):

                row = filtered_history[
                    filtered_history[
                        "analysis_id"
                    ]
                    == analysis_id
                ].iloc[0]

                return (
                    f"Run {analysis_id} — "
                    f"{row['street_name']} — "
                    f"{float(row['distance_m']):.0f} m — "
                    f"{row['requested_assets_display']}"
                )

            selected_historical_run = (
                st.selectbox(
                    "Analysis run",
                    options=run_options,
                    format_func=format_run_option,
                )
            )

            if st.button(
                "Load Historical Run Details"
            ):

                try:

                    run_context = (
                        get_analysis_run_context(
                            selected_historical_run
                        )
                    )

                    reconstructed_assets = (
                        get_affected_assets(
                            geometry_wkt=run_context[
                                "geometry_wkt"
                            ],
                            distance_m=float(
                                run_context[
                                    "distance_m"
                                ]
                            ),
                            asset_types=list(
                                run_context[
                                    "requested_asset_types"
                                ]
                            ),
                        )
                    )

                    st.session_state.historical_run_context = (
                        run_context
                    )

                    st.session_state.historical_run_assets = (
                        reconstructed_assets
                    )

                except Exception as error:

                    st.error(
                        f"Could not load historical run details: "
                        f"{error}"
                    )


            historical_context = (
                st.session_state.historical_run_context
            )

            historical_assets = (
                st.session_state.historical_run_assets
            )

            if (
                historical_context
                and historical_assets
            ):

                st.divider()

                st.markdown(
                    f"### Reconstructed Run "
                    f"{historical_context['analysis_id']}"
                )

                requested_types = list(
                    historical_context[
                        "requested_asset_types"
                    ]
                )

                requested_labels = ", ".join(
                    ASSET_LABELS[
                        asset_type
                    ]
                    for asset_type in requested_types
                )

                st.html(
                    f"""
                    <div class="history-note">
                        <strong>Road:</strong>
                        {html.escape(
                            historical_context['street_name']
                        )}
                        &nbsp;&nbsp;|&nbsp;&nbsp;

                        <strong>Distance:</strong>
                        {float(
                            historical_context['distance_m']
                        ):.0f} m
                        &nbsp;&nbsp;|&nbsp;&nbsp;

                        <strong>Requested assets:</strong>
                        {html.escape(requested_labels)}
                    </div>
                    """
                )


                # --------------------------------------------------
                # Compare Saved Counts With Reconstruction
                # --------------------------------------------------

                mismatches = []

                for asset_type in requested_types:

                    saved_count = int(
                        historical_context[
                            ASSET_COUNT_COLUMNS[
                                asset_type
                            ]
                        ]
                    )

                    current_count = len(
                        historical_assets[
                            asset_type
                        ]
                    )

                    if (
                        saved_count
                        != current_count
                    ):

                        mismatches.append(
                            (
                                asset_type,
                                saved_count,
                                current_count,
                            )
                        )

                if mismatches:

                    mismatch_text = "; ".join(
                        (
                            f"{ASSET_LABELS[asset_type]}: "
                            f"saved {saved_count}, "
                            f"current {current_count}"
                        )
                        for (
                            asset_type,
                            saved_count,
                            current_count,
                        )
                        in mismatches
                    )

                    st.warning(
                        "Current asset data differs from the "
                        "original saved run summary. "
                        + mismatch_text
                    )

                else:

                    st.success(
                        "The reconstructed asset counts match "
                        "the original saved run."
                    )


                # --------------------------------------------------
                # Historical Detail Tabs
                # --------------------------------------------------

                historical_tabs = st.tabs(
                    [
                        (
                            f"{ASSET_LABELS[asset_type]} "
                            f"({len(historical_assets[asset_type])})"
                        )
                        for asset_type
                        in requested_types
                    ]
                )

                for (
                    tab,
                    asset_type,
                ) in zip(
                    historical_tabs,
                    requested_types,
                ):

                    with tab:

                        st.markdown(
                            f"### "
                            f"{ASSET_LABELS[asset_type]} Details"
                        )

                        helper_text(
                            "These records were reconstructed "
                            "from the current database using the "
                            "road segment, distance and asset types "
                            "stored with the selected analysis run."
                        )

                        (
                            historical_table,
                            historical_center_columns,
                        ) = prepare_asset_display_table(
                            historical_assets[
                                asset_type
                            ]
                        )

                        render_professional_table(
                            dataframe=historical_table,
                            center_columns=(
                                historical_center_columns
                            ),
                            max_height=430,
                        )

    else:

        st.info(
            "No analysis history is available yet."
        )

except Exception as error:

    st.error(
        f"Could not load analysis history: {error}"
    )