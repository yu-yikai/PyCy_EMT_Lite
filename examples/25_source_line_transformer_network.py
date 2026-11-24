"""完整单相线性供电网：两π段线路、变压器与固定阻抗负荷。

运行：uv run python examples/25_source_line_transformer_network.py

src--Rs--send--两π段线路(mid)--recv--Rp--Lp--core--理想T--secondary
           |                         |           |               |
        Rcomp_s/Lcomp_s          Rcomp_r/Lcomp_r  Rm||Lm       Rsec--Lz1
           |                         |           |               |
           0                         0           0            load_bus--0V表--load
                                                                 |           |
                                                               Rzs/Lzs     Rload||Cload
                                                                 |           |
                                                                 0           0

线路send/mid/recv另有对地C和G。150km仅用两个有限π段，不是宽频传播模型。
从原60Hz正弦稳态开始，全部8个电感电流和4个电容电压均为非零初值。
额定P/Q用于换算固定R/L/C；实际功率由端电压决定，没有恒功率控制或冷启动。
"""

import cmath
import math

import numpy as np

from pycy_emt_lite import (
    Capacitor,
    Inductor,
    Resistor,
    SimulationConfig,
    SinglePhaseTransformer,
    VoltageSource,
)
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

FREQUENCY = 60.0
OMEGA = 2 * math.pi * FREQUENCY
PRIMARY_RATED_RMS = 735000 / math.sqrt(3)
SECONDARY_RATED_RMS = 315000 / math.sqrt(3)
SOURCE_PEAK_VOLTAGE = math.sqrt(2) * PRIMARY_RATED_RMS
SOURCE_RESISTANCE = 2.0
TIME_STEP = 10e-6
STOP_TIME = 0.05

# SPS原线路在60Hz作双曲修正；Y为一整节的总分路导纳，各端取Y/2。
LINE_LENGTH_KM = 150.0
LINE_SECTIONS = 2
LINE_R_PER_KM = 0.011
LINE_L_PER_KM = 0.8674e-3
LINE_C_PER_KM = 13.41e-9
line_z = complex(LINE_R_PER_KM, OMEGA * LINE_L_PER_KM)
line_y = complex(0, OMEGA * LINE_C_PER_KM)
line_zc = cmath.sqrt(line_z / line_y)
line_gamma = cmath.sqrt(line_z * line_y)
section_length = LINE_LENGTH_KM / LINE_SECTIONS
section_z = line_zc * cmath.sinh(line_gamma * section_length)
section_y = 2 / line_zc * cmath.tanh(line_gamma * section_length / 2)
LINE_RESISTANCE = section_z.real
LINE_INDUCTANCE = section_z.imag / OMEGA
LINE_CAPACITANCE = section_y.imag / OMEGA
LINE_CONDUCTANCE = section_y.real  # 原生展开确有三条电阻，不能因输入G=0省略

TRANSFORMER_RATING = 750e6 / 3
TURNS_RATIO = 735000 / 315000  # 单相绕组电压比，不再加三相√3系数
primary_base = PRIMARY_RATED_RMS**2 / TRANSFORMER_RATING
secondary_base = SECONDARY_RATED_RMS**2 / TRANSFORMER_RATING
PRIMARY_RESISTANCE = 0.001 * primary_base
PRIMARY_INDUCTANCE = 0.15 * primary_base / OMEGA
SECONDARY_RESISTANCE = 0.001 * secondary_base
MAGNETIZING_RESISTANCE = 500 * primary_base
MAGNETIZING_INDUCTANCE = 500 * primary_base / OMEGA

# 两端补偿是有损串联RL；P/Q均为这个单相块的额定值，不能再除3。
COMPENSATION_ACTIVE_POWER = 110e6 / 300
COMPENSATION_INDUCTIVE_VAR = 110e6
compensation_z = PRIMARY_RATED_RMS**2 / complex(COMPENSATION_ACTIVE_POWER, -COMPENSATION_INDUCTIVE_VAR)
COMPENSATION_RESISTANCE = compensation_z.real
COMPENSATION_INDUCTANCE = compensation_z.imag / OMEGA
Z1_RESISTANCE = 0.734
Z1_INDUCTANCE = 0.02085
ZS_RESISTANCE = 11.0
ZS_INDUCTANCE = 0.2925
SECONDARY_SERIES_RESISTANCE = SECONDARY_RESISTANCE + Z1_RESISTANCE
LOAD_ACTIVE_POWER = 200e6
LOAD_CAPACITIVE_VAR = 50e6
LOAD_RESISTANCE = SECONDARY_RATED_RMS**2 / LOAD_ACTIVE_POWER
LOAD_CAPACITANCE = LOAD_CAPACITIVE_VAR / (OMEGA * SECONDARY_RATED_RMS**2)


