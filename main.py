import sys
import os
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QDialog, QFrame, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWebEngineWidgets import QWebEngineView

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_data_dir():
    data_dir = os.path.join(get_app_dir(), 'DATA')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

DATA_DIR = get_data_dir()
CLIENT_SECRETS_FILE = os.path.join(DATA_DIR, 'client_secret.json')
TOKEN_FILE = os.path.join(DATA_DIR, 'token.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
SPREADSHEET_ID = "1lCQNIikEVragvoO-CzWi_LLb_Ybf-qvXpmusPnrCGqM"

GITHUB_REPO = "djstarman80/TallerApp"
GITHUB_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            return json.load(open(CONFIG_FILE))
        except:
            return {}
    return {}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


DRIVE_FILE_ID = "1gTJGi_voYACOJkLUbAuHoBjuQYVM8yDV"


def get_remote_version(sheets):
    print("[DEBUG] Obteniendo versión remota...")
    try:
        service = sheets.service
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="CONFIG!A:E"
        ).execute()
        values = result.get("values", [])
        print(f"[DEBUG] Datos recibidos de CONFIG: {values}")
        if len(values) >= 2 and len(values[1]) >= 5:
            version = values[1][4].strip()
            print(f"[DEBUG] Versión remota: {version}")
            return version
        print("[DEBUG] No se encontró versión en la segunda fila")
        return None
    except Exception as e:
        print(f"[DEBUG] Error getting remote version: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_for_updates(sheets):
    print("[DEBUG] Verificando actualizaciones...")
    local_config = load_config()
    local_version = local_config.get("version", "0.0.0")
    print(f"[DEBUG] Versión local: {local_version}")
    
    remote_version = get_remote_version(sheets)
    print(f"[DEBUG] Resultado get_remote_version: {remote_version}")
    
    if remote_version and remote_version != local_version:
        return {
            "available": True,
            "new_version": remote_version,
            "current_version": local_version
        }
    return {"available": False}


def download_and_update(parent=None):
    print("[DEBUG] Iniciando descarga de actualización desde GitHub...")
    try:
        import urllib.request
        import json
        
        print(f"[DEBUG] Obteniendo info de release: {GITHUB_RELEASE_URL}")
        
        req = urllib.request.Request(
            GITHUB_RELEASE_URL,
            headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            release_data = json.loads(response.read().decode())
        
        print(f"[DEBUG] Versión del release: {release_data.get('tag_name', 'unknown')}")
        
        download_url = None
        for asset in release_data.get('assets', []):
            if asset.get('name', '').lower() == 'tallerapp.exe':
                download_url = asset.get('browser_download_url')
                break
        
        if not download_url:
            print("[DEBUG] No se encontró TallerApp.exe en el release")
            QMessageBox.warning(parent, "Error", 
                "No se encontró el archivo TallerApp.exe en el release de GitHub")
            return
        
        print(f"[DEBUG] URL de descarga: {download_url}")
        
        temp_path = os.path.join(get_data_dir(), "TallerApp_new.exe")
        print(f"[DEBUG] Ruta temporal: {temp_path}")
        
        print("[DEBUG] Descargando archivo...")
        req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = response.read()
            print(f"[DEBUG] Bytes recibidos: {len(data)}")
            
            with open(temp_path, 'wb') as f:
                f.write(data)
        
        if os.path.exists(temp_path):
            file_size = os.path.getsize(temp_path)
            print(f"[DEBUG] Archivo descargado. Tamaño: {file_size} bytes")
        else:
            print("[DEBUG] ERROR: Archivo no existe después de descargar")
            QMessageBox.warning(parent, "Error", "No se pudo descargar el archivo")
            return
        
        current_exe = sys.executable
        print(f"[DEBUG] Ejecutable actual: {current_exe}")
        
        batch_path = os.path.join(get_data_dir(), "update.bat")
        print(f"[DEBUG] Creando batch en: {batch_path}")
        
        with open(batch_path, "w") as f:
            f.write(f"""@echo off
timeout /t 2 /nobreak >nul
copy /y "{temp_path}" "{current_exe}"
del "{temp_path}"
del "%~f0"
start "" "{current_exe}"
""")
        
        print("[DEBUG] Batch creado. Iniciando actualización...")
        QMessageBox.information(parent, "Actualización", 
            f"Actualización descargada ({file_size} bytes). La app se reiniciará...")
        os.startfile(batch_path)
        sys.exit(0)
        
    except Exception as e:
        print(f"[DEBUG] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        QMessageBox.warning(parent, "Error", f"Error al descargar: {str(e)}")


def get_sheet_names(credentials):
    try:
        service = build("sheets", "v4", credentials=credentials)
        result = service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()
        sheets = result.get("sheets", [])
        return [s.get("properties", {}).get("title", "Sheet1") for s in sheets]
    except:
        return ["Sheet1"]


def get_users_config(credentials):
    try:
        service = build("sheets", "v4", credentials=credentials)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="CONFIG!A:D"
        ).execute()
        values = result.get("values", [])
        if not values or len(values) < 2:
            return []
        headers = values[0]
        users = []
        for row in values[1:]:
            if row and len(row) > 0 and row[0].strip():
                user = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        user[header.strip()] = row[i].strip()
                    else:
                        user[header.strip()] = ""
                users.append(user)
        return users
    except Exception as e:
        print(f"Error getting config: {e}")
        return []


def get_config_password(credentials, email):
    try:
        users = get_users_config(credentials)
        for user in users:
            if user.get("MAIL", "").lower() == email.lower():
                return user.get("PASS", "")
        return ""
    except:
        return ""


def get_user_info(credentials, email):
    try:
        users = get_users_config(credentials)
        for user in users:
            if user.get("MAIL", "").lower() == email.lower():
                return {
                    "name": user.get("NOMBRE", email.split('@')[0]),
                    "category": user.get("CATEGORIA", "Técnico")
                }
        return {
            "name": email.split('@')[0],
            "category": "Técnico"
        }
    except:
        return {
            "name": email.split('@')[0],
            "category": "Técnico"
        }


COLUMNAS = [
    "ORDEN", "TECNICO", "FECHA PEDIDO", "ESTADO", 
    "FECHA COTIZADO", "ACEPTADO", "FECHA ACEPTADO", 
    "COMPRADO", "FECHA COMPRADO", "N° TICKET", "",
    "USUARIO COTIZO", "USUARIO COMPRO", "ULTIMO CAMBIO", ""
]


def get_short_name(email):
    return email.split('@')[0] if '@' in email else email


class GoogleSheets:
    def __init__(self, credentials=None, sheet_name=None):
        self.credentials = credentials
        self.service = None
        config = load_config()
        self.sheet_name = sheet_name or config.get("sheet_name") or self.get_first_sheet()
        if credentials:
            self.service = build("sheets", "v4", credentials=credentials)
            if not self.sheet_name or self.sheet_name not in get_sheet_names(credentials):
                self.sheet_name = self.get_first_sheet()

    def get_first_sheet(self):
        if not self.service:
            return "Sheet1"
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=SPREADSHEET_ID
            ).execute()
            sheets = result.get("sheets", [])
            if sheets:
                return sheets[0].get("properties", {}).get("title", "Sheet1")
        except:
            pass
        return "Sheet1"
    
    def set_sheet_name(self, sheet_name):
        self.sheet_name = sheet_name
        config = load_config()
        config["sheet_name"] = sheet_name
        save_config(config)

    def get_next_ticket_number(self):
        if not self.service:
            return 1
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{self.sheet_name}!A:K"
            ).execute()
            values = result.get("values", [])
            if not values or len(values) <= 1:
                return 1
            
            last_ticket = 0
            for row in values[1:]:
                if row and len(row) > 0 and row[0].strip():
                    if len(row) > 9 and row[9].strip():
                        try:
                            ticket = int(row[9])
                            if ticket > last_ticket:
                                last_ticket = ticket
                        except:
                            pass
            
            return last_ticket + 1
        except Exception as e:
            print(f"Error getting ticket: {e}")
            return 1

    def get_all_data(self):
        if not self.service:
            return []
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{self.sheet_name}!A:N"
            ).execute()
            values = result.get("values", [])
            if not values:
                return []
            headers = COLUMNAS
            data = []
            for row in values[1:]:
                row_dict = {}
                for i, header in enumerate(headers):
                    row_dict[header] = row[i] if i < len(row) else ""
                data.append(row_dict)
            return data
        except Exception as e:
            print(f"Error getting data: {e}")
            return []

    def append_row(self, row_data):
        if not self.service:
            return False
        try:
            result = self.service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{self.sheet_name}!A:A",
                valueInputOption="USER_ENTERED",
                body={"values": [row_data]}
            ).execute()
            return True
        except Exception as e:
            print(f"Error appending row: {e}")
            return False

    def find_empty_row(self):
        if not self.service:
            return None
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{self.sheet_name}!A:A"
            ).execute()
            values = result.get("values", [])
            for idx, row in enumerate(values[1:], start=2):
                if not row or len(row) < 1 or not row[0].strip():
                    return idx
            return None
        except Exception as e:
            print(f"Error finding empty row: {e}")
            return None

    def update_row(self, row_index, row_data):
        if not self.service:
            return False
        try:
            cell_range = f"{self.sheet_name}!A{row_index}:N{row_index}"
            self.service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=cell_range,
                valueInputOption="USER_ENTERED",
                body={"values": [row_data]}
            ).execute()
            return True
        except Exception as e:
            print(f"Error updating row: {e}")
            return False


