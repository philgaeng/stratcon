from pathlib import Path

import pytz

# Data quality thresholds
MAX_MISSING_DAYS_PER_MONTH = 5
MAX_CONSECUTIVE_MISSING_TIMESTAMPS = 2
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_HOUR = 0.20
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_DAY = 0.05
MAX_PERCENTAGE_MISSING_TIMESTAMPS_PER_MONTH = 0.01

# Time classifications
WEEKDAYS = [0, 1, 2, 3, 4]  # Monday to Friday
HOURS = list(range(24))  # 0-23
NIGHT_HOURS = [22, 23, 0, 1, 2, 3, 4, 5]
DAY_HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17]

# Environmental constants
CO2_EMISSIONS_PER_KWH = 0.038  # kgCO2e/kWh

# Timezone configuration
PHILIPPINES_TZ = pytz.timezone('Asia/Manila')

# Default client
DEFAULT_CLIENT = "NEO"

# Default paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOGS_DIR = str(_PROJECT_ROOT / "logs")
DEFAULT_REPORTS_DIR = "/home/philg/projects/stratcon/reports"
DEFAULT_RESOURCES_DIR = "/home/philg/projects/stratcon/resources/logos"
SOURCE_TYPES = ["meter_records", "building", "epc", "client"]


def verify_source_type(source: str = "meter_records") -> str:
    """
    Validate that a given source value is supported by the service layer.

    Args:
        source: The source string to validate.

    Returns:
        The validated source string (useful for fluent-style usage).

    Raises:
        ValueError: If the provided source is not part of SOURCE_TYPES.
    """
    if source not in SOURCE_TYPES:
        allowed = ", ".join(SOURCE_TYPES)
        raise ValueError(f"Invalid source '{source}'. Allowed source types: {allowed}.")
    return source

class ReportStyle:
    # Colors
    CONSUMPTION_COLOR = '#f5b041'   # orange
    PRODUCTION_COLOR = '#76b7b2'    # teal/light green
    IMPORT_COLOR = '#4e79a7'        # blue
    EXPORT_COLOR = '#333333'        # dark gray/black
    STRATCON_DARK_GREEN = '#2E7D32'
    STRATCON_MEDIUM_GREEN = '#388E3C'
    STRATCON_PRIMARY_GREEN = '#4CAF50'
    STRATCON_LIGHT_GREEN = '#8BC34A'
    STRATCON_YELLOW = '#FFEB3B'
    
    # Grey shades
    STRATCON_BLACK = '#333'
    STRATCON_DARK_GREY = '#2c3e50'
    STRATCON_MEDIUM_GREY = '#666'
    STRATCON_GREY = '#888'
    STRATCON_LIGHT_GREY = '#7f8c8d'
    STRATCON_VERY_LIGHT_GREY = '#bdc3c7'

    # Font families
    HEADING_FONT_FAMILY = "Montserrat, Arial, sans-serif"
    BODY_FONT_FAMILY = "Inter, sans-serif"

    # Font sizes
    FONT_SIZE = 14
    H1_FONT_SIZE = 24
    H2_FONT_SIZE = 20
    H3_FONT_SIZE = 18

    # For HTML
    HTML_FONT_STYLE = f"font-family:{BODY_FONT_FAMILY}; font-size:{FONT_SIZE}px;"
    HTML_H1_STYLE = f"font-family:{HEADING_FONT_FAMILY}; font-size:{H1_FONT_SIZE}px; font-weight:bold;"
    HTML_H2_STYLE = f"font-family:{HEADING_FONT_FAMILY}; font-size:{H2_FONT_SIZE}px; font-weight:bold;"
    HTML_H3_STYLE = f"font-family:{BODY_FONT_FAMILY}; font-size:{H3_FONT_SIZE}px; font-weight:bold;"

class PlotlyStyle:
    CONSUMPTION_COLOR = ReportStyle.CONSUMPTION_COLOR
    PRODUCTION_COLOR = ReportStyle.PRODUCTION_COLOR
    IMPORT_COLOR = ReportStyle.IMPORT_COLOR
    EXPORT_COLOR = ReportStyle.EXPORT_COLOR
    STRATCON_DARK_GREEN = ReportStyle.STRATCON_DARK_GREEN
    STRATCON_MEDIUM_GREEN = ReportStyle.STRATCON_MEDIUM_GREEN
    STRATCON_PRIMARY_GREEN = ReportStyle.STRATCON_PRIMARY_GREEN
    STRATCON_LIGHT_GREEN = ReportStyle.STRATCON_LIGHT_GREEN
    STRATCON_YELLOW = ReportStyle.STRATCON_YELLOW
    STRATCON_BLACK = ReportStyle.STRATCON_BLACK
    STRATCON_DARK_GREY = ReportStyle.STRATCON_DARK_GREY
    STRATCON_MEDIUM_GREY = ReportStyle.STRATCON_MEDIUM_GREY
    STRATCON_GREY = ReportStyle.STRATCON_GREY
    STRATCON_LIGHT_GREY = ReportStyle.STRATCON_LIGHT_GREY
    STRATCON_VERY_LIGHT_GREY = ReportStyle.STRATCON_VERY_LIGHT_GREY

    BODY_FONT_FAMILY = ReportStyle.BODY_FONT_FAMILY
    HEADING_FONT_FAMILY = ReportStyle.HEADING_FONT_FAMILY
    BODY_FONT_SIZE = ReportStyle.FONT_SIZE
    TITLE_FONT_SIZE = ReportStyle.H2_FONT_SIZE
    update_font = dict(family=BODY_FONT_FAMILY, size=BODY_FONT_SIZE)
    update_title_font = dict(family=HEADING_FONT_FAMILY, size=TITLE_FONT_SIZE)
        