def steady_phasors() -> dict[str, complex]:
    """仅本例的复阻抗递推；峰值相量q表示Im(q·exp(jωt))。

    从负荷向源逐级合并，再向前算节点与支流。初值取虚部，不读取参考波形。
    """
    zcomp = complex(COMPENSATION_RESISTANCE, OMEGA * COMPENSATION_INDUCTANCE)
    zzs = complex(ZS_RESISTANCE, OMEGA * ZS_INDUCTANCE)
    yload = complex(1 / LOAD_RESISTANCE, OMEGA * LOAD_CAPACITANCE)
    zload_bus = 1 / (yload + 1 / zzs)
    zsecondary = SECONDARY_SERIES_RESISTANCE + 1j * OMEGA * Z1_INDUCTANCE + zload_bus
    ymag = 1 / MAGNETIZING_RESISTANCE + 1 / (1j * OMEGA * MAGNETIZING_INDUCTANCE)
    zcore = 1 / (ymag + 1 / (TURNS_RATIO**2 * zsecondary))
    zprimary = complex(PRIMARY_RESISTANCE, OMEGA * PRIMARY_INDUCTANCE) + zcore
    zline = complex(LINE_RESISTANCE, OMEGA * LINE_INDUCTANCE)
    yline = complex(LINE_CONDUCTANCE, OMEGA * LINE_CAPACITANCE)
    yrecv = yline / 2 + 1 / zcomp + 1 / zprimary
    ymid = yline + 1 / (zline + 1 / yrecv)
    ysend = yline / 2 + 1 / zcomp + 1 / (zline + 1 / ymid)

    vsend = SOURCE_PEAK_VOLTAGE / (1 + SOURCE_RESISTANCE * ysend)
    vmid = vsend / (1 + zline * ymid)
    vrecv = vmid / (1 + zline * yrecv)
    ip = vrecv / zprimary
    vcore = ip * zcore
    vsecondary = vcore / TURNS_RATIO
    iz1 = vsecondary / zsecondary
    vload = iz1 * zload_bus
    return {
        "v:src": complex(SOURCE_PEAK_VOLTAGE), "v:send": vsend, "v:mid": vmid,
        "v:recv": vrecv, "v:core": vcore, "v:secondary": vsecondary,
        "v:load_bus": vload, "v:load": vload,
        "i:Rs": (SOURCE_PEAK_VOLTAGE - vsend) / SOURCE_RESISTANCE,
        "i:Lline1": (vsend - vmid) / zline, "i:Lline2": (vmid - vrecv) / zline,
        "i:Lcomp_s": vsend / zcomp, "i:Lcomp_r": vrecv / zcomp,
        "i:Lp": ip, "i:Lm": vcore / (1j * OMEGA * MAGNETIZING_INDUCTANCE),
        "i:Lz1": iz1, "i:Lzs": vload / zzs, "i:Iload": yload * vload,
    }


