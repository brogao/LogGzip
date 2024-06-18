# =========================================================================
# Copyright (C) 2016-2023 LOGPAI (https://github.com/logpai).
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========================================================================

import sys
sys.path.append("../../")
from logparser.LogCluster import LogParser
from logparser.utils import evaluator
import os
import pandas as pd
import time

input_dir = "../../data/loghub_2k/"  # The input directory of log file
output_dir = "LogCluster_result/"  # The output directory of parsing results

benchmark_settings = {
    "HDFS": {
        "log_file": "HDFS/HDFS_2k.log",
        "log_format": "<Date> <Time> <Pid> <Level> <Component>: <Content>",
        "regex": [r"blk_-?\d+", r"(\d+\.){3}\d+(:\d+)?"],
        "rsupport": 10,
    },
    "Hadoop": {
        "log_file": "Hadoop/Hadoop_2k.log",
        "log_format": "<Date> <Time> <Level> \[<Process>\] <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "rsupport": 10,
    },
    "Spark": {
        "log_file": "Spark/Spark_2k.log",
        "log_format": "<Date> <Time> <Level> <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"\b[KGTM]?B\b", r"([\w-]+\.){2,}[\w-]+"],
        "rsupport": 10,
    },
    "Zookeeper": {
        "log_file": "Zookeeper/Zookeeper_2k.log",
        "log_format": "<Date> <Time> - <Level>  \[<Node>:<Component>@<Id>\] - <Content>",
        "regex": [r"(/|)(\d+\.){3}\d+(:\d+)?"],
        "rsupport": 0.5,
    },
    "BGL": {
        "log_file": "BGL/BGL_2k.log",
        "log_format": "<Label> <Timestamp> <Date> <Node> <Time> <NodeRepeat> <Type> <Component> <Level> <Content>",
        "regex": [r"core\.\d+"],
        "rsupport": 2,
    },
    "HPC": {
        "log_file": "HPC/HPC_2k.log",
        "log_format": "<LogId> <Node> <Component> <State> <Time> <Flag> <Content>",
        "regex": [r"=\d+"],
        "rsupport": 0.1,
    },
    "Thunderbird": {
        "log_file": "Thunderbird/Thunderbird_2k.log",
        "log_format": "<Label> <Timestamp> <Date> <User> <Month> <Day> <Time> <Location> <Component>(\[<PID>\])?: <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "rsupport": 2,
    },
    "Windows": {
        "log_file": "Windows/Windows_2k.log",
        "log_format": "<Date> <Time>, <Level>                  <Component>    <Content>",
        "regex": [r"0x.*?\s"],
        "rsupport": 0.2,
    },
    "Linux": {
        "log_file": "Linux/Linux_2k.log",
        "log_format": "<Month> <Date> <Time> <Level> <Component>(\[<PID>\])?: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"\d{2}:\d{2}:\d{2}"],
        "rsupport": 40,
    },
    "Android": {
        "log_file": "Android/Android_2k.log",
        "log_format": "<Date> <Time>  <Pid>  <Tid> <Level> <Component>: <Content>",
        "regex": [
            r"(/[\w-]+)+",
            r"([\w-]+\.){2,}[\w-]+",
            r"\b(\-?\+?\d+)\b|\b0[Xx][a-fA-F\d]+\b|\b[a-fA-F\d]{4,}\b",
        ],
        "rsupport": 1,
    },
    "HealthApp": {
        "log_file": "HealthApp/HealthApp_2k.log",
        "log_format": "<Time>\|<Component>\|<Pid>\|<Content>",
        "regex": [],
        "rsupport": 7,
    },
    "Apache": {
        "log_file": "Apache/Apache_2k.log",
        "log_format": "\[<Time>\] \[<Level>\] <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "rsupport": 30,
    },
    "Proxifier": {
        "log_file": "Proxifier/Proxifier_2k.log",
        "log_format": "\[<Time>\] <Program> - <Content>",
        "regex": [
            r"<\d+\ssec",
            r"([\w-]+\.)+[\w-]+(:\d+)?",
            r"\d{2}:\d{2}(:\d{2})*",
            r"\b[KGTM]?B\b",
        ],
        "rsupport": 10,
    },
    "OpenSSH": {
        "log_file": "OpenSSH/OpenSSH_2k.log",
        "log_format": "<Date> <Day> <Time> <Component> sshd\[<Pid>\]: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"([\w-]+\.){2,}[\w-]+"],
        "rsupport": 0.1,
    },
    "OpenStack": {
        "log_file": "OpenStack/OpenStack_2k.log",
        "log_format": "<Logrecord> <Date> <Time> <Pid> <Level> <Component> \[<ADDR>\] <Content>",
        "regex": [r"((\d+\.){3}\d+,?)+", r"/.+?\s", r"\d+"],
        "rsupport": 3,
    },
    "Mac": {
        "log_file": "Mac/Mac_2k.log",
        "log_format": "<Month>  <Date> <Time> <User> <Component>\[<PID>\]( \(<Address>\))?: <Content>",
        "regex": [r"([\w-]+\.){2,}[\w-]+"],
        "rsupport": 0.2,
    },
}

bechmark_result = []
for dataset, setting in benchmark_settings.items():
    print("\n=== Evaluation on %s ===" % dataset)
    indir = os.path.join(input_dir, os.path.dirname(setting["log_file"]))
    log_file = os.path.basename(setting["log_file"])

    parser = LogParser(
        indir,
        setting["log_format"],
        output_dir,
        rex=setting["regex"],
        rsupport=setting["rsupport"],
    )
    # 开始解析前获取当前时间
    start_time = time.time()
    # 开始解析
    parser.parse(log_file)
    # 解析完成后获取当前时间并计算解析所需时间
    parsing_time = time.time() - start_time
    # 保留三位小数
    parsing_time = round(parsing_time, 3)
    # 更新调用evaluate函数
    GA, PA, FGA, PTA, RTA, FTA = evaluator.evaluate(
        groundtruth=os.path.join(indir, log_file + "_structured_cor.csv"),
        # groundtruth=os.path.join(indir, log_file + "_structured_corrected.csv"),
        parsedresult=os.path.join(output_dir, log_file + "_structured.csv"),
    )
    # 对所有指标保留三位小数
    GA = round(GA, 3)
    PA = round(PA, 3)
    FGA = round(FGA, 3)
    FTA = round(FTA, 3)
    PTA = round(PTA, 3)
    RTA = round(RTA, 3)

    benchmark_result.append([dataset, GA, PA, FGA, PTA, RTA, FTA, parsing_time])

print("=== Overall evaluation results ===")
df_result = pd.DataFrame(benchmark_result, columns=["Dataset", "GA", "PA", "FGA", "PTA", "RTA", "FTA", "P_Time"])
df_result.set_index("Dataset", inplace=True)

# 计算各指标的平均值，并保留三位小数
average_GA = round(df_result["GA"].mean(), 3)
average_PA = round(df_result["PA"].mean(), 3)
average_FGA = round(df_result["FGA"].mean(), 3)
average_PTA = round(df_result["PTA"].mean(), 3)
average_RTA = round(df_result["RTA"].mean(), 3)
average_FTA = round(df_result["FTA"].mean(), 3)
average_parsing_time = round(df_result["P_Time"].mean(), 3)

# 将新行添加到DataFrame中，包含平均值
df_result.loc["Average"] = [average_GA, average_PA, average_FGA, average_PTA,
                            average_RTA, average_FTA, average_parsing_time]
print(df_result)
df_result.to_csv("LogCluster_bechmark_result.csv", float_format="%.6f")