def get_user_email(credentials):
    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info.get("email", "")
    except Exception as e:
        print(f"Error getting email: {e}")
        return ""


class OAuthWindow(QDialog):
    auth_completed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Iniciar sesión con Google")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Por favor, espere...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.flow = None
        self.start_oauth()

    def start_oauth(self):
        client_secrets = get_client_secrets_path()
        if not client_secrets:
            QMessageBox.warning(
                self, "Error",
                "No se encontró client_secret.json\nBusque en la carpeta DATA/"
            )
            self.close()
            return

        try:
            self.flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets, SCOPES
            )
            
            self.label.setText("Abriendo navegador de Google...")
            
            self.flow.redirect_uri = "http://localhost"
            credentials = self.flow.run_local_server(
                port=8080,
                authorization_prompt_message="Por favor, autorice la aplicación en el navegador"
            )

            with open(TOKEN_FILE, "w") as token:
                token.write(credentials.to_json())

            self.auth_completed.emit(credentials.to_json())
            self.close()
            
        except Exception as e:
            print(f"Error en OAuth: {e}")
            self.label.setText(f"Error: {str(e)}")
            QMessageBox.warning(self, "Error", f"Error en autenticación: {e}")


def load_credentials():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as token:
                creds_dict = json.load(token)
            creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)
            if creds and creds.valid:
                return creds
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())
                return creds
        except Exception as e:
            print(f"Error loading credentials: {e}")
    return None


def get_client_secrets_path():
    if os.path.exists(CLIENT_SECRETS_FILE):
        return CLIENT_SECRETS_FILE
    fallback = os.path.join(get_app_dir(), 'client_secret.json')
    if os.path.exists(fallback):
        return fallback
    return None