def create_components() -> tuple[Component, ...]:
    """按源、两π、补偿、T、末端支路分组；只用现有线性元件。"""
    q = steady_phasors()
    return (
        VoltageSource("Vs", "src", "0", lambda t: SOURCE_PEAK_VOLTAGE * math.sin(OMEGA * t),
                      derivative=lambda t: SOURCE_PEAK_VOLTAGE * OMEGA * math.cos(OMEGA * t)),
        Resistor("Rs", "src", "send", SOURCE_RESISTANCE),
        # 两节串联RL；中点相邻的两个半电容/半电导精确并联。
        Resistor("Rline1", "send", "line1_rl", LINE_RESISTANCE),
        Inductor("Lline1", "line1_rl", "mid", LINE_INDUCTANCE, initial_current=q["i:Lline1"].imag),
        Resistor("Rline2", "mid", "line2_rl", LINE_RESISTANCE),
        Inductor("Lline2", "line2_rl", "recv", LINE_INDUCTANCE, initial_current=q["i:Lline2"].imag),
        Capacitor("Csend", "send", "0", LINE_CAPACITANCE / 2, initial_voltage=q["v:send"].imag),
        Capacitor("Cmid", "mid", "0", LINE_CAPACITANCE, initial_voltage=q["v:mid"].imag),
        Capacitor("Crecv", "recv", "0", LINE_CAPACITANCE / 2, initial_voltage=q["v:recv"].imag),
        Resistor("Gsend", "send", "0", 2 / LINE_CONDUCTANCE),
        Resistor("Gmid", "mid", "0", 1 / LINE_CONDUCTANCE),
        Resistor("Grecv", "recv", "0", 2 / LINE_CONDUCTANCE),
        # 两补偿支流统一为母线→地；它们与线路充电一起改变两端总流。
        Resistor("Rcomp_s", "send", "comp_s_rl", COMPENSATION_RESISTANCE),
        Inductor("Lcomp_s", "comp_s_rl", "0", COMPENSATION_INDUCTANCE,
                 initial_current=q["i:Lcomp_s"].imag),
        Resistor("Rcomp_r", "recv", "comp_r_rl", COMPENSATION_RESISTANCE),
        Inductor("Lcomp_r", "comp_r_rl", "0", COMPENSATION_INDUCTANCE,
                 initial_current=q["i:Lcomp_r"].imag),
        # 励磁在原边漏感之后，纯理想T内部不再重复加入励磁或漏阻抗。
        Resistor("Rp", "recv", "primary_rl", PRIMARY_RESISTANCE),
        Inductor("Lp", "primary_rl", "core", PRIMARY_INDUCTANCE, initial_current=q["i:Lp"].imag),
        Resistor("Rm", "core", "0", MAGNETIZING_RESISTANCE),
        Inductor("Lm", "core", "0", MAGNETIZING_INDUCTANCE, initial_current=q["i:Lm"].imag),
        SinglePhaseTransformer("T", "core", "0", "secondary", "0", TURNS_RATIO),
        # R2与Z1的R之间没有分流，可合并；损耗仍可用同一i:Lz1分别计算。
        Resistor("Rsec", "secondary", "secondary_rl", SECONDARY_SERIES_RESISTANCE),
        Inductor("Lz1", "secondary_rl", "load_bus", Z1_INDUCTANCE, initial_current=q["i:Lz1"].imag),
        Resistor("Rzs", "load_bus", "zs_rl", ZS_RESISTANCE),
        Inductor("Lzs", "zs_rl", "0", ZS_INDUCTANCE, initial_current=q["i:Lzs"].imag),
        # 0V表只测R||C总流；Zs接在表前，不能并入负荷测量。
        VoltageSource("Iload", "load_bus", "load", 0.0),
        Resistor("Rload", "load", "0", LOAD_RESISTANCE),
        Capacitor("Cload", "load", "0", LOAD_CAPACITANCE, initial_voltage=q["v:load"].imag),
    )


def print_summary(result: SimulationResult) -> None:
    """显示实际稳态RMS与单相P/Q；3周期傅里叶读数不使用额定功率代替。"""
    time = result.series("time")
    phase = np.exp(-1j * OMEGA * time)
    duration = time[-1] - time[0]

    def port(voltage: str, current: str) -> tuple[float, float, complex]:
        v = 2j / duration * np.trapezoid(result.series(voltage) * phase, time)
        i = 2j / duration * np.trapezoid(result.series(current) * phase, time)
        return rms(result, voltage), rms(result, current), v * i.conjugate() / 2

    source_v, source_i, source_power = port("v:src", "i:Rs")
    load_v, load_i, load_power = port("v:load", "i:Iload")
    print(f"源：{source_v / 1000:.3f}kV RMS，{source_i:.3f}A RMS，"
          f"P={source_power.real / 1e6:.6f}MW，Q={source_power.imag / 1e6:.6f}Mvar。")
    print(f"RC负荷：{load_v / 1000:.3f}kV RMS，{load_i:.3f}A RMS，"
          f"P={load_power.real / 1e6:.6f}MW，Q={load_power.imag / 1e6:.6f}Mvar。")
    print(f"其余电阻（含Zs、补偿、绕组、线路G和铁损）耗散约"
          f"{(source_power.real - load_power.real) / 1e6:.6f}MW。")
    print("从非零稳态初值开始；额定200MW/50Mvar只用于固定R/C换算，并非实际恒功率。")
    print("线路充电与补偿使源流和两段串联流不同；i:Lz1=i:Lzs+i:Iload。")


def define_case() -> CaseDefinition:
    plots = (
        PlotSpec(("v:send", "v:recv", "v:load"), "voltages.png",
                 title="Line sending/receiving and transformed load voltages (V)"),
        PlotSpec(("i:Rs", "i:Lline1", "i:Lline2"), "line_currents.png",
                 title="Source and line currents: charging and compensation (A)"),
        PlotSpec(("i:Lz1", "i:Lzs", "i:Iload"), "load_currents.png",
                 title="Secondary branch = shunt RL + parallel RC load current (A)"),
    )
    return CaseDefinition(
        name="source_line_transformer", components=create_components(),
        config=SimulationConfig(TIME_STEP, STOP_TIME, method="trapezoidal", linear_solver_mode="reuse"),
        plots=plots, summary=print_summary,
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
