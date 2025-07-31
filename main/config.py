class ReportStyle:
    # Colors
    CONSUMPTION_COLOR = '#f5b041'   # orange
    PRODUCTION_COLOR = '#76b7b2'    # teal/light green
    IMPORT_COLOR = '#4e79a7'        # blue
    EXPORT_COLOR = '#333333'        # dark gray/black

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

    BODY_FONT_FAMILY = ReportStyle.BODY_FONT_FAMILY
    HEADING_FONT_FAMILY = ReportStyle.HEADING_FONT_FAMILY
    BODY_FONT_SIZE = ReportStyle.FONT_SIZE
    TITLE_FONT_SIZE = ReportStyle.H2_FONT_SIZE
    update_font = dict(family=BODY_FONT_FAMILY, size=BODY_FONT_SIZE)
    update_title_font = dict(family=HEADING_FONT_FAMILY, size=TITLE_FONT_SIZE)
        