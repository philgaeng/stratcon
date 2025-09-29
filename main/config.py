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
        