import math
import tkinter as tk
from tkinter import ttk, messagebox

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# =========================================================
# Grover core
# =========================================================
def optimal_grover_iterations(n_qubits: int, num_solutions: int = 1) -> int:
    if num_solutions <= 0:
        raise ValueError("num_solutions 必須 >= 1")
    n_states = 2 ** n_qubits
    r = math.floor((math.pi / 4) * math.sqrt(n_states / num_solutions))
    return max(1, r)


def apply_phase_oracle_for_target(qc: QuantumCircuit, qubits, target_qubit_order: str):
    n = len(qubits)
    if len(target_qubit_order) != n:
        raise ValueError("target 長度必須等於 qubit 數")
    if any(b not in "01" for b in target_qubit_order):
        raise ValueError("target 只能包含 0 或 1")
    if n < 2:
        raise ValueError("這份程式預設支援 n >= 2")

    # 把 target 中是 0 的位元翻成 1，讓目標態映成 |11...1>
    for i, bit in enumerate(target_qubit_order):
        if bit == "0":
            qc.x(qubits[i])

    # 對 |11...1> 做 phase flip
    qc.h(qubits[-1])
    qc.mcx(qubits[:-1], qubits[-1])
    qc.h(qubits[-1])

    # 還原
    for i, bit in enumerate(target_qubit_order):
        if bit == "0":
            qc.x(qubits[i])


def apply_diffuser(qc: QuantumCircuit, qubits):
    n = len(qubits)
    if n < 2:
        raise ValueError("這份程式預設支援 n >= 2")

    qc.h(qubits)
    qc.x(qubits)

    qc.h(qubits[-1])
    qc.mcx(qubits[:-1], qubits[-1])
    qc.h(qubits[-1])

    qc.x(qubits)
    qc.h(qubits)


def build_grover_circuit(target_display: str):
    n = len(target_display)
    if n < 2:
        raise ValueError("請至少輸入 2 個 bits，例如 11、101、1011")
    if any(b not in "01" for b in target_display):
        raise ValueError("目標 bitstring 只能包含 0 或 1")

    # Qiskit counts 顯示順序為高位 classical bit 在左
    # measure(q[i] -> c[i]) 時，counts 字串看起來會是 q(n-1)...q0
    # 因此若想讓顯示結果就是 target_display，需要反轉成 oracle 的 qubit 順序
    target_qubit_order = target_display[::-1]

    qc = QuantumCircuit(n, n)

    # Step 1: 均勻疊加
    qc.h(range(n))

    # Step 2: Grover iterations
    iterations = optimal_grover_iterations(n, num_solutions=1)
    for _ in range(iterations):
        apply_phase_oracle_for_target(qc, list(range(n)), target_qubit_order)
        apply_diffuser(qc, list(range(n)))

    # Step 3: measurement
    qc.measure(range(n), range(n))
    return qc, iterations


def run_grover(target_display: str, shots: int):
    qc, iterations = build_grover_circuit(target_display)

    simulator = AerSimulator()
    tqc = transpile(qc, simulator)
    result = simulator.run(tqc, shots=shots).result()
    counts = result.get_counts()

    return qc, iterations, counts


