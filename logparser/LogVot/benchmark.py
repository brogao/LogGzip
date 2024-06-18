#benchmark.py
import sys
sys.path.append("../../")
from logparser.Drain import LogParser
from logparser.utils import evaluator
import os
import pandas as pd
import time
from collections import Counter
from logparser.LogVot.Drain import LogParser as DrainParser
from logparser.LogVot.LogMine import LogParser as LogMineParser
from logparser.LogVot.Brain import LogParser as BrainParser

input_dir = "../../data/loghub_2k/"  # The input directory of log file
output_dir = "LogVot_result/"  # The output directory of parsing results

benchmark_settings = {
    "HDFS": {
        "log_file": "HDFS/HDFS_2k.log",
        "log_format": "<Date> <Time> <Pid> <Level> <Component>: <Content>",
        "regex": [r"blk_-?\d+", r"(\d+\.){3}\d+(:\d+)?"],
        "drain": {
            "depth": 4,
            "st": 0.5,
        },
        "brain": {
            "delimiter": [""],
            "theshold": 2,
        },
        "logmine": {
            "max_dist": 0.005,
            "k": 1,
            "levels": 2,
        }
    },
    "Hadoop": {
        "log_file": "Hadoop/Hadoop_2k.log",
        "log_format": "<Date> <Time> <Level> \[<Process>\] <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "drain": {
            "depth": 4,
            "st": 0.5,
        },
        "brain": {
            "delimiter": [],
            "theshold": 6,
        },
        "logmine": {
            "max_dist": 0.005,
            "k": 1,
            "levels": 2,
        }
    },
    "Spark": {
        "log_file": "Spark/Spark_2k.log",
        "log_format": "<Date> <Time> <Level> <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"\b[KGTM]?B\b", r"([\w-]+\.){2,}[\w-]+"],
        "drain": {
            "depth": 4,
            "st": 0.5,
        },
        "brain": {
            "delimiter": [],
            "theshold": 4,
        },
        "logmine": {
            "max_dist": 0.01,
            "k": 1,
            "levels": 2,
        }
    },

}
# 创建一个字典来存储每个数据集的解析结果
ensemble_results = {}


def majority_vote(votes):
    # 对结果进行投票
    vote_count = Counter(votes)
    winner = vote_count.most_common(1)[0][0]
    return winner

# 定义用于初始化不同解析器的函数
def init_drain_parser(setting, indir, outdir):
    return DrainParser(
        log_format=setting["log_format"],
        indir=indir,
        outdir=outdir,
        rex=setting["regex"],
        depth=setting["drain"]["depth"],
        st=setting["drain"]["st"]
    )
def init_brain_parser(setting, indir, outdir):
    return BrainParser(
        log_format=setting["log_format"],
        indir=indir,
        outdir=outdir,
        rex=setting["regex"],
        delimeter=setting["brain"]["delimiter"],
        logname=dataset,
        threshold=setting["brain"]["theshold"]
    )

def init_logmine_parser(setting, indir, outdir):
    return LogMineParser(
        log_format=setting["log_format"],
        indir=indir,
        outdir=outdir,
        rex=setting["regex"],
        max_dist=setting["logmine"]["max_dist"],
        k=setting["logmine"]["k"],
        levels=setting["logmine"]["levels"]
    )

parsers = {
    "Drain": init_drain_parser,
    "brain": init_brain_parser,
    "LogMine": init_logmine_parser
}

bechmark_result = []
for dataset, setting in benchmark_settings.items():
    print("\n=== Evaluation on %s ===" % dataset)
    indir = os.path.join(input_dir, os.path.dirname(setting["log_file"]))
    log_file = os.path.basename(setting["log_file"])

    # 开始解析前获取当前时间
    start_time = time.time()
    all_templates = []
    for parser_name, parser_init in parsers.items():
        parser = parser_init(setting, indir, output_dir)
        parser.parse(log_file)
        parsed_result = parser.get_parsed_templates()  # 获取解析后的模板列表
        all_templates.extend(parsed_result)

        # 投票选择最常见的模板
    template_counts = Counter(all_templates)
    final_templates = [template for template, count in template_counts.items() if count > len(parsers) / 2]

    # 存储结果
    ensemble_results[dataset] = final_templates

    # 解析完成后获取当前时间并计算解析所需时间
    parsing_time = time.time() - start_time
    # 存储解析结果到文件
    parsedresult_file = os.path.join(output_dir, log_file + "_structured.csv")
    with open(parsedresult_file, "w") as f:
        for template in final_templates:
            f.write(f"{template}\n")

    F1_measure, accuracy = evaluator.evaluate(
        groundtruth=os.path.join(indir, log_file + "_structured.csv"),
        # groundtruth=os.path.join(indir, log_file + "_structured_corrected.csv"),
        parsedresult=os.path.join(output_dir, log_file + "_structured.csv"),
    )
    # 在结果列表中添加解析时间
    bechmark_result.append([dataset, F1_measure, accuracy, parsing_time])

print("\n=== Overall evaluation results ===")
df_result = pd.DataFrame(bechmark_result, columns=["Dataset", "F1_measure", "Accuracy", "ParsingTime"])
df_result.set_index("Dataset", inplace=True)

# 计算F1_measure、Accuracy和ParsingTime的平均值
average_f1 = df_result["F1_measure"].mean()
average_accuracy = df_result["Accuracy"].mean()
average_parsing_time = df_result["ParsingTime"].mean()
# 将新行添加到DataFrame中，包含平均值
df_result.loc["Average"] = [average_f1, average_accuracy, average_parsing_time]
print(df_result)
