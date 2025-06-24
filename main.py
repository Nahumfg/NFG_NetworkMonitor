# main.py
import sys
import csv
import os
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem
)
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from matplotlib.ticker import FuncFormatter

class NetworkMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFG Network Monitor v2.0")
        self.setFixedSize(1000, 750)
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
        
        #Vista Enriquecida
        self.table_procesos = QTableWidget()
        self.table_procesos.setColumnCount(5)
        self.table_procesos.setHorizontalHeaderLabels(["PID", "Nombre", "Local", "Remoto", "Estado"])
        self.table_procesos.setAlternatingRowColors(True)
        self.table_procesos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_procesos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_procesos.setStyleSheet("QHeaderView::section { font-weight: bold; }")
        
        
        self.layout.addWidget(self.label_lista)
        self.layout.addWidget(self.table_procesos)
        self.table_procesos.setMinimumHeight(100)
        
        #Boton de ayuda
        self.btn_about = QPushButton("ℹ️ Acerca de")
        self.btn_about.setFixedWidth(140)
        self.btn_about.setStyleSheet("margin-top: 10px;")
        self.layout.addWidget(self.btn_about)
        
        self.btn_about.clicked.connect(self.mostrar_info_autor)
        
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

        #self.list_widget.currentItemChanged.connect(self.update_process_info)
        self.table_procesos.itemSelectionChanged.connect(self.update_process_info)

        # Temporizadores
        self.timer_graph = QTimer()
        self.timer_graph.timeout.connect(self.update_graph)
        self.timer_graph.start(1000)

        self.timer_proc = QTimer()
        self.timer_proc.timeout.connect(self.actualizar_lista_procesos)
        self.timer_proc.start(5000)

        self.actualizar_lista_procesos()
        
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
        
        self.version_label = QLabel("🔖 NFG Network Monitor v2.0 - por Nahum Flores Gómez")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet("color: gray; font-style: italic; margin-top: 8px;")
        self.layout.addWidget(self.version_label)
        
        #boton trafico oscuro
        self.btn_netstat = QPushButton("🔎 Ver conexiones activas (netstat)")
        self.layout.addWidget(self.btn_netstat)
        self.btn_netstat.clicked.connect(self.ver_conexiones_netstat)
        
        self.toggle_netstat_mode = QPushButton("🧠 Modo netstat OFF")
        self.toggle_netstat_mode.setCheckable(True)
        self.layout.addWidget(self.toggle_netstat_mode)
        
        self.toggle_netstat_mode.clicked.connect(self.toggle_modo_netstat)
        self.netstat_mode = False  # Estado inicial
        
        self.table_procesos.horizontalHeader().setStretchLastSection(True)
        self.table_procesos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        #self.layout.addWidget(self.table_procesos, stretch=3)
        #self.layout.addWidget(self.canvas, stretch=2)
    
    def mostrar_info_autor(self):
        QMessageBox.information(
            self,
            "Acerca de NFG Monitor",
            (
                "📡 NFG Network Monitor v2.0\n"
                "Desarrollado con cariño por Nahum Flores\n\n"
                "🚗 Ingeniería • 🧪 Python • ⚙️ Creatividad\n\n"
                "¿Te resultó útil? Puedes apoyarme con una donación 🫶\n"
                "📬 PayPal: paypal.me/Nahumfg \n"
            )
        )
    
    def toggle_modo_netstat(self):
        self.netstat_mode = self.toggle_netstat_mode.isChecked()
    
        if self.netstat_mode:
            self.toggle_netstat_mode.setText("🧠 Modo netstat ON")
            self.actualizar_vista_netstat()
            self.table_procesos.resizeRowsToContents()
        else:
            self.toggle_netstat_mode.setText("🧠 Modo netstat OFF")
            self.actualizar_lista_procesos()
    
    def actualizar_lista_procesos(self):
        self.table_procesos.setRowCount(0)
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                conns = proc.net_connections(kind='inet')
                for conn in conns:
                    laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "-"
                    raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
                    fila = self.table_procesos.rowCount()
                    self.table_procesos.insertRow(fila)
                    for i, valor in enumerate([
                        str(proc.info['pid']),
                        proc.info['name'],
                        laddr,
                        raddr,
                        conn.status
                    ]):
                        self.table_procesos.setItem(fila, i, QTableWidgetItem(valor))
            except Exception:
                pass
    
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
                conns = proc.net_connections(kind='inet')
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
    
    
    
    def cancelar_reanudacion(self):
        self.countdown_timer.stop()
        self.countdown_label.setText(f"❌ Reanudación automática cancelada para el proceso {self.current_pid_paused}.")
        self.btn_cancelar_timer.setEnabled(False)
        self.current_pid_paused = None
    
    def update_graph(self):
        if self.netstat_mode:
            self.actualizar_vista_netstat()
            self.table_procesos.resizeRowsToContents()
            return
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
    
        self.save_to_csv(up, down)
    
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
        fila = self.table_procesos.currentRow()
        if fila == -1:
            return
    
        try:
            pid_item = self.table_procesos.item(fila, 0)  # Columna PID
            nombre_item = self.table_procesos.item(fila, 1)  # Nombre del proceso
    
            if not pid_item or not nombre_item:
                return
    
            pid = int(pid_item.text())
            nombre = nombre_item.text()
    
            proc = psutil.Process(pid)
            ruta = proc.exe()
            uso_cpu = proc.cpu_percent(interval=0.1)
            memoria = round(proc.memory_info().rss / (1024 * 1024), 2)
    
            detalles = (
                f"🔍 Proceso seleccionado:\n"
                f"PID: {pid}\n"
                f"Nombre: {nombre}\n"
                f"Ruta: {ruta}\n"
                f"CPU: {uso_cpu}%\n"
                f"Memoria: {memoria} MB"
            )
    
            print(detalles)  # O muestra en un QMessageBox si prefieres
    
        except Exception as e:
            print(f"Error al obtener info del proceso: {e}")
    
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
                self.actualizar_lista_procesos()
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
    
    def save_to_csv(self, up, down):
        from datetime import datetime
        ruta = "logs/historial.csv"
        encabezado = ["timestamp", "download", "upload", "total"]
    
        try:
            nuevo = not os.path.isfile(ruta)
            with open(ruta, "a", newline="") as f:
                writer = csv.writer(f)
                if nuevo:
                    writer.writerow(encabezado)
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([ahora, down, up, up + down])
        except Exception as e:
            print(f"Error guardando CSV: {e}")

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
        
    def ver_conexiones_netstat(self):
        self.table_procesos.setRowCount(0)
        conexiones = psutil.net_connections(kind='inet')
    
        for c in conexiones:
            pid = c.pid if c.pid is not None else 0
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
            raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-"
            estado = c.status
    
            try:
                proc = psutil.Process(pid) if pid else None
                nombre = proc.name() if proc else "System/Idle"
            except Exception:
                nombre = "Desconocido"
    
            fila = self.table_procesos.rowCount()
            self.table_procesos.insertRow(fila)
            
            self.table_procesos.setItem(fila, 0, QTableWidgetItem(str(pid)))
            self.table_procesos.setItem(fila, 1, QTableWidgetItem(nombre))
            self.table_procesos.setItem(fila, 2, QTableWidgetItem(laddr))
            self.table_procesos.setItem(fila, 3, QTableWidgetItem(raddr))
            self.table_procesos.setItem(fila, 4, QTableWidgetItem(estado))
            
    def actualizar_vista_netstat(self):
        self.table_procesos.setRowCount(0)
        conexiones = psutil.net_connections(kind='inet')
    
        for conn in conexiones:
            pid = conn.pid if conn.pid else 0
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "-"
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
            estado = conn.status
    
            try:
                proc = psutil.Process(pid) if pid else None
                nombre = proc.name() if proc else "System/Idle"
            except Exception:
                nombre = "Desconocido"
    
            fila = self.table_procesos.rowCount()
            self.table_procesos.insertRow(fila)
            for i, valor in enumerate([str(pid), nombre, laddr, raddr, estado]):
                item = QTableWidgetItem(valor)
                self.table_procesos.setItem(fila, i, item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = NetworkMonitor()
    monitor.show()
    sys.exit(app.exec())
