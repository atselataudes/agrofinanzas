import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    PAGE_TITLE = "AgroFinanzas Pro"
    PAGE_ICON = "🥑"
    LAYOUT = "wide"
    # En Railway: monta un volumen en /data y define DB_PATH=/data/agro.db
    # En local:   usa la carpeta del proyecto (comportamiento original)
    DB_NAME = os.environ.get("DB_PATH", os.path.join(_BASE_DIR, "agro_finanzas_pro.db"))
    UPLOAD_FOLDER = os.environ.get("UPLOAD_PATH", os.path.join(_BASE_DIR, "comprobantes"))
    
    # UI Colors
    COLOR_PRIMARY = "#2e7d32"
    COLOR_SECONDARY = "#1976d2"
    COLOR_DEBT = "#d32f2f"
    
    @staticmethod
    def setup_folders():
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
