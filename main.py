# main.py
import sys
import csv
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QMessageBox, QFileDialog
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QIcon
from matplotlib.ticker import FuncFormatter

class NetworkMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFG Network Monitor")
        self.setFixedSize(1000, 700)
        self.setFont(QFont("Segoe UI", 10))
        self.setWindowIcon(QIcon("icono_nfg.ico"))  # Asegúrate de tener el ícono en la carpeta

        # Variables de red
        self.traffic_data = []
        self.prev_bytes = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
        self.log_path = "logs/historial.csv"
                # Layout principal
        self.layout = QVBoxLayout()

        # Lista de procesos con conexión activa
        self.label_lista = QLabel("🔍 Procesos con conexión a Internet:")
        self.list_widget = QListWidget()
        self.layout.addWidget(self.label_lista)
        self.layout.addWidget(self.list_widget)

        # Detalles del proceso seleccionado
        self.process_info = QLabel("Selecciona un proceso para ver detalles.")
        self.layout.addWidget(self.process_info)

        # Botones de control de procesos
        btn_layout = QHBoxLayout()
        self.btn_pause = QPushButton("⏸ Pausar")
        self.btn_resume = QPushButton("▶ Reanudar")
        self.btn_kill = QPushButton("🛑 Finalizar")
        self.btn_export = QPushButton("📁 Exportar CSV")
        for btn in [self.btn_pause, self.btn_resume, self.btn_kill, self.btn_export]:
            btn.setFixedWidth(120)
            btn_layout.addWidget(btn)
        self.layout.addLayout(btn_layout)

        # Gráfico de uso de red en tiempo real
        self.figure, self.ax = plt.subplots()
        self.canvas = Canvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Aplicar layout final
        self.setLayout(self.layout)
        
        self.btn_pause.clicked.connect(lambda: self.control_process("pause"))
        self.btn_resume.clicked.connect(lambda: self.control_process("resume"))
        self.btn_kill.clicked.connect(lambda: self.control_process("kill"))
        self.btn_export.clicked.connect(self.export_csv)

        self.list_widget.currentItemChanged.connect(self.update_process_info)

        # Temporizadores
        self.timer_graph = QTimer()
        self.timer_graph.timeout.connect(self.update_graph)
        self.timer_graph.start(1000)

        self.timer_proc = QTimer()
        self.timer_proc.timeout.connect(self.update_process_list)
        self.timer_proc.start(5000)

        self.update_process_list()
        
        self.label_top = QLabel("Proceso con más conexiones activas: ---")
        self.layout.addWidget(self.label_top)
        
        self.timer_top = QTimer()
        self.timer_top.timeout.connect(self.update_top_network_process)
        self.timer_top.start(3000)  # cada 3 segundos
        
        self.countdown_label = QLabel("")
        self.layout.addWidget(self.countdown_label)
        
        self.pause_timers = {}  # Para manejar múltiples pausas si se extiende
        self.countdown = 0
        self.current_pid_paused = None
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        
        # Configurar duración de pausa
        self.label_duracion = QLabel("⏱ Duración de pausa automática (segundos):")
        self.input_duracion = QListWidget()
        self.input_duracion.addItems(["5", "10", "15", "30", "60"])
        self.input_duracion.setCurrentRow(0)
        
        # Botón para cancelar la cuenta regresiva
        self.btn_cancelar_timer = QPushButton("❌ Cancelar reanudación automática")
        self.btn_cancelar_timer.setEnabled(False)
        
        self.layout.addWidget(self.label_duracion)
        self.layout.addWidget(self.input_duracion)
        self.layout.addWidget(self.btn_cancelar_timer)
        
        self.btn_cancelar_timer.clicked.connect(self.cancelar_reanudacion)
        
        self.upload_data = []
        self.download_data = []
        self.prev_sent = psutil.net_io_counters().bytes_sent
        self.prev_recv = psutil.net_io_counters().bytes_recv

    
    def update_countdown(self):
        if self.countdown > 0:
            self.countdown -= 1
            self.countdown_label.setText(f"⏳ Proceso {self.current_pid_paused} se reanudará en {self.countdown} segundos...")
        else:
            try:
                proc = psutil.Process(self.current_pid_paused)
                proc.resume()
                self.countdown_label.setText(f"✅ Proceso {self.current_pid_paused} reanudado automáticamente.")
            except Exception:
                self.countdown_label.setText("⚠️ Falló la reanudación automática.")
                self.countdown_timer.stop()
                self.btn_cancelar_timer.setEnabled(False)
                self.current_pid_paused = None

    
    def update_top_network_process(self):
        max_conns = 0
        top_pid = None
        top_name = "N/A"
    
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                conns = proc.connections(kind='inet')
                if conns and len(conns) > max_conns:
                    max_conns = len(conns)
                    top_pid = proc.pid
                    top_name = proc.info['name']
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue

        if top_pid:
            self.label_top.setText(f"🔥 Más activo: {top_name} (PID {top_pid}) con {max_conns} conexiones")
        else:
            self.label_top.setText("No hay actividad significativa detectada.")
    
    def update_process_list(self):
        self.list_widget.clear()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.connections(kind='inet'):
                    self.list_widget.addItem(f"{proc.info['pid']} - {proc.info['name']}")
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
    
    def cancelar_reanudacion(self):
        self.countdown_timer.stop()
        self.countdown_label.setText(f"❌ Reanudación automática cancelada para el proceso {self.current_pid_paused}.")
        self.btn_cancelar_timer.setEnabled(False)
        self.current_pid_paused = None
    
    def update_graph(self):
        counters = psutil.net_io_counters()
        up = counters.bytes_sent - self.prev_sent
        down = counters.bytes_recv - self.prev_recv
        self.prev_sent = counters.bytes_sent
        self.prev_recv = counters.bytes_recv
    
        self.upload_data.append(up)
        self.download_data.append(down)
        if len(self.upload_data) > 60:
            self.upload_data.pop(0)
            self.download_data.pop(0)
    
        self.save_to_csv(up + down)
    
        # Escalar colores por tráfico
        color_down = "lime" if down < 100_000 else "gold" if down < 500_000 else "red"
        color_up = "deepskyblue" if up < 100_000 else "orange" if up < 500_000 else "crimson"
    
        self.ax.clear()
        x = list(range(len(self.upload_data)))
        self.ax.plot(x, self.download_data, label="⬇ Descarga", color=color_down, linewidth=2.5)
        self.ax.plot(x, self.upload_data, label="⬆ Subida", color=color_up, linewidth=1.5, linestyle="--")
    
        # Umbral visual (opcional)
        umbral = 100_000
        self.ax.axhline(umbral, color='orange', linestyle='--', label=f"Umbral {self.format_bytes(umbral)}")
    
        # Mostrar último valor como texto
        if self.download_data:
            self.ax.text(x[-1], self.download_data[-1], self.format_bytes(self.download_data[-1]),
                        color=color_down, fontsize=9, va='bottom', ha='right')
        if self.upload_data:
            self.ax.text(x[-1], self.upload_data[-1], self.format_bytes(self.upload_data[-1]),
                        color=color_up, fontsize=9, va='top', ha='right')
    
        # Ejes y estilos
        self.ax.set_title("📡 Tráfico de red en tiempo real", color="white")
        self.ax.set_ylabel("Velocidad", color="white")
        self.ax.set_facecolor("#1e1e1e")
        self.ax.tick_params(colors="white")
        self.ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: self.format_bytes(y)))
        self.ax.legend(facecolor="#2a2a2a", edgecolor="white", labelcolor="white", fontsize=9)
    
        self.figure.tight_layout()
        self.canvas.draw()
    
    def format_bytes(self, num):
        for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
            if num < 1024:
                return f"{num:.1f} {unit}"
            num /= 1024
        return f"{num:.1f} TB/s"
    
    def update_process_info(self):
        item = self.list_widget.currentItem()
        if item:
            pid = int(item.text().split(" - ")[0])
            try:
                proc = psutil.Process(pid)
                self.process_info.setText(f"🧠 {proc.name()} | PID: {pid} | Estado: {proc.status()}")
            except Exception:
                self.process_info.setText("Error al obtener información del proceso.")
    
    def control_process(self, action):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Atención", "Selecciona un proceso primero.")
            return
        pid = int(item.text().split(" - ")[0])
        try:
            proc = psutil.Process(pid)
            if action == "pause":
                proc.suspend()
                self.current_pid_paused = pid
                self.countdown = int(self.input_duracion.currentItem().text())
                self.countdown_label.setText(f"⏸️ Proceso {pid} pausado. Se reanudará en {self.countdown} segundos...")
                self.countdown_timer.start(1000)
                self.btn_cancelar_timer.setEnabled(True)


            elif action == "resume":
                proc.resume()
                QMessageBox.information(self, "Éxito", f"Proceso {pid} reanudado.")
            elif action == "kill":
                proc.terminate()
                QMessageBox.information(self, "Éxito", f"Proceso {pid} finalizado.")
                self.update_process_list()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
    
    def auto_resume(self, pid):
        try:
            proc = psutil.Process(pid)
            if proc.status() == psutil.STATUS_STOPPED:
                proc.resume()
                QMessageBox.information(self, "Reanudado", f"Proceso {pid} reanudado automáticamente.")
        except Exception:
            pass  # el proceso pudo haber terminado entre pausado y reanudado
    
    def save_to_csv(self, delta_bytes):
        try:
            with open(self.log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([psutil.boot_time(), delta_bytes])
        except Exception:
            pass

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar historial como...", "historial.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(self.log_path, 'r') as original, open(path, 'w') as new_file:
                    new_file.write(original.read())
                QMessageBox.information(self, "Exportado", "Historial exportado con éxito.")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
    
    def format_bytes(self, num):
        for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
            if num < 1024:
                return f"{num:.1f} {unit}"
            num /= 1024
        return f"{num:.1f} TB/s"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = NetworkMonitor()
    monitor.show()
    sys.exit(app.exec())