class LoginWindow(QWidget):
    login_successful = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Taller - Login")
        self.setMinimumSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        title = QLabel("Sistema de Pedidos")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Ingrese con su cuenta Google")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.login_btn = QPushButton("Iniciar sesión con Google")
        self.login_btn.setMinimumHeight(50)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                font-size: 16px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #3574E8;
            }
        """)
        self.login_btn.clicked.connect(self.start_login)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.login_btn)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.setLayout(layout)

    def start_login(self):
        self.login_btn.setEnabled(False)
        self.status_label.setText("Abriendo navegador...")

        self.oauth_window = OAuthWindow()
        self.oauth_window.auth_completed.connect(self.on_auth_success)
        self.oauth_window.show()

    def on_auth_success(self, credentials_json):
        creds = Credentials.from_authorized_user_info(
            json.loads(credentials_json), SCOPES
        )
        email = get_user_email(creds)
        self.login_successful.emit(credentials_json, email)
        self.status_label.setText("Login exitoso!")


class RoleSelectorWindow(QWidget):
    role_selected = pyqtSignal(str, str)

    def __init__(self, email):
        super().__init__()
        self.email = email
        self.setWindowTitle("Seleccionar Rol")
        self.setMinimumSize(400, 250)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        title = QLabel(f"Bienvenido\n{self.email}")
        title.setStyleSheet("font-size: 18px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Seleccione su rol:")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tecnico_btn = QPushButton("Técnico")
        self.tecnico_btn.setMinimumHeight(60)
        self.tecnico_btn.setStyleSheet("""
            QPushButton {
                background-color: #34A853;
                color: white;
                font-size: 18px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2E8B47;
            }
        """)
        self.tecnico_btn.clicked.connect(lambda: self.select_role("Tecnico"))

        self.compras_btn = QPushButton("Compras")
        self.compras_btn.setMinimumHeight(60)
        self.compras_btn.setStyleSheet("""
            QPushButton {
                background-color: #EA4335;
                color: white;
                font-size: 18px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #C62828;
            }
        """)
        self.compras_btn.clicked.connect(lambda: self.select_role("Compras"))

        logout_btn = QPushButton("Cerrar sesión")
        logout_btn.clicked.connect(self.logout)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.tecnico_btn)
        layout.addWidget(self.compras_btn)
        layout.addStretch()
        layout.addWidget(logout_btn)
        layout.addStretch()

        self.setLayout(layout)

    def select_role(self, role):
        self.role_selected.emit(self.email, role)

    def logout(self):
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        QApplication.quit()


class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cambiar Hoja")
        self.setMinimumSize(300, 150)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        lbl = QLabel("Ingrese contraseña para cambiar de hoja:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Contraseña")
        
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.clicked.connect(self.accept)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        
        layout.addWidget(lbl)
        layout.addWidget(self.pass_input)
        layout.addLayout(btn_layout)
        self.setLayout(layout)


class NuevaCotizacionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Cotización")
        self.setMinimumSize(400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        lbl_orden = QLabel("Orden:")
        self.orden_input = QLineEdit()
        self.orden_input.setPlaceholderText("Ingrese el número de orden")
        
        layout.addWidget(lbl_orden)
        layout.addWidget(self.orden_input)
        
        btn_layout = QHBoxLayout()
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setStyleSheet("background-color: #34A853; color: white; font-weight: bold;")
        btn_guardar.clicked.connect(self.accept)
        
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_cancelar)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)


class TecnicoWindow(QWidget):
    logout_signal = pyqtSignal()
    
    OPCIONES_ESTADO = ["Cotizacion", "Cotizado", "Rechazado"]
    OPCIONES_SI_NO = ["Pendiente", "Aceptada", "Rechazada"]

    def __init__(self, email, user_name, sheets_service):
        super().__init__()
        self.email = email
        self.user_name = user_name
        self.sheets = sheets_service
        self.data = []
        self.row_map = {}
        self.cambios = {}
        self.last_data_count = 0
        self.setWindowTitle("Técnico - Pedidos")
        self.setMinimumSize(1100, 600)
        self.filtro_actual = "Todos"
        self.filtro_tecnico = "Todos los Técnicos"
        self.setup_ui()
        self.load_data()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(10000)

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header = QLabel(f"Técnico: {self.user_name}")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        version_label = QLabel("MP@Soft V 1.1")
        version_label.setStyleSheet("font-size: 10px; color: gray;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        header_layout.addWidget(header)
        header_layout.addWidget(version_label)
        header_widget.setLayout(header_layout)
        
        self.filtro_combo = QComboBox()
        self.filtro_combo.addItems(["Todos", "Pendientes", "Cotizados", "Aceptados", "Rechazados", "Comprar"])
        self.filtro_combo.currentTextChanged.connect(self.on_filtro_changed)

        self.filtro_tecnico_combo = QComboBox()
        self.filtro_tecnico_combo.addItems(["Todos los Técnicos"])
        self.filtro_tecnico_combo.currentTextChanged.connect(self.on_tecnico_changed)
        
        self.filtro_hoja_combo = QComboBox()
        self.filtro_hoja_combo.currentTextChanged.connect(self.on_hoja_changed)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_data)

        logout_btn = QPushButton("Cerrar sesión")
        logout_btn.clicked.connect(self.logout_signal.emit)

        nuevo_btn = QPushButton("➕ Nueva Cotización")
        nuevo_btn.setStyleSheet("background-color: #34A853; color: white; font-weight: bold; padding: 8px;")
        nuevo_btn.clicked.connect(self.nuevo_pedido)

        guardar_btn = QPushButton("💾 Guardar cambios")
        guardar_btn.setStyleSheet("background-color: #4285F4; color: white; font-weight: bold; padding: 8px;")
        guardar_btn.clicked.connect(self.guardar_cambios)
        
        btn_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QLabel("Hoja:"))
        btn_layout.addWidget(self.filtro_hoja_combo)
        btn_layout.addWidget(QLabel("Técnico:"))
        btn_layout.addWidget(self.filtro_tecnico_combo)
        btn_layout.addWidget(QLabel("Estado:"))
        btn_layout.addWidget(self.filtro_combo)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(nuevo_btn)
        btn_layout.addWidget(guardar_btn)
        btn_layout.addWidget(logout_btn)
        btn_widget.setLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(15)
        headers = COLUMNAS + [""]
        self.table.setHorizontalHeaderLabels(headers)
        
        for i in range(10):
            self.table.setColumnWidth(i, 100)
        self.table.setColumnWidth(10, 30)
        self.table.setColumnWidth(11, 100)
        self.table.setColumnWidth(12, 100)
        self.table.setColumnWidth(13, 100)
        self.table.setColumnWidth(14, 80)

        layout.addWidget(header_widget)
        layout.addWidget(btn_widget)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def nuevo_pedido(self):
        dialog = NuevaCotizacionDialog(self)
        if dialog.exec():
            orden = dialog.orden_input.text().strip()
            if not orden:
                QMessageBox.warning(self, "Error", "Debe ingresar una Orden")
                return
            
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            ticket = self.sheets.get_next_ticket_number()
            
            row_data = [
                orden,
                self.user_name,
                fecha,
                "Cotizacion",
                "",
                "Pendiente",
                "",
                "Pendiente",
                "",
                str(ticket),
                "",  # USUARIO COTIZO
                "",  # USUARIO COMPRO
                ""   # ULTIMO CAMBIO
            ]

            empty_row = self.sheets.find_empty_row()
            if empty_row:
                if self.sheets.update_row(empty_row, row_data):
                    QMessageBox.information(self, "Éxito", f"Cotización creada con Ticket #{ticket}")
                    self.load_data()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo crear la cotización")
            else:
                if self.sheets.append_row(row_data):
                    QMessageBox.information(self, "Éxito", f"Cotización creada con Ticket #{ticket}")
                    self.load_data()
                else:
                    QMessageBox.critical(self, "Error", "No se pudo crear la cotización")

    def editar_pedido(self, row_idx):
        QMessageBox.information(self, "Editar", "Función de editar en desarrollo")

    def borrar_pedido(self, row_idx):
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Está seguro de eliminar esta cotización?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            original_row = self.row_map.get(row_idx)
            if original_row is None:
                return
            
            empty_row = [""] * 14
            if self.sheets.update_row(original_row, empty_row):
                QMessageBox.information(self, "Éxito", "Cotización eliminada")
                self.load_data()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar la cotización")

    def on_combo_changed(self, row, col, text):
        if row not in self.cambios:
            self.cambios[row] = {}
        self.cambios[row][col] = text

    def guardar_cambios(self):
        if not self.cambios:
            QMessageBox.information(self, "Info", "No hay cambios para guardar")
            return
        
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        nombre_corto = self.user_name
        guardados = 0
        
        for row_idx, cambios in self.cambios.items():
            original_row = self.row_map.get(row_idx)
            if original_row is None:
                continue
            
            data_idx = original_row - 2
            if data_idx >= len(self.data):
                continue
            
            current_data = self.data[data_idx]
            
            estado = current_data.get("ESTADO", "")
            aceptado = cambios.get(5, current_data.get("ACEPTADO", ""))
            purchased = current_data.get("COMPRADO", "")
            
            fecha_cotizado = current_data.get("FECHA COTIZADO", "")
            usuario_cotizo = current_data.get("USUARIO COTIZO", "")
            
            if estado == "Cotizado" and current_data.get("ESTADO", "") != "Cotizado":
                fecha_cotizado = fecha
                usuario_cotizo = nombre_corto
            
            fecha_aceptado = current_data.get("FECHA ACEPTADO", "")
            if aceptado == "Aceptada" and current_data.get("ACEPTADO", "") != "Aceptada":
                fecha_aceptado = fecha
            
            fecha_comprado = current_data.get("FECHA COMPRADO", "")
            
            updated_row = [
                current_data.get("ORDEN", ""),
                current_data.get("TECNICO", ""),
                current_data.get("FECHA PEDIDO", ""),
                estado,
                fecha_cotizado,
                aceptado,
                fecha_aceptado,
                purchased,
                fecha_comprado,
                current_data.get("N° TICKET", ""),
                "",  # Columna K vacía
                usuario_cotizo,
                current_data.get("USUARIO COMPRO", ""),
                current_data.get("ULTIMO CAMBIO", "")
            ]
            
            if self.sheets.update_row(original_row, updated_row):
                guardados += 1
        
        self.cambios = {}
        QMessageBox.information(self, "Éxito", f"Se guardaron {guardados} cambio(s)")
        self.load_data()

    def toggle_aceptado(self, row_idx):
        # Verificar que ESTADO permita cambiar ACEPTADO
        estado_widget = self.table.cellWidget(row_idx, 3)
        if estado_widget:
            estado = estado_widget.text()
            if estado != "Cotizado":
                QMessageBox.warning(self, "No permitido", 
                    "Solo se puede cambiar ACEPTADO cuando ESTADO está en Cotizado")
                return
        
        widget = self.table.cellWidget(row_idx, 5)
        if not widget:
            return
        current_aceptado = widget.text()
        idx = self.OPCIONES_SI_NO.index(current_aceptado) if current_aceptado in self.OPCIONES_SI_NO else 0
        next_idx = (idx + 1) % len(self.OPCIONES_SI_NO)
        nuevo_aceptado = self.OPCIONES_SI_NO[next_idx]
        
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][5] = nuevo_aceptado
        
        btn = self.table.cellWidget(row_idx, 5)
        btn.setText(nuevo_aceptado)
        btn.setStyleSheet(self.get_aceptado_style(nuevo_aceptado))
        
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.RightButton:
            for row_idx in range(self.table.rowCount()):
                btn = self.table.cellWidget(row_idx, 5)
                if btn == obj:
                    self.mostrar_menu_aceptado(row_idx)
                    return True
                btn_estado = self.table.cellWidget(row_idx, 3)
                if btn_estado == obj:
                    self.mostrar_menu_estado(row_idx)
                    return True
                btn_comprado = self.table.cellWidget(row_idx, 7)
                if btn_comprado == obj:
                    self.mostrar_menu_comprado(row_idx)
                    return True
        return super().eventFilter(obj, event)

    def mostrar_menu_aceptado(self, row_idx):
        menu = QMenu(self)
        for opcion in self.OPCIONES_SI_NO:
            action = menu.addAction(opcion)
            action.triggered.connect(lambda checked, o=opcion, r=row_idx: self.seleccionar_aceptado(r, o))
        menu.exec(QCursor.pos())

    def mostrar_menu_estado(self, row_idx):
        menu = QMenu(self)
        for opcion in self.OPCIONES_ESTADO:
            action = menu.addAction(opcion)
            action.triggered.connect(lambda checked, o=opcion, r=row_idx: self.seleccionar_estado(r, o))
        menu.exec(QCursor.pos())

    def mostrar_menu_comprado(self, row_idx):
        menu = QMenu(self)
        for opcion in self.OPCIONES_SI_NO:
            action = menu.addAction(opcion)
            action.triggered.connect(lambda checked, o=opcion, r=row_idx: self.seleccionar_comprado(r, o))
        menu.exec(QCursor.pos())

    def seleccionar_aceptado(self, row_idx, valor):
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][5] = valor
        btn = self.table.cellWidget(row_idx, 5)
        btn.setText(valor)
        btn.setStyleSheet(self.get_aceptado_style(valor))
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")

    def seleccionar_estado(self, row_idx, valor):
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][3] = valor
        btn = self.table.cellWidget(row_idx, 3)
        btn.setText(valor)
        btn.setStyleSheet(self.get_estado_style(valor))
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")

    def seleccionar_comprado(self, row_idx, valor):
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][7] = valor
        btn = self.table.cellWidget(row_idx, 7)
        btn.setText(valor)
        btn.setStyleSheet(self.get_comprado_style(valor))
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")

    def populate_table(self):
        self.table.setRowCount(0)
        self.row_map = {}

        # Filtrar por técnico seleccionado
        if self.filtro_tecnico == "Todos los Técnicos":
            filtered_data = self.data
        else:
            filtro_lower = self.filtro_tecnico.lower()
            filtered_data = [
                row for row in self.data
                if row.get("TECNICO", "").lower() == filtro_lower
            ]
        
        # Aplicar filtro de estado para Técnico
        if self.filtro_actual == "Pendientes":
            filtered_data = [row for row in filtered_data if row.get("ESTADO", "") == "Cotizacion"]
        elif self.filtro_actual == "Cotizados":
            filtered_data = [row for row in filtered_data if row.get("ESTADO", "") == "Cotizado"]
        elif self.filtro_actual == "Aceptados":
            filtered_data = [row for row in filtered_data if row.get("ACEPTADO", "") == "Aceptada"]
        elif self.filtro_actual == "Rechazados":
            filtered_data = [row for row in filtered_data 
                if row.get("ACEPTADO", "") == "Rechazada" or row.get("ESTADO", "") == "Cancelado"]
        elif self.filtro_actual == "Comprar":
            filtered_data = [row for row in filtered_data if row.get("ACEPTADO", "") == "Aceptada" and row.get("COMPRADO", "") == "Pendiente"]

        for row_idx, row in enumerate(filtered_data):
            original_idx = self.data.index(row)
            self.row_map[row_idx] = original_idx + 2

            self.table.insertRow(row_idx)
            
            orden_roja, fecha_aceptado_roja = self.verificar_vencimiento(row)
            
            self.table.setItem(row_idx, 0, QTableWidgetItem(row.get("ORDEN", "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(row.get("TECNICO", "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(row.get("FECHA PEDIDO", "")))
            
            if orden_roja and self.table.item(row_idx, 0):
                self.table.item(row_idx, 0).setBackground(Qt.GlobalColor.red)
            
            # Orden, TECNICO, FECHA PEDIDO son solo lectura
            if self.table.item(row_idx, 0):
                self.table.item(row_idx, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
            if self.table.item(row_idx, 1):
                self.table.item(row_idx, 1).setFlags(Qt.ItemFlag.ItemIsEnabled)
            if self.table.item(row_idx, 2):
                self.table.item(row_idx, 2).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # ESTADO - solo lectura para Técnico (lo maneja Compras) - BOTON con color
            estado = row.get("ESTADO", "Cotizacion")
            btn_estado = QPushButton(estado)
            btn_estado.setFixedSize(90, 25)
            btn_estado.setStyleSheet(self.get_estado_style(estado))
            btn_estado.setEnabled(False)
            self.table.setCellWidget(row_idx, 3, btn_estado)
            
            # FECHA COTIZADO solo lectura
            self.table.setItem(row_idx, 4, QTableWidgetItem(row.get("FECHA COTIZADO", "")))
            if self.table.item(row_idx, 4):
                self.table.item(row_idx, 4).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # ACEPTADO - editable para Técnico (Pendiente, Aceptado, Rechazado) - BOTON
            aceptado = row.get("ACEPTADO", "Pendiente")
            btn_aceptado = QPushButton(aceptado)
            btn_aceptado.setFixedSize(90, 25)
            btn_aceptado.setStyleSheet(self.get_aceptado_style(aceptado))
            btn_aceptado.clicked.connect(lambda checked, r=row_idx: self.toggle_aceptado(r))
            btn_aceptado.installEventFilter(self)
            self.table.setCellWidget(row_idx, 5, btn_aceptado)
            
            # FECHA ACEPTADO solo lectura
            self.table.setItem(row_idx, 6, QTableWidgetItem(row.get("FECHA ACEPTADO", "")))
            if self.table.item(row_idx, 6):
                if fecha_aceptado_roja:
                    self.table.item(row_idx, 6).setBackground(Qt.GlobalColor.red)
                self.table.item(row_idx, 6).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # COMPRADO - solo lectura para Técnico (lo maneja Compras) - BOTON con color
            comprado = row.get("COMPRADO", "Pendiente")
            btn_comprado = QPushButton(comprado)
            btn_comprado.setFixedSize(90, 25)
            btn_comprado.setStyleSheet(self.get_comprado_style(comprado))
            btn_comprado.setEnabled(False)
            self.table.setCellWidget(row_idx, 7, btn_comprado)
            
            # FECHA COMPRADO y N° TICKET solo lectura
            self.table.setItem(row_idx, 8, QTableWidgetItem(row.get("FECHA COMPRADO", "")))
            if self.table.item(row_idx, 8):
                self.table.item(row_idx, 8).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_idx, 9, QTableWidgetItem(row.get("N° TICKET", "")))
            if self.table.item(row_idx, 9):
                self.table.item(row_idx, 9).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # USUARIO COTIZO, USUARIO COMPRO, ULTIMO CAMBIO
            self.table.setItem(row_idx, 11, QTableWidgetItem(row.get("USUARIO COTIZO", "")))
            if self.table.item(row_idx, 11):
                self.table.item(row_idx, 11).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_idx, 12, QTableWidgetItem(row.get("USUARIO COMPRO", "")))
            if self.table.item(row_idx, 12):
                self.table.item(row_idx, 12).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_idx, 13, QTableWidgetItem(row.get("ULTIMO CAMBIO", "")))
            if self.table.item(row_idx, 13):
                self.table.item(row_idx, 13).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # Botones de editar y borrar
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(30, 25)
            edit_btn.clicked.connect(lambda checked, r=row_idx: self.editar_pedido(r))
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 25)
            delete_btn.clicked.connect(lambda checked, r=row_idx: self.borrar_pedido(r))
            
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row_idx, 14, btn_widget)

            self.table.resizeColumnsToContents()
        
        status = f"Mostrando {len(filtered_data)} cotización(es)"
        self.table.setToolTip(status)

    def load_data(self):
        self.data = self.sheets.get_all_data()
        self.last_data_count = len(self.data)
        
        print(f"DEBUG: Cargo {len(self.data)} filas de la hoja {self.sheets.sheet_name}")
        
        hojas = get_sheet_names(self.sheets.credentials)
        self.filtro_hoja_combo.blockSignals(True)
        current = self.filtro_hoja_combo.currentText()
        self.filtro_hoja_combo.clear()
        self.filtro_hoja_combo.addItems(hojas)
        if current in hojas:
            self.filtro_hoja_combo.setCurrentText(current)
        else:
            self.filtro_hoja_combo.setCurrentText(self.sheets.sheet_name)
        self.filtro_hoja_combo.blockSignals(False)
        
        tecnicos = ["Todos los Técnicos"]
        tecnicos_set = set(row.get("TECNICO", "") for row in self.data if row.get("TECNICO", ""))
        tecnicos.extend(sorted(tecnicos_set))
        self.filtro_tecnico_combo.blockSignals(True)
        self.filtro_tecnico_combo.clear()
        self.filtro_tecnico_combo.addItems(tecnicos)
        if self.user_name in tecnicos:
            self.filtro_tecnico_combo.setCurrentText(self.user_name)
            self.filtro_tecnico = self.user_name
        else:
            self.filtro_tecnico_combo.setCurrentText("Todos los Técnicos")
            self.filtro_tecnico = "Todos los Técnicos"
        self.filtro_tecnico_combo.blockSignals(False)
        
        self.cambios = {}
        
        self.filtro_combo.blockSignals(True)
        self.filtro_combo.setCurrentText("Todos")
        self.filtro_actual = "Todos"
        self.filtro_combo.blockSignals(False)
        
        self.populate_table()

    def auto_refresh(self):
        scroll_pos = self.table.verticalScrollBar().value()
        
        old_count = self.last_data_count
        self.data = self.sheets.get_all_data()
        self.cambios = {}
        self.populate_table()
        
        self.table.verticalScrollBar().setValue(scroll_pos)
        
        if self.last_data_count > old_count:
            QMessageBox.information(self, "Actualizado", "Nuevo pedido detectado!")

    def get_estado_style(self, estado):
        if estado == "Cotizacion":
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        elif estado == "Cotizado":
            return "background-color: #ccffcc; color: #006600; font-weight: bold;"
        elif estado == "Cancelado":
            return "background-color: #ffcc99; color: #cc6600; font-weight: bold;"
        return ""

    def get_aceptado_style(self, aceptado):
        if aceptado == "Pendiente":
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        elif aceptado == "Aceptada":
            return "background-color: #ccffcc; color: #006600; font-weight: bold;"
        elif aceptado == "Rechazada":
            return "background-color: #ffcc99; color: #cc6600; font-weight: bold;"
        return ""

    def get_comprado_style(self, comprador):
        if comprador == "Pendiente":
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        elif comprador == "Aceptada":
            return "background-color: #ccffcc; color: #006600; font-weight: bold;"
        elif comprador == "Rechazada":
            return "background-color: #ffcc99; color: #cc6600; font-weight: bold;"
        return ""

    def verificar_vencimiento(self, row):
        fecha_cotizado = row.get("FECHA COTIZADO", "")
        estado = row.get("ESTADO", "")
        fecha_aceptado = row.get("FECHA ACEPTADO", "")
        aceptado = row.get("ACEPTADO", "")
        
        orden_roja = False
        fecha_aceptado_roja = False
        
        if estado == "Cotizacion" and fecha_cotizado:
            try:
                fecha = datetime.strptime(fecha_cotizado, "%Y-%m-%d %H:%M")
                if (datetime.now() - fecha).days > 2:
                    orden_roja = True
            except:
                pass
        
        if aceptado == "Pendiente" and fecha_aceptado:
            try:
                fecha = datetime.strptime(fecha_aceptado, "%Y-%m-%d %H:%M")
                if (datetime.now() - fecha).days > 2:
                    fecha_aceptado_roja = True
            except:
                pass
        
        return orden_roja, fecha_aceptado_roja

    def guardar_cambio(self, row_idx):
        original_row = self.row_map.get(row_idx)
        if original_row is None:
            return False
        
        data_idx = original_row - 2
        if data_idx >= len(self.data):
            return False
        
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        nombre_corto = self.user_name
        
        cambios = self.cambios.get(row_idx, {})
        
        current_data = self.data[data_idx]
        
        estado = current_data.get("ESTADO", "")
        aceptado = cambios.get(5, current_data.get("ACEPTADO", ""))
        purchased = current_data.get("COMPRADO", "")
        
        fecha_cotizado = current_data.get("FECHA COTIZADO", "")
        usuario_cotizo = current_data.get("USUARIO COTIZO", "")
        
        if estado == "Cotizado" and current_data.get("ESTADO", "") != "Cotizado":
            fecha_cotizado = fecha
            usuario_cotizo = nombre_corto
        
        fecha_aceptado = current_data.get("FECHA ACEPTADO", "")
        if aceptado == "Aceptada" and current_data.get("ACEPTADO", "") != "Aceptada":
            fecha_aceptado = fecha
        
        fecha_comprado = current_data.get("FECHA COMPRADO", "")
        
        updated_row = [
            current_data.get("ORDEN", ""),
            current_data.get("TECNICO", ""),
            current_data.get("FECHA PEDIDO", ""),
            estado,
            fecha_cotizado,
            aceptado,
            fecha_aceptado,
            purchased,
            fecha_comprado,
            current_data.get("N° TICKET", ""),
            "",  # Columna K vacía
            usuario_cotizo,
            current_data.get("USUARIO COMPRO", ""),
            current_data.get("ULTIMO CAMBIO", "")
        ]
        
        if self.sheets.update_row(original_row, updated_row):
            self.cambios.pop(row_idx, None)
            return True
        return False

    def toggle_estado(self, row_idx):
        widget = self.table.cellWidget(row_idx, 3)
        if not widget:
            return
        current_estado = widget.text()
        idx = self.OPCIONES_ESTADO.index(current_estado) if current_estado in self.OPCIONES_ESTADO else 0
        next_idx = (idx + 1) % len(self.OPCIONES_ESTADO)
        nuevo_estado = self.OPCIONES_ESTADO[next_idx]
        
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][3] = nuevo_estado
        
        btn = self.table.cellWidget(row_idx, 3)
        btn.setText(nuevo_estado)
        btn.setStyleSheet(self.get_estado_style(nuevo_estado))
        
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el cambio")

    def toggle_comprado(self, row_idx):
        widget = self.table.cellWidget(row_idx, 7)
        if not widget:
            return
        current_comprado = widget.text()
        idx = self.OPCIONES_SI_NO.index(current_comprado) if current_comprado in self.OPCIONES_SI_NO else 0
        next_idx = (idx + 1) % len(self.OPCIONES_SI_NO)
        nuevo_comprado = self.OPCIONES_SI_NO[next_idx]
        
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][7] = nuevo_comprado
        
        btn = self.table.cellWidget(row_idx, 7)
        btn.setText(nuevo_comprado)
        btn.setStyleSheet(self.get_comprado_style(nuevo_comprado))
        
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el cambio")

    def on_filtro_changed(self, texto):
        self.filtro_actual = texto
        self.populate_table()

    def on_tecnico_changed(self, texto):
        self.filtro_tecnico = texto
        self.populate_table()

    def on_hoja_changed(self, texto):
        password = get_config_password(self.sheets.credentials, self.email)
        if not password:
            password = "Taller"
        dialog = PasswordDialog(self)
        if dialog.exec():
            if dialog.pass_input.text() == password:
                self.sheets.set_sheet_name(texto)
                self.load_data()
                QMessageBox.information(self, "Éxito", f"Hoja cambiada a: {texto}")
            else:
                QMessageBox.warning(self, "Error", "Contraseña incorrecta")
                self.filtro_hoja_combo.setCurrentText(self.sheets.sheet_name)


class ComprasWindow(QWidget):
    logout_signal = pyqtSignal()
    
    OPCIONES_ESTADO = ["Cotizacion", "Cotizado", "Rechazado"]
    OPCIONES_SI_NO = ["Pendiente", "Aceptada", "Rechazada"]

    def __init__(self, email, user_name, sheets_service):
        super().__init__()
        self.email = email
        self.user_name = user_name
        self.sheets = sheets_service
        self.data = []
        self.row_map = {}
        self.cambios = {}
        self.last_data_count = 0
        self.setWindowTitle("Compras - Pedidos")
        self.setMinimumSize(1200, 600)
        self.filtro_actual = "Todos"
        self.filtro_tecnico = "Todos los Técnicos"
        self.setup_ui()
        self.load_data()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(10000)

    def on_filtro_changed(self, texto):
        self.filtro_actual = texto
        self.populate_table()

    def on_tecnico_changed(self, texto):
        self.filtro_tecnico = texto
        self.populate_table()

    def on_hoja_changed(self, texto):
        password = get_config_password(self.sheets.credentials, self.email)
        if not password:
            password = "Taller"
        dialog = PasswordDialog(self)
        if dialog.exec():
            if dialog.pass_input.text() == password:
                self.sheets.set_sheet_name(texto)
                self.load_data()
                QMessageBox.information(self, "Éxito", f"Hoja cambiada a: {texto}")
            else:
                QMessageBox.warning(self, "Error", "Contraseña incorrecta")
                self.filtro_hoja_combo.setCurrentText(self.sheets.sheet_name)

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header = QLabel(f"Compras: {self.user_name}")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        version_label = QLabel("MP@Soft V 1.1")
        version_label.setStyleSheet("font-size: 10px; color: gray;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        header_layout.addWidget(header)
        header_layout.addWidget(version_label)
        header_widget.setLayout(header_layout)

        self.filtro_combo = QComboBox()
        self.filtro_combo.addItems(["Todos", "Pendientes", "Cotizados", "Aceptados", "Rechazados", "Comprados", "Comprar"])
        self.filtro_combo.currentTextChanged.connect(self.on_filtro_changed)

        self.filtro_tecnico_combo = QComboBox()
        self.filtro_tecnico_combo.addItems(["Todos los Técnicos"])
        self.filtro_tecnico_combo.currentTextChanged.connect(self.on_tecnico_changed)

        self.filtro_hoja_combo = QComboBox()
        self.filtro_hoja_combo.currentTextChanged.connect(self.on_hoja_changed)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_data)

        guardar_btn = QPushButton("💾 Guardar cambios")
        guardar_btn.setStyleSheet("background-color: #34A853; color: white; font-weight: bold; padding: 8px;")
        guardar_btn.clicked.connect(self.guardar_cambios)
        
        logout_btn = QPushButton("Cerrar sesión")
        logout_btn.clicked.connect(self.logout_signal.emit)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QLabel("Hoja:"))
        btn_layout.addWidget(self.filtro_hoja_combo)
        btn_layout.addWidget(QLabel("Estado:"))
        btn_layout.addWidget(self.filtro_combo)
        btn_layout.addWidget(QLabel("Técnico:"))
        btn_layout.addWidget(self.filtro_tecnico_combo)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(guardar_btn)
        btn_layout.addWidget(logout_btn)
        btn_widget.setLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels(COLUMNAS)
        
        for i in range(10):
            self.table.setColumnWidth(i, 100)
        self.table.setColumnWidth(10, 30)
        self.table.setColumnWidth(11, 100)
        self.table.setColumnWidth(12, 100)
        self.table.setColumnWidth(13, 100)
        
        self.table.itemChanged.connect(self.on_cell_changed)

        layout.addWidget(header_widget)
        layout.addWidget(btn_widget)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def on_cell_changed(self, item):
        row = item.row()
        col = item.column()
        if col in [3, 5, 7]:
            if row not in self.cambios:
                self.cambios[row] = {}
            self.cambios[row][col] = item.text()

    def load_data(self):
        self.data = self.sheets.get_all_data()
        self.last_data_count = len(self.data)
        
        print(f"DEBUG: Cargo {len(self.data)} filas de la hoja {self.sheets.sheet_name}")
        
        hojas = get_sheet_names(self.sheets.credentials)
        self.filtro_hoja_combo.blockSignals(True)
        current = self.filtro_hoja_combo.currentText()
        self.filtro_hoja_combo.clear()
        self.filtro_hoja_combo.addItems(hojas)
        if current in hojas:
            self.filtro_hoja_combo.setCurrentText(current)
        else:
            self.filtro_hoja_combo.setCurrentText(self.sheets.sheet_name)
        self.filtro_hoja_combo.blockSignals(False)
        
        tecnicos = ["Todos los Técnicos"]
        tecnicos_set = set(row.get("TECNICO", "") for row in self.data if row.get("TECNICO", ""))
        tecnicos.extend(sorted(tecnicos_set))
        self.filtro_tecnico_combo.blockSignals(True)
        current_tecnico = self.filtro_tecnico_combo.currentText()
        self.filtro_tecnico_combo.clear()
        self.filtro_tecnico_combo.addItems(tecnicos)
        if current_tecnico in tecnicos:
            self.filtro_tecnico_combo.setCurrentText(current_tecnico)
        self.filtro_tecnico_combo.blockSignals(False)
        
        self.cambios = {}
        
        self.filtro_combo.blockSignals(True)
        self.filtro_combo.setCurrentText("Todos")
        self.filtro_actual = "Todos"
        self.filtro_combo.blockSignals(False)
        
        self.populate_table()

    def auto_refresh(self):
        scroll_pos = self.table.verticalScrollBar().value()
        
        old_data = self.data.copy()
        old_count = self.last_data_count
        self.data = self.sheets.get_all_data()
        self.cambios = {}
        
        # Usar N° TICKET como identificador único
        tickets_old = {row.get("N° TICKET", ""): row for row in old_data if row.get("N° TICKET", "")}
        
        for new_row in self.data:
            ticket = new_row.get("N° TICKET", "")
            # Solo verificar si hay cambios, sin notificaciones
            pass
        
        self.populate_table()
        
        self.table.verticalScrollBar().setValue(scroll_pos)
        
        if self.last_data_count > old_count:
            QMessageBox.information(self, "Actualizado", "Nuevo pedido detectado!")

    def get_estado_style(self, estado):
        if estado == "Cotizacion":
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        elif estado == "Cotizado":
            return "background-color: #ccffcc; color: #006600; font-weight: bold;"
        elif estado == "Cancelado":
            return "background-color: #ffcc99; color: #cc6600; font-weight: bold;"
        return ""

    def get_aceptado_style(self, aceptado):
        if aceptado == "Pendiente":
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        elif aceptado == "Aceptada":
            return "background-color: #ccffcc; color: #006600; font-weight: bold;"
        elif aceptado == "Rechazada":
            return "background-color: #ffcc99; color: #cc6600; font-weight: bold;"
        return ""

    def get_comprado_style(self, comprador):
        if comprador == "Pendiente":
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold;"
        elif comprador == "Aceptada":
            return "background-color: #ccffcc; color: #006600; font-weight: bold;"
        elif comprador == "Rechazada":
            return "background-color: #ffcc99; color: #cc6600; font-weight: bold;"
        return ""

    def verificar_vencimiento(self, row):
        fecha_cotizado = row.get("FECHA COTIZADO", "")
        estado = row.get("ESTADO", "")
        fecha_aceptado = row.get("FECHA ACEPTADO", "")
        aceptado = row.get("ACEPTADO", "")
        
        orden_roja = False
        fecha_aceptado_roja = False
        
        if estado == "Cotizacion" and fecha_cotizado:
            try:
                fecha = datetime.strptime(fecha_cotizado, "%Y-%m-%d %H:%M")
                if (datetime.now() - fecha).days > 2:
                    orden_roja = True
            except:
                pass
        
        if aceptado == "Pendiente" and fecha_aceptado:
            try:
                fecha = datetime.strptime(fecha_aceptado, "%Y-%m-%d %H:%M")
                if (datetime.now() - fecha).days > 2:
                    fecha_aceptado_roja = True
            except:
                pass
        
        return orden_roja, fecha_aceptado_roja

    def guardar_cambio(self, row_idx):
        print(f"DEBUG guardar_cambio: row_idx={row_idx}, row_map={self.row_map}")
        original_row = self.row_map.get(row_idx)
        if original_row is None:
            print(f"DEBUG: original_row is None for row_idx={row_idx}")
            return False
        
        data_idx = original_row - 2
        if data_idx >= len(self.data):
            print(f"DEBUG: data_idx {data_idx} >= len(self.data) {len(self.data)}")
            return False
        
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        nombre_corto = get_short_name(self.email)
        
        cambios = self.cambios.get(row_idx, {})
        current_data = self.data[data_idx]
        
        estado = cambios.get(3, current_data.get("ESTADO", ""))
        aceptado = cambios.get(5, current_data.get("ACEPTADO", ""))
        comprado = cambios.get(7, current_data.get("COMPRADO", ""))
        
        fecha_cotizado = current_data.get("FECHA COTIZADO", "")
        usuario_cotizo = current_data.get("USUARIO COTIZO", "")
        if estado == "Cotizado" and current_data.get("ESTADO", "") != "Cotizado":
            fecha_cotizado = fecha
            usuario_cotizo = nombre_corto
        
        fecha_aceptado = current_data.get("FECHA ACEPTADO", "")
        if aceptado == "Aceptada" and current_data.get("ACEPTADO", "") != "Aceptada":
            fecha_aceptado = fecha
        
        fecha_comprado = current_data.get("FECHA COMPRADO", "")
        usuario_compro = current_data.get("USUARIO COMPRO", "")
        if comprado == "Aceptada" and current_data.get("COMPRADO", "") != "Aceptada":
            fecha_comprado = fecha
            usuario_compro = nombre_corto
        
        updated_row = [
            current_data.get("ORDEN", ""),
            current_data.get("TECNICO", ""),
            current_data.get("FECHA PEDIDO", ""),
            estado,
            fecha_cotizado,
            aceptado,
            fecha_aceptado,
            comprado,
            fecha_comprado,
            current_data.get("N° TICKET", ""),
            "",  # Columna K vacía
            usuario_cotizo,  # Columna L - USUARIO COTIZO
            usuario_compro,  # Columna M - USUARIO COMPRO
            nombre_corto    # Columna N - ULTIMO CAMBIO
        ]
        
        if self.sheets.update_row(original_row, updated_row):
            self.cambios.pop(row_idx, None)
            return True
        return False

    def toggle_estado(self, row_idx):
        widget = self.table.cellWidget(row_idx, 3)
        if not widget:
            return
        current_estado = widget.text()
        idx = self.OPCIONES_ESTADO.index(current_estado) if current_estado in self.OPCIONES_ESTADO else 0
        next_idx = (idx + 1) % len(self.OPCIONES_ESTADO)
        nuevo_estado = self.OPCIONES_ESTADO[next_idx]
        
        print(f"DEBUG toggle_estado: row_idx={row_idx}, current={current_estado}, nuevo={nuevo_estado}")
        
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][3] = nuevo_estado
        
        btn = self.table.cellWidget(row_idx, 3)
        btn.setText(nuevo_estado)
        btn.setStyleSheet(self.get_estado_style(nuevo_estado))
        
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el cambio")

    def toggle_comprado(self, row_idx):
        widget = self.table.cellWidget(row_idx, 7)
        if not widget:
            return
        current_comprado = widget.text()
        idx = self.OPCIONES_SI_NO.index(current_comprado) if current_comprado in self.OPCIONES_SI_NO else 0
        next_idx = (idx + 1) % len(self.OPCIONES_SI_NO)
        nuevo_comprado = self.OPCIONES_SI_NO[next_idx]
        
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][7] = nuevo_comprado
        
        btn = self.table.cellWidget(row_idx, 7)
        btn.setText(nuevo_comprado)
        btn.setStyleSheet(self.get_comprado_style(nuevo_comprado))
        
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar el cambio")

    def populate_table(self):
        self.table.setRowCount(0)
        self.row_map = {}

        # Aplicar filtro de técnico
        if hasattr(self, 'filtro_tecnico') and self.filtro_tecnico != "Todos los Técnicos":
            filtered_data = [row for row in self.data if row.get("TECNICO", "") == self.filtro_tecnico]
        else:
            filtered_data = self.data
        
        # Aplicar filtro de estado
        if self.filtro_actual == "Pendientes":
            filtered_data = [row for row in filtered_data if row.get("ESTADO", "") == "Cotizacion"]
        elif self.filtro_actual == "Cotizados":
            filtered_data = [row for row in filtered_data if row.get("ESTADO", "") == "Cotizado"]
        elif self.filtro_actual == "Aceptados":
            filtered_data = [row for row in filtered_data if row.get("ACEPTADO", "") == "Aceptada"]
        elif self.filtro_actual == "Rechazados":
            filtered_data = [row for row in filtered_data if row.get("ESTADO", "") == "Cancelado"]
        elif self.filtro_actual == "Comprados":
            filtered_data = [row for row in filtered_data if row.get("COMPRADO", "") == "Aceptada"]
        elif self.filtro_actual == "Comprar":
            filtered_data = [row for row in filtered_data if row.get("ACEPTADO", "") == "Aceptada" and row.get("COMPRADO", "") == "Pendiente"]

        for row_idx, row in enumerate(filtered_data):
            original_idx = self.data.index(row)
            self.row_map[row_idx] = original_idx + 2

            self.table.insertRow(row_idx)
            
            orden_roja, fecha_aceptado_roja = self.verificar_vencimiento(row)
            
            self.table.setItem(row_idx, 0, QTableWidgetItem(row.get("ORDEN", "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(row.get("TECNICO", "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(row.get("FECHA PEDIDO", "")))
            
            if orden_roja and self.table.item(row_idx, 0):
                self.table.item(row_idx, 0).setBackground(Qt.GlobalColor.red)
            
            if self.table.item(row_idx, 0):
                self.table.item(row_idx, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
            if self.table.item(row_idx, 1):
                self.table.item(row_idx, 1).setFlags(Qt.ItemFlag.ItemIsEnabled)
            if self.table.item(row_idx, 2):
                self.table.item(row_idx, 2).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # ESTADO - editable para Compras (Cotizacion, Cotizado, Rechazado) - BOTON
            estado = row.get("ESTADO", "Cotizacion")
            btn_estado = QPushButton(estado)
            btn_estado.setFixedSize(90, 25)
            btn_estado.setStyleSheet(self.get_estado_style(estado))
            btn_estado.clicked.connect(lambda checked, r=row_idx: self.toggle_estado(r))
            btn_estado.installEventFilter(self)
            self.table.setCellWidget(row_idx, 3, btn_estado)
            
            self.table.setItem(row_idx, 4, QTableWidgetItem(row.get("FECHA COTIZADO", "")))
            if self.table.item(row_idx, 4):
                self.table.item(row_idx, 4).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # ACEPTADO - solo lectura para Compras (lo maneja Técnico) - BOTON con color
            aceptado = row.get("ACEPTADO", "Pendiente")
            btn_aceptado = QPushButton(aceptado)
            btn_aceptado.setFixedSize(90, 25)
            btn_aceptado.setStyleSheet(self.get_aceptado_style(aceptado))
            btn_aceptado.setEnabled(False)
            self.table.setCellWidget(row_idx, 5, btn_aceptado)
            
            self.table.setItem(row_idx, 6, QTableWidgetItem(row.get("FECHA ACEPTADO", "")))
            if self.table.item(row_idx, 6):
                if fecha_aceptado_roja:
                    self.table.item(row_idx, 6).setBackground(Qt.GlobalColor.red)
                self.table.item(row_idx, 6).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # COMPRADO - editable para Compras (Pendiente, Aceptado, Rechazado) - BOTON
            comprado = row.get("COMPRADO", "Pendiente")
            btn_comprado = QPushButton(comprado)
            btn_comprado.setFixedSize(90, 25)
            btn_comprado.setStyleSheet(self.get_comprado_style(comprado))
            btn_comprado.clicked.connect(lambda checked, r=row_idx: self.toggle_comprado(r))
            btn_comprado.installEventFilter(self)
            self.table.setCellWidget(row_idx, 7, btn_comprado)
            
            self.table.setItem(row_idx, 8, QTableWidgetItem(row.get("FECHA COMPRADO", "")))
            if self.table.item(row_idx, 8):
                self.table.item(row_idx, 8).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_idx, 9, QTableWidgetItem(row.get("N° TICKET", "")))
            if self.table.item(row_idx, 9):
                self.table.item(row_idx, 9).setFlags(Qt.ItemFlag.ItemIsEnabled)
            
            # USUARIO COTIZO, USUARIO COMPRO, ULTIMO CAMBIO
            self.table.setItem(row_idx, 11, QTableWidgetItem(row.get("USUARIO COTIZO", "")))
            if self.table.item(row_idx, 11):
                self.table.item(row_idx, 11).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_idx, 12, QTableWidgetItem(row.get("USUARIO COMPRO", "")))
            if self.table.item(row_idx, 12):
                self.table.item(row_idx, 12).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row_idx, 13, QTableWidgetItem(row.get("ULTIMO CAMBIO", "")))
            if self.table.item(row_idx, 13):
                self.table.item(row_idx, 13).setFlags(Qt.ItemFlag.ItemIsEnabled)

        self.table.resizeColumnsToContents()
        
        self.table.setToolTip(f"Total: {len(self.data)} pedido(s)")

    def on_combo_changed(self, row, col, text):
        if row not in self.cambios:
            self.cambios[row] = {}
        self.cambios[row][col] = text

    def guardar_cambios(self):
        if not self.cambios:
            QMessageBox.information(self, "Info", "No hay cambios para guardar")
            return
        
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        nombre_corto = get_short_name(self.email)
        guardados = 0
        
        for row_idx, cambios in self.cambios.items():
            original_row = self.row_map.get(row_idx)
            if original_row is None:
                continue
            
            data_idx = original_row - 2
            if data_idx >= len(self.data):
                continue
            
            current_data = self.data[data_idx]
            
            estado = cambios.get(3, current_data.get("ESTADO", ""))
            aceptado = cambios.get(5, current_data.get("ACEPTADO", ""))
            comprado = cambios.get(7, current_data.get("COMPRADO", ""))
            
            fecha_cotizado = current_data.get("FECHA COTIZADO", "")
            if estado == "Cotizado" and current_data.get("ESTADO", "") != "Cotizado":
                fecha_cotizado = fecha
            
            fecha_aceptado = current_data.get("FECHA ACEPTADO", "")
            if aceptado == "Aceptada" and current_data.get("ACEPTADO", "") != "Aceptada":
                fecha_aceptado = fecha
            
            fecha_comprado = current_data.get("FECHA COMPRADO", "")
            usuario_compro = current_data.get("USUARIO COMPRO", "")
            if comprado == "Aceptada" and current_data.get("COMPRADO", "") != "Aceptada":
                fecha_comprado = fecha
                usuario_compro = nombre_corto
            
            updated_row = [
                current_data.get("ORDEN", ""),
                current_data.get("TECNICO", ""),
                current_data.get("FECHA PEDIDO", ""),
                estado,
                fecha_cotizado,
                aceptado,
                fecha_aceptado,
                comprado,
                fecha_comprado,
                current_data.get("N° TICKET", ""),
                "",  # Columna K vacía
                current_data.get("USUARIO COTIZO", ""),  # Columna L
                usuario_compro,  # Columna M
                nombre_corto    # Columna N
            ]
            
            if self.sheets.update_row(original_row, updated_row):
                guardados += 1
        
        self.cambios = {}
        QMessageBox.information(self, "Éxito", f"Se guardaron {guardados} cambio(s)")
        self.load_data()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.RightButton:
            for row_idx in range(self.table.rowCount()):
                btn_estado = self.table.cellWidget(row_idx, 3)
                if btn_estado == obj:
                    self.mostrar_menu_estado(row_idx)
                    return True
                btn_comprado = self.table.cellWidget(row_idx, 7)
                if btn_comprado == obj:
                    self.mostrar_menu_comprado(row_idx)
                    return True
        return super().eventFilter(obj, event)

    def mostrar_menu_estado(self, row_idx):
        menu = QMenu(self)
        for opcion in self.OPCIONES_ESTADO:
            action = menu.addAction(opcion)
            action.triggered.connect(lambda checked, o=opcion, r=row_idx: self.seleccionar_estado(r, o))
        menu.exec(QCursor.pos())

    def mostrar_menu_comprado(self, row_idx):
        menu = QMenu(self)
        for opcion in self.OPCIONES_SI_NO:
            action = menu.addAction(opcion)
            action.triggered.connect(lambda checked, o=opcion, r=row_idx: self.seleccionar_comprado(r, o))
        menu.exec(QCursor.pos())

    def seleccionar_estado(self, row_idx, valor):
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][3] = valor
        btn = self.table.cellWidget(row_idx, 3)
        btn.setText(valor)
        btn.setStyleSheet(self.get_estado_style(valor))
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")

    def seleccionar_comprado(self, row_idx, valor):
        if row_idx not in self.cambios:
            self.cambios[row_idx] = {}
        self.cambios[row_idx][7] = valor
        btn = self.table.cellWidget(row_idx, 7)
        btn.setText(valor)
        btn.setStyleSheet(self.get_comprado_style(valor))
        if self.guardar_cambio(row_idx):
            QMessageBox.information(self, "Guardado", "Cambio guardado correctamente")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.credentials = None
        self.sheets = None
        self.user_email = None
        self.user_name = None
        self.user_category = None

        creds = load_credentials()
        if creds:
            self.credentials = creds
            self.user_email = get_user_email(creds)
            if self.user_email:
                self.sheets = GoogleSheets(creds)
                self.load_user_info()
                if self.user_category:
                    self.auto_open_role()
                    return
                self.show_role_selector()
                return

        self.show_login()

    def load_user_info(self):
        user_info = get_user_info(self.credentials, self.user_email)
        self.user_name = user_info.get("name", self.user_email.split('@')[0])
        self.user_category = user_info.get("category", "Técnico")
        self.save_user_config()

    def save_user_config(self):
        config = load_config()
        config["user_email"] = self.user_email
        config["user_name"] = self.user_name
        config["user_category"] = self.user_category
        save_config(config)

    def auto_open_role(self):
        if self.user_category == "Compras":
            self.show_compras()
        else:
            self.show_tecnico()

    def show_login(self):
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.on_login_success)
        self.setCentralWidget(self.login_window)
        self.setMinimumSize(400, 300)

    def on_login_success(self, credentials_json, email):
        creds = Credentials.from_authorized_user_info(
            json.loads(credentials_json), SCOPES
        )
        self.credentials = creds
        self.user_email = email
        self.sheets = GoogleSheets(self.credentials)
        self.load_user_info()
        if self.user_category:
            self.auto_open_role()
        else:
            self.show_role_selector()

    def show_role_selector(self):
        self.role_window = RoleSelectorWindow(self.user_email)
        self.role_window.role_selected.connect(self.on_role_selected)
        self.setCentralWidget(self.role_window)
        self.setMinimumSize(400, 250)

    def on_role_selected(self, email, role):
        self.user_category = role
        self.save_user_config()
        if role == "Tecnico":
            self.show_tecnico()
        elif role == "Compras":
            self.show_compras()

    def show_tecnico(self):
        self.check_and_update()
        self.tecnico_window = TecnicoWindow(self.user_email, self.user_name, self.sheets)
        self.tecnico_window.logout_signal.connect(self.logout)
        self.setCentralWidget(self.tecnico_window)
        self.setMinimumSize(1000, 600)

    def show_compras(self):
        self.check_and_update()
        self.compras_window = ComprasWindow(self.user_email, self.user_name, self.sheets)
        self.compras_window.logout_signal.connect(self.logout)
        self.setCentralWidget(self.compras_window)
        self.setMinimumSize(1100, 600)

    def check_and_update(self):
        print("[DEBUG] === INICIANDO VERIFICACIÓN DE ACTUALIZACIONES ===")
        update_info = check_for_updates(self.sheets)
        print(f"[DEBUG] Resultado de check_for_updates: {update_info}")
        if update_info.get("available"):
            print(f"[DEBUG] ¡Actualización disponible! {update_info['current_version']} -> {update_info['new_version']}")
            msg = QMessageBox()
            msg.setWindowTitle("Actualización disponible")
            msg.setText(f"Versión actual: {update_info['current_version']}\nNueva versión: {update_info['new_version']}")
            msg.setInformativeText("¿Desea actualizar ahora?")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            if msg.exec() == QMessageBox.StandardButton.Yes:
                print("[DEBUG] Usuario aceptó actualizar")
                download_and_update(self)
            else:
                print("[DEBUG] Usuario rechazó actualización")
        else:
            print("[DEBUG] No hay actualización disponible")

    def logout(self):
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        config = load_config()
        config.pop("user_email", None)
        config.pop("user_name", None)
        config.pop("user_category", None)
        save_config(config)
        self.credentials = None
        self.sheets = None
        self.user_email = None
        self.user_name = None
        self.user_category = None
        self.show_login()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
