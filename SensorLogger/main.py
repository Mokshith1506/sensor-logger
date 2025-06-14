import tkinter as tk
from tkinter import ttk, messagebox
import random
import time
import pandas as pd
import json
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from threading import Thread, Event
import os


class SensorSimulator:
    def __init__(self):
        self.running = Event()
        self.paused = False
        self.data = []
        self.error_log = []
        self.temp_limits = (20, 30)
        self.pressure_limits = (95, 105)

    def simulate_temp(self):
        return round(random.uniform(18.0, 32.0), 2)

    def simulate_pressure(self):
        return round(random.uniform(92.0, 108.0), 2)

    def generate_data(self):
        temp1 = self.simulate_temp()
        temp2 = self.simulate_temp() if random.random() > 0.05 else None
        pressure = self.simulate_pressure()
        timestamp = time.strftime("%H:%M:%S")

        status = "OK"
        issues = []

        if temp2 is None:
            status = "TEMP SENSOR FAIL"
            issues.append(("Temp2", "No Data"))
        elif abs(temp1 - temp2) > 3:
            status = "TEMP SENSOR MISMATCH"
            issues.append(("Temp Redundancy", f"{temp1} vs {temp2}"))

        if not (self.pressure_limits[0] <= pressure <= self.pressure_limits[1]):
            status = "PRESSURE FAULT"
            issues.append(("Pressure", pressure))

        for issue in issues:
            self.error_log.append((timestamp, issue[0], issue[1]))

        self.data.append(
            (timestamp, temp1, temp2 if temp2 is not None else "--", pressure, status))
        return timestamp, temp1, temp2, pressure, status

    def start_logging(self):
        self.running.set()
        while self.running.is_set():
            if not self.paused:
                self.generate_data()
            time.sleep(1)

    def stop_logging(self):
        self.running.clear()

    def export_data(self):
        os.makedirs("reports", exist_ok=True)

        df = pd.DataFrame(self.data, columns=[
                          "Time", "Temp1", "Temp2", "Pressure", "Status"])
        df.to_csv("reports/sensor_data_log.csv", index=False)

        if self.error_log:
            with open("reports/sensor_error_log.json", "w") as f:
                json.dump([{"Time": t, "Sensor": s, "Issue": i}
                          for t, s, i in self.error_log], f, indent=4)

        temps = [d[1] for d in self.data if isinstance(d[1], (int, float))]
        pressures = [d[3] for d in self.data if isinstance(d[3], (int, float))]
        summary = []

        if temps and pressures:
            summary.append(f"Total Data Points: {len(self.data)}")
            summary.append(
                f"Temperature -> Min: {min(temps):.2f}, Max: {max(temps):.2f}, Mean: {sum(temps)/len(temps):.2f}")
            summary.append(
                f"Pressure    -> Min: {min(pressures):.2f}, Max: {max(pressures):.2f}, Mean: {sum(pressures)/len(pressures):.2f}")
            summary.append("")

        error_types = {}
        for _, sensor, issue in self.error_log:
            error_types[sensor] = error_types.get(sensor, 0) + 1

        summary.append("Error Type Breakdown:")
        for sensor, count in error_types.items():
            summary.append(f" - {sensor}: {count} occurrence(s)")

        with open("reports/report_summary.txt", "w") as f:
            f.write("\n".join(summary))


class SensorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensor Logger ")
        self.sim = SensorSimulator()

        self.temp1_vals = []
        self.pressure_vals = []
        self.timestamps = []

        self.build_ui()
        self.update_ui()

    def build_ui(self):
        # Controls Frame
        control_frame = ttk.LabelFrame(self.root, text="Controls")
        control_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(control_frame, text="Start", command=self.start_logging).pack(
            side="left", padx=5, pady=5)
        ttk.Button(control_frame, text="Pause",
                   command=self.pause_logging).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Resume",
                   command=self.resume_logging).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Stop",
                   command=self.stop_logging).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Export",
                   command=self.export_data).pack(side="left", padx=5)

        # Live Reading Display
        self.reading_frame = ttk.LabelFrame(self.root, text="Live Sensor Data")
        self.reading_frame.pack(fill="x", padx=10, pady=5)

        self.temp1_var = tk.StringVar(value="Temp1: -- °C")
        self.temp2_var = tk.StringVar(value="Temp2: -- °C")
        self.pressure_var = tk.StringVar(value="Pressure: -- kPa")

        ttk.Label(self.reading_frame, textvariable=self.temp1_var).pack(
            side="left", padx=10)
        ttk.Label(self.reading_frame, textvariable=self.temp2_var).pack(
            side="left", padx=10)
        ttk.Label(self.reading_frame, textvariable=self.pressure_var).pack(
            side="left", padx=10)

        # Status Frame
        status_frame = ttk.LabelFrame(self.root, text="System Status")
        status_frame.pack(fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(status_frame, text="Status: --")
        self.status_label.pack(side="left", padx=10)

        self.score_label = ttk.Label(status_frame, text="Health Score: --")
        self.score_label.pack(side="left", padx=10)

        self.trend_label = ttk.Label(status_frame, text="Trend: --")
        self.trend_label.pack(side="left", padx=10)

        # Graph Area
        self.fig, self.ax = plt.subplots(2, 1, figsize=(6, 4))
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def start_logging(self):
        self.sim.running.set()
        self.sim.paused = False
        self.thread = Thread(target=self.sim.start_logging)
        self.thread.daemon = True
        self.thread.start()

    def pause_logging(self):
        self.sim.paused = True
        self.status_label.config(text="Status: PAUSED", foreground="orange")

    def resume_logging(self):
        self.sim.paused = False

    def stop_logging(self):
        self.sim.stop_logging()
        self.status_label.config(text="Status: STOPPED", foreground="black")

    def export_data(self):
        self.sim.export_data()
        messagebox.showinfo(
            "Export", "Data & reports saved in /reports folder.")

    def calculate_trend(self, data):
        if len(data) < 5:
            return "--"
        delta = data[-1] - data[-5]
        if delta > 1.0:
            return "Rising"
        elif delta < -1.0:
            return "Falling"
        else:
            return "Stable"

    def update_ui(self):
        if self.sim.data:
            t, temp1, temp2, pressure, status = self.sim.data[-1]

            self.timestamps.append(t)
            self.temp1_vals.append(temp1)
            self.pressure_vals.append(pressure)

            self.timestamps = self.timestamps[-20:]
            self.temp1_vals = self.temp1_vals[-20:]
            self.pressure_vals = self.pressure_vals[-20:]

            self.ax[0].clear()
            self.ax[0].plot(self.timestamps, self.temp1_vals, color="red")
            self.ax[0].set_ylabel("Temp1 (°C)")
            self.ax[0].tick_params(axis='x', rotation=45)

            self.ax[1].clear()
            self.ax[1].plot(self.timestamps, self.pressure_vals, color="blue")
            self.ax[1].set_ylabel("Pressure (kPa)")
            self.ax[1].tick_params(axis='x', rotation=45)

            self.canvas.draw()

            # Update live readings
            self.temp1_var.set(f"Temp1: {temp1} °C")
            self.temp2_var.set(f"Temp2: {temp2 if temp2 != '--' else '--'} °C")
            self.pressure_var.set(f"Pressure: {pressure} kPa")

            # Update status with color
            self.status_label.config(
                text=f"Status: {status}", foreground="green" if status == "OK" else "red")
            self.score_label.config(
                text=f"Health Score: {max(0, 100 - len(self.sim.error_log))}")
            self.trend_label.config(
                text=f"Trend: {self.calculate_trend(self.temp1_vals)}")

        self.root.after(1000, self.update_ui)


if __name__ == "__main__":
    root = tk.Tk()
    app = SensorGUI(root)
    root.mainloop()
