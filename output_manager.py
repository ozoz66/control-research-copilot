# -*- coding: utf-8 -*-
"""
输出管理器 - AutoControl-Scientist
负责管理项目输出目录结构和文件保存
"""

import os
import re
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional
from logger_config import get_logger

logger = get_logger(__name__)


class OutputManager:
    """
    输出管理器
    管理项目输出的目录结构：output/项目名/paper/ 和 output/项目名/code/
    """

    def __init__(self, base_output_dir: str = "./output"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.current_project_dir: Optional[Path] = None
        self.paper_dir: Optional[Path] = None
        self.code_dir: Optional[Path] = None

    def create_project(self, topic: str) -> Path:
        """
        创建新项目目录结构

        Args:
            topic: 研究课题名称

        Returns:
            项目根目录路径
        """
        # 生成项目名：简短英文名称
        project_name = self._generate_short_name(topic)

        # 创建目录结构
        self.current_project_dir = self.base_output_dir / project_name
        self.paper_dir = self.current_project_dir / "paper"
        self.code_dir = self.current_project_dir / "code"

        self.current_project_dir.mkdir(parents=True, exist_ok=True)
        self.paper_dir.mkdir(exist_ok=True)
        self.code_dir.mkdir(exist_ok=True)
        (self.code_dir / "matlab").mkdir(exist_ok=True)
        (self.code_dir / "dsp").mkdir(exist_ok=True)

        return self.current_project_dir

    def _generate_short_name(self, topic: str) -> str:
        """
        从研究课题生成简短英文项目名

        Args:
            topic: 研究课题（中文或英文）

        Returns:
            简短英文项目名
        """
        # 关键词映射表
        keyword_map = {
            # 控制方法
            "自适应": "adaptive", "滑模": "smc", "模糊": "fuzzy",
            "神经网络": "nn", "强化学习": "rl", "鲁棒": "robust",
            "预测": "mpc", "最优": "optimal", "迭代学习": "ilc",
            "重复": "rc", "反步": "backstep", "容错": "ft",
            "分布式": "distributed", "协同": "coop", "事件触发": "event",
            # 观测器
            "扩展状态观测器": "eso", "ESO": "eso", "观测器": "obs",
            "卡尔曼": "kalman", "扰动观测": "dob",
            # 性能目标
            "抖动": "chatter", "有限时间": "finite", "收敛": "conv",
            "跟踪": "track", "抑制": "reject", "稳定": "stable",
            # 应用
            "电机": "motor", "机械臂": "arm", "无人机": "uav",
            "车辆": "vehicle", "悬架": "susp", "磁悬浮": "maglev",
        }

        # 提取关键词
        parts = []
        topic_lower = topic.lower()

        for cn, en in keyword_map.items():
            if cn.lower() in topic_lower or cn in topic:
                if en not in parts:
                    parts.append(en)
                if len(parts) >= 3:  # 最多3个关键词
                    break

        # 如果没有匹配到关键词，使用时间戳
        if not parts:
            parts = ["proj"]

        # 添加时间戳确保唯一性
        timestamp = datetime.now().strftime("%m%d_%H%M")
        project_name = "_".join(parts) + "_" + timestamp

        return project_name

    def _sanitize_name(self, name: str, max_len: int = 50) -> str:
        """将名称转换为安全的文件名"""
        safe = re.sub(r'[\\/*?:"<>|]', '', name)
        safe = safe.replace(' ', '_')[:max_len]
        return safe if safe else "unnamed_project"

    def save_latex(self, content: str, filename: str = "paper.tex") -> Path:
        """保存LaTeX文件到paper目录"""
        if not self.paper_dir:
            raise ValueError("请先创建项目目录")
        filepath = self.paper_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def save_matlab_code(self, content: str, filename: str) -> Path:
        """保存MATLAB代码到code/matlab目录"""
        if not self.code_dir:
            raise ValueError("请先创建项目目录")
        filepath = self.code_dir / "matlab" / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def get_matlab_working_dir(self) -> Path:
        """获取MATLAB工作目录（paper目录，图片直接保存在此处供LaTeX使用）"""
        if not self.paper_dir:
            raise ValueError("请先创建项目目录")
        return self.paper_dir

    def save_figure(self, src_path: str, filename: str = None) -> Path:
        """
        将图片保存/复制到paper目录（供LaTeX编译使用）

        Args:
            src_path: 源图片路径
            filename: 目标文件名（可选，默认使用原文件名）

        Returns:
            保存后的文件路径
        """
        import shutil
        if not self.paper_dir:
            raise ValueError("请先创建项目目录")

        src = Path(src_path)
        if not src.exists():
            raise FileNotFoundError(f"图片文件不存在: {src_path}")

        dest_name = filename if filename else src.name
        dest_path = self.paper_dir / dest_name

        if src != dest_path:
            shutil.copy2(src, dest_path)

        return dest_path

    def save_dsp_code(self, content: str, filename: str) -> Path:
        """保存DSP代码到code/dsp目录"""
        if not self.code_dir:
            raise ValueError("请先创建项目目录")
        filepath = self.code_dir / "dsp" / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath

    def compile_pdf(self, tex_filename: str = "paper.tex") -> Optional[Path]:
        """编译LaTeX为PDF"""
        if not self.paper_dir:
            return None
        # 校验文件名安全性
        if not re.match(r'^[\w\-\.]+$', tex_filename) or '..' in tex_filename:
            logger.error("不安全的 tex 文件名: %s", tex_filename)
            return None
        tex_path = self.paper_dir / tex_filename
        if not tex_path.exists():
            return None
        try:
            for _ in range(2):
                subprocess.run(
                    ["pdflatex", "-no-shell-escape", "-interaction=nonstopmode", tex_filename],
                    cwd=self.paper_dir, capture_output=True, timeout=120
                )
            pdf_path = self.paper_dir / tex_filename.replace('.tex', '.pdf')
            if pdf_path.exists():
                self._cleanup_latex_aux()
                return pdf_path
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error("PDF编译失败: %s", e)
        return None

    def _cleanup_latex_aux(self):
        """清理LaTeX辅助文件"""
        if not self.paper_dir:
            return
        for ext in ['.aux', '.log', '.out', '.toc', '.lof', '.lot', '.bbl', '.blg']:
            for f in self.paper_dir.glob(f"*{ext}"):
                f.unlink(missing_ok=True)

    def save_context(self, context, filename: str = "context.json") -> Path:
        """保存上下文到项目目录"""
        if not self.current_project_dir:
            raise ValueError("请先创建项目目录")
        filepath = self.current_project_dir / filename
        context.save_to_file(str(filepath))
        return filepath

    def open_overleaf(self) -> bool:
        """打开浏览器访问Overleaf，用户可手动上传tex文件编译"""
        try:
            webbrowser.open("https://www.overleaf.com/project")
            return True
        except Exception as e:
            logger.error("打开Overleaf失败: %s", e)
            return False

    def get_tex_path(self) -> Optional[Path]:
        """获取tex文件路径，方便用户上传到Overleaf"""
        if self.paper_dir:
            tex_file = self.paper_dir / "paper.tex"
            if tex_file.exists():
                return tex_file
        return None
