"""
hw-1 步态训练辅助设备仿真研究项目
被动动态步行与准被动仿生机构研究

安装说明：
    标准安装:        pip install .
    可编辑安装:      pip install -e .
    开发环境:        pip install -e .[dev]
    完整安装:        pip install -e .[all]
"""

from setuptools import find_packages, setup

# 核心依赖（最小运行环境）
core_requirements = [
    "mujoco>=3.3.7",
    "numpy>=2.0.0",
    "scipy>=1.10.0",
    "imageio>=2.30.0",
    "imageio-ffmpeg>=0.6.0",
    "matplotlib>=3.8.0",
    "pillow>=10.0.0",
    "plotly>=5.17.0",
    "seaborn>=0.12.0",
    "pandas>=2.0.0",
    "pyyaml>=6.0",
]

# 测试依赖
test_requirements = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.1.0",
    "pytest-xdist>=3.3.0",
    "pytest-benchmark>=4.0.0",
]

# 开发依赖
dev_requirements = [
    "black>=24.4.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "pre-commit>=3.5.0",
    "ipython>=8.12.0",
    "jupyter>=1.0.0",
    "types-setuptools>=69.0.0",
    "types-pyyaml>=6.0.0",
]

# 参数优化依赖
optimization_requirements = [
    "cma>=3.2.2",
    "deap>=1.3.1",
    "joblib>=1.3.0",
    "pymoo>=0.6.0",
    "salib>=1.4.7",
    "scikit-learn>=1.3.0",
    "scikit-optimize>=0.9.0",
]

# UI 工具依赖
ui_requirements = [
    "streamlit>=1.28.0",
]

# 安全工具依赖
security_requirements = [
    "safety>=3.0.0",
    "bandit>=1.7.0",
    "pip-audit>=2.6.0",
]

# 文档依赖
docs_requirements = [
    "pdoc>=14.0.0",
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=2.0.0",
    "myst-parser>=2.0.0",
]

# 性能分析依赖
profiling_requirements = [
    "memory-profiler>=0.61.0",
    "line-profiler>=4.1.0",
    "py-spy>=0.3.14",
]

setup(
    name="hw-1",
    version="1.0.0",
    description="步态训练辅助设备仿真研究 - 被动动态步行与准被动仿生机构",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="段泽琪",
    author_email="2024211317@buct.edu.cn",
    url="https://github.com/your-repo/hw-1",
    packages=find_packages(exclude=["tests", "tests.*", "*.tests", "*.tests.*"]),
    python_requires=">=3.9",
    install_requires=core_requirements,
    extras_require={
        "test": test_requirements,
        "dev": dev_requirements + test_requirements,
        "optimization": optimization_requirements,
        "ui": ui_requirements,
        "security": security_requirements,
        "docs": docs_requirements,
        "profiling": profiling_requirements,
        "all": (
            test_requirements
            + dev_requirements
            + optimization_requirements
            + ui_requirements
            + security_requirements
            + docs_requirements
            + profiling_requirements
        ),
    },
    entry_points={
        "console_scripts": [
            "hw1-benchmark=benchmarks.benchmark_runner:main",
            "hw1-monitor=monitoring.system_monitor:main",
            "hw1-profile=advanced_profiling.profile_runner:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Robotics",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
    ],
    keywords="passive dynamic walking, compass gait, biomimetic, MuJoCo, rehabilitation device",
    project_urls={
        "Documentation": "https://github.com/your-repo/hw-1/docs",
        "Source": "https://github.com/your-repo/hw-1",
        "Tracker": "https://github.com/your-repo/hw-1/issues",
    },
    include_package_data=True,
    zip_safe=False,
)