# =========================================================
# UI
# =========================================================
class GroverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Grover Quantum Search UI (Qiskit)")
        self.root.geometry("1100x820")

        self.main = ttk.Frame(root, padding=12)
        self.main.pack(fill="both", expand=True)

        self._build_top_controls()
        self._build_info_area()
        self._build_middle_area()
        self._build_bottom_area()

        self.set_status("請輸入目標 bitstring，例如 1011，然後按執行。")

    def _build_top_controls(self):
        top = ttk.Frame(self.main)
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="目標 bitstring：").grid(row=0, column=0, sticky="w")
        self.target_var = tk.StringVar(value="1011")
        self.ent_target = ttk.Entry(top, textvariable=self.target_var, width=20)
        self.ent_target.grid(row=0, column=1, sticky="w", padx=(6, 20))

        ttk.Label(top, text="Shots：").grid(row=0, column=2, sticky="w")
        self.shots_var = tk.StringVar(value="1024")
        self.ent_shots = ttk.Entry(top, textvariable=self.shots_var, width=12)
        self.ent_shots.grid(row=0, column=3, sticky="w", padx=(6, 20))

        self.btn_run = ttk.Button(top, text="執行 Grover", command=self.on_run)
        self.btn_run.grid(row=0, column=4, sticky="w", padx=(0, 10))

        self.btn_clear = ttk.Button(top, text="清除輸出", command=self.clear_output)
        self.btn_clear.grid(row=0, column=5, sticky="w")

    def _build_info_area(self):
        info = ttk.LabelFrame(self.main, text="執行資訊", padding=10)
        info.pack(fill="x", pady=(0, 10))

        self.info_text = tk.Text(info, height=7, font=("Helvetica", 12), wrap="word")
        self.info_text.pack(fill="x", expand=False)

    def _build_middle_area(self):
        middle = ttk.Frame(self.main)
        middle.pack(fill="both", expand=True, pady=(0, 10))

        left = ttk.LabelFrame(middle, text="Measurement Counts", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.counts_text = tk.Text(left, font=("Courier New", 12), wrap="none")
        self.counts_text.pack(side="left", fill="both", expand=True)

        counts_scroll = ttk.Scrollbar(left, orient="vertical", command=self.counts_text.yview)
        counts_scroll.pack(side="right", fill="y")
        self.counts_text.configure(yscrollcommand=counts_scroll.set)

        right = ttk.LabelFrame(middle, text="簡易統計", padding=10)
        right.pack(side="left", fill="both", expand=False, padx=(6, 0))

        self.stats_text = tk.Text(right, width=34, font=("Helvetica", 12), wrap="word")
        self.stats_text.pack(fill="both", expand=True)

    def _build_bottom_area(self):
        bottom = ttk.LabelFrame(self.main, text="Quantum Circuit", padding=10)
        bottom.pack(fill="both", expand=True)

        self.circuit_text = tk.Text(bottom, font=("Courier New", 10), wrap="none")
        self.circuit_text.pack(side="left", fill="both", expand=True)

        yscroll = ttk.Scrollbar(bottom, orient="vertical", command=self.circuit_text.yview)
        yscroll.pack(side="right", fill="y")
        self.circuit_text.configure(yscrollcommand=yscroll.set)

    def set_status(self, msg: str):
        self.root.title(f"Grover Quantum Search UI (Qiskit) | {msg}")

    def clear_output(self):
        self.info_text.delete("1.0", "end")
        self.counts_text.delete("1.0", "end")
        self.stats_text.delete("1.0", "end")
        self.circuit_text.delete("1.0", "end")
        self.set_status("輸出已清除")

    def validate_inputs(self):
        target = self.target_var.get().strip()
        shots_str = self.shots_var.get().strip()

        if len(target) < 2:
            raise ValueError("目標 bitstring 至少要 2 位，例如 11 或 1011")
        if any(ch not in "01" for ch in target):
            raise ValueError("目標 bitstring 只能包含 0 和 1")

        if not shots_str.isdigit():
            raise ValueError("Shots 必須是正整數")
        shots = int(shots_str)
        if shots <= 0:
            raise ValueError("Shots 必須大於 0")

        return target, shots

    def on_run(self):
        try:
            target, shots = self.validate_inputs()
        except Exception as e:
            messagebox.showerror("輸入錯誤", str(e))
            return

        self.btn_run.config(state="disabled")
        self.set_status("執行中...")

        try:
            qc, iterations, counts = run_grover(target, shots)

            self.show_info(target, shots, len(target), iterations)
            self.show_counts(counts, target)
            self.show_stats(counts, target, shots)
            self.show_circuit(qc)

            self.set_status("完成")
        except Exception as e:
            messagebox.showerror("執行錯誤", str(e))
            self.set_status("執行失敗")
        finally:
            self.btn_run.config(state="normal")

    def show_info(self, target, shots, n_qubits, iterations):
        self.info_text.delete("1.0", "end")
        self.info_text.insert("end", f"Target bitstring : {target}\n")
        self.info_text.insert("end", f"Number of qubits : {n_qubits}\n")
        self.info_text.insert("end", f"Search space size: 2^{n_qubits} = {2 ** n_qubits}\n")
        self.info_text.insert("end", f"Shots            : {shots}\n")
        self.info_text.insert("end", f"Grover iterations: {iterations}\n")
        self.info_text.insert("end", "\n")
        self.info_text.insert(
            "end",
            "流程：Hadamard 疊加 → Oracle phase flip → Diffuser amplitude amplification → Measurement\n",
        )

    def show_counts(self, counts, target):
        self.counts_text.delete("1.0", "end")
        total = sum(counts.values())
        ordered = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        self.counts_text.insert("end", f"{'State':<12}{'Counts':<12}{'Probability':<14}Remark\n")
        self.counts_text.insert("end", "-" * 52 + "\n")

        for bitstring, cnt in ordered:
            prob = cnt / total
            remark = "<-- target" if bitstring == target else ""
            self.counts_text.insert(
                "end",
                f"{bitstring:<12}{cnt:<12}{prob:<14.6%}{remark}\n"
            )

    def show_stats(self, counts, target, shots):
        self.stats_text.delete("1.0", "end")

        total = sum(counts.values())
        ordered = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        best_state, best_count = ordered[0]
        target_count = counts.get(target, 0)
        success_prob = target_count / total if total else 0.0

        self.stats_text.insert("end", f"最常出現狀態：\n{best_state}\n\n")
        self.stats_text.insert("end", f"Target：\n{target}\n\n")
        self.stats_text.insert("end", f"Target counts：\n{target_count} / {shots}\n\n")
        self.stats_text.insert("end", f"Target probability：\n{success_prob:.6%}\n\n")
        self.stats_text.insert("end", f"是否成功放大目標態：\n{'是' if best_state == target else '否'}\n")

    def show_circuit(self, qc: QuantumCircuit):
        self.circuit_text.delete("1.0", "end")
        circuit_ascii = qc.draw(output="text").single_string()
        self.circuit_text.insert("end", circuit_ascii)


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    GroverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()