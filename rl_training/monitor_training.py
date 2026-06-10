"""监控Residual RL训练进度。

运行方式：
    cd D:\Dunna\Documents\hw-1
    .venv-mujoco\Scripts\activate
    python rl_training\monitor_training.py
"""

import sys
from pathlib import Path
import time

HW1_ROOT = Path(__file__).resolve().parent.parent

def monitor_training():
    """监控训练进度。"""
    output_file = Path("C:/Users/duanj/AppData/Local/Temp/claude/C--Users-duanj/2f34224f-2fee-4325-bb9f-283537501c5a/tasks/bj3vq4s6c.output")

    print("=" * 80)
    print("Residual RL训练监控")
    print("=" * 80)
    print(f"\n日志文件: {output_file}")
    print("\nTensorBoard启动命令:")
    print("  cd D:\\Dunna\\Documents\\hw-1")
    print("  tensorboard --logdir=logs\\residual_rl_curriculum\\tensorboard")
    print("  然后访问: http://localhost:6006")
    print("\n模型保存位置:")
    print("  最终模型: models/residual_rl_curriculum/final_model.zip")
    print("  最佳模型: models/residual_rl_curriculum/best/")
    print("  检查点: models/residual_rl_curriculum/checkpoints/")
    print("\n按Ctrl+C退出监控")
    print("=" * 80)

    if not output_file.exists():
        print(f"\n[警告] 日志文件不存在，训练可能尚未启动")
        return

    last_position = 0

    try:
        while True:
            with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_content = f.read()
                last_position = f.tell()

                if new_content:
                    print(new_content, end='')

            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n监控已停止")


if __name__ == "__main__":
    monitor_training()
