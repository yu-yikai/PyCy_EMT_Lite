"""
文件名称：variables.py
文件作用：管理 MNA 中除节点电压外的支路电流未知量。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class VariableManager:
    """支路电流变量管理器。

    理想电压源和电感等元件会引入额外支路电流未知量。本管理器为它们分配相对索引，
    最终矩阵中的实际索引为 `branch_offset + branch_index`。
    """

    _branch_currents: dict[str, int] = field(default_factory=dict)

    def add_branch_current(self, name: str) -> int:
        """注册支路电流变量并返回相对索引。"""

        if name in self._branch_currents:
            raise ValueError(f"支路电流变量 {name!r} 已存在。")
        index = len(self._branch_currents)
        self._branch_currents[name] = index
        return index

    @property
    def branch_count(self) -> int:
        """返回支路电流变量数量。"""

        return len(self._branch_currents)

    @property
    def branch_names(self) -> list[str]:
        """按索引顺序返回支路电流变量名称。"""

        return [name for name, _ in sorted(self._branch_currents.items(), key=lambda item: item[1])]
