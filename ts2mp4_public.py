import subprocess
import re
import datetime
import os
from pathlib import Path

# ==================== ⚙️ 用户配置区域 / User Configuration ====================
# [注意] 使用前请修改下面的路径 / Please update the path below before use
# 示例/Example: r"D:\Downloads\MyVideos"
INPUT_FOLDER_PATH = r"YOUR_INPUT_FOLDER_PATH_HERE"

# 新输出文件夹名称 / Output Folder Name
OUTPUT_FOLDER_NAME = "Converted_Videos_MP4"
# ========================================================================

def clean_filename(original_name):
    """
    文件名清洗核心逻辑：
    1. 去掉后缀 (.ts)
    2. 将 Windows 非法字符 (\ / : * ? " < > |) 替换为空格
    3. 将可能引起问题的字符 (- _) 也替换为空格
    4. 去除首尾和中间多余的空格
    """
    name_no_ext = Path(original_name).stem
    # 正则表达式：匹配非法字符
    pattern = r'[\\/:*?"<>|\-_]' 
    clean_name = re.sub(pattern, ' ', name_no_ext)
    # 把多个连续空格合并成一个，并去掉首尾空格
    return re.sub(r'\s+', ' ', clean_name).strip()

def get_current_time():
    """获取当前时间字符串"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def convert_and_verify():
    # --- 1. 路径准备 ---
    source_dir = Path(INPUT_FOLDER_PATH)
    # 输出目录 = 源目录的父级 + 新文件夹名
    output_dir = source_dir.parent / OUTPUT_FOLDER_NAME

    # 检查源文件夹
    if not source_dir.exists():
        print(f"❌ [错误] 找不到源文件夹，请检查路径:\n   {source_dir}")
        return

    # 创建输出文件夹
    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        print(f"📂 [新建] 输出文件夹已建立: {output_dir}")
    else:
        print(f"📂 [就绪] 输出文件夹已存在: {output_dir}")

    # --- 2. 扫描源文件 ---
    ts_files = list(source_dir.glob("*.ts"))
    total_files = len(ts_files)
    
    if total_files == 0:
        print("⚠️  源文件夹里没有找到任何 .ts 视频文件。")
        return

    # 定义日志文件路径
    log_file_path = output_dir / "_转换运行日志.txt"

    print(f"\n🎬 准备处理 {total_files} 个视频")
    print(f"📝 运行日志将保存在: {log_file_path.name}")
    print("-" * 60)

    # 预期文件名列表 (用于最后的数据核对)
    expected_mp4_names = []
    
    # 计数器
    success_count = 0
    fail_count = 0
    skip_count = 0

    # --- 3. 开始处理循环 ---
    # 使用 'a' (append) 模式写日志，避免覆盖之前的记录，或者用 'w' 每次清空
    with open(log_file_path, "w", encoding="utf-8") as log:
        log.write(f"=== 任务启动: {get_current_time()} ===\n")
        log.write(f"源路径: {source_dir}\n")
        log.write(f"新路径: {output_dir}\n\n")

        for index, ts_file in enumerate(ts_files, 1):
            # A. 计算应该生成的新文件名 (清洗逻辑)
            clean_name = clean_filename(ts_file.name)
            output_file = output_dir / f"{clean_name}.mp4"
            
            # 存入预期列表，稍后核对用
            expected_mp4_names.append(output_file.name)

            # B. 检查是否已存在 (断点续传逻辑)
            status_tag = ""
            log_detail = ""
            
            if output_file.exists():
                skip_count += 1
                status_tag = "⏭️ 跳过"
                log_detail = "文件已存在，无需转换"
            else:
                # C. 不存在则开始转换
                command = [
                    "ffmpeg", 
                    "-i", str(ts_file), 
                    "-c", "copy",   # 核心：无损极速复制
                    "-y",           # 覆盖（虽然前面判断了，但加个保险）
                    str(output_file)
                ]
                
                try:
                    # 执行命令，捕获错误流
                    result = subprocess.run(command, text=True, stderr=subprocess.PIPE)
                    
                    if result.returncode == 0:
                        success_count += 1
                        status_tag = "✅ 成功"
                        log_detail = "转换完成"
                    else:
                        fail_count += 1
                        status_tag = "❌ 失败"
                        # 提取最后一行报错信息
                        error_msg = result.stderr.split('\n')[-2] if result.stderr else "未知FFmpeg错误"
                        log_detail = f"错误: {error_msg}"
                        
                except Exception as e:
                    fail_count += 1
                    status_tag = "❌ 异常"
                    log_detail = f"Python运行错误: {str(e)}"

            # D. 实时显示进度
            completion_rate = (index / total_files) * 100
            # 截取过长的文件名以便显示
            display_name = (clean_name[:25] + '..') if len(clean_name) > 25 else clean_name
            
            print(f"[{index}/{total_files}] "
                  f"{completion_rate:.1f}% | "
                  f"✅:{success_count} ⏭️:{skip_count} ❌:{fail_count} | "
                  f"{status_tag} {display_name}")

            # E. 写入日志
            log.write(f"[{get_current_time()}] {status_tag} | 原名: {ts_file.name} -> 新名: {output_file.name} | {log_detail}\n")
            log.flush() # 确保实时写入硬盘

        # --- 4. 最终数据核对 (Verification) ---
        print("\n" + "="*20 + " 📊 最终核对报告 " + "="*20)
        log.write("\n=== 最终核对报告 ===\n")
        
        # 扫描新文件夹里实际存在的文件
        actual_mp4_files = list(output_dir.glob("*.mp4"))
        actual_mp4_names = [f.name for f in actual_mp4_files]
        
        # 准备总结文案
        summary_lines = [
            f"1. 文件数量对比:",
            f"   - 源视频 (.ts):  {total_files} 个",
            f"   - 新视频 (.mp4): {len(actual_mp4_files)} 个",
            f"\n2. 执行结果统计:",
            f"   - ✅ 本次成功: {success_count}",
            f"   - ⏭️ 本次跳过: {skip_count}",
            f"   - ❌ 本次失败: {fail_count}",
            f"   - 📈 总完成率: {(len(actual_mp4_files)/total_files)*100:.1f}% (基于最终文件数)"
        ]
        
        for line in summary_lines:
            print(line)
            log.write(line + "\n")

        # 核心：比对“预期列表”和“实际列表”的差集
        # missing_files = 预期应该有 - 实际存在的
        missing_files = set(expected_mp4_names) - set(actual_mp4_names)
        
        if missing_files:
            warning_msg = f"\n⚠️ 警告: 发现 {len(missing_files)} 个视频未完成转换 (请检查日志中的失败项):"
            print(warning_msg)
            log.write(warning_msg + "\n")
            for missing in missing_files:
                print(f"   - {missing}")
                log.write(f"   - {missing}\n")
        else:
            success_msg = "\n✨ 完美！所有源视频都已成功对应到新文件夹中。"
            print(success_msg)
            log.write(success_msg + "\n")

        print("=" * 60)
        print(f"新视频存放位置: {output_dir}")
        print(f"详细日志文件:   {log_file_path}")

if __name__ == "__main__":
    convert_and_verify()