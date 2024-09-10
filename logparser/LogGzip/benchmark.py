#benchmark.py：
import sys
sys.path.append("../../")
from logparser.LogGzip import LogParser
from logparser.utils import evaluator
import os
import pandas as pd
from  logparser.LogGzip.compressors import DefaultCompressor
import time
import zstandard as zstd

input_dir = "../../data/loghub_24/"  # The input directory of log file
output_dir = "LogGzip_result/"  # The output directory of parsing results


benchmark_settings = {
    "HDFS": {
        "log_file": "HDFS/HDFS_2k.log",
        "log_format": "<Date> <Time> <Pid> <Level> <Component>: <Content>",
        "regex": [r"blk_-?\d+", r"(\d+\.){3}\d+(:\d+)?"],
        "threshold": 0.1,
        "mask_digits": True,
        "delimiters": [r'\s+', r'\:'],
    },
    "Hadoop": {
        "log_file": "Hadoop/Hadoop_2k.log",
        "log_format": "<Date> <Time> <Level> \[<Process>\] <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "threshold": 0.1,
        "mask_digits": False,
        "delimiters": [r'\s+', r'\_'],
    },
    "Spark": {
        "log_file": "Spark/Spark_2k.log",
        "log_format": "<Date> <Time> <Level> <Component>: <Content>",
        "regex": [r"(\d+\.){3}\d+", r"\b[KGTM]?B\b", r"([\w-]+\.){2,}[\w-]+"],
        "threshold": 0.85,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "Zookeeper": {
        "log_file": "Zookeeper/Zookeeper_2k.log",
        "log_format": "<Date> <Time> - <Level>  \[<Node>:<Component>@<Id>\] - <Content>",
        "regex": [r"(/|)(\d+\.){3}\d+(:\d+)?"],
        "threshold": 0.9,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "BGL": {
        "log_file": "BGL/BGL_2k.log",
        "log_format": "<Label> <Timestamp> <Date> <Node> <Time> <NodeRepeat> <Type> <Component> <Level> <Content>",
        "regex": [r"core\.\d+"],
        "threshold": 0.7,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "HPC": {
        "log_file": "HPC/HPC_2k.log",
        "log_format": "<LogId> <Node> <Component> <State> <Time> <Flag> <Content>",
        "regex": [r"=\d+"],
        "threshold": 0.8,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "Thunderbird": {
        "log_file": "Thunderbird/Thunderbird_2k.log",
        "log_format": "<Label> <Timestamp> <Date> <User> <Month> <Day> <Time> <Location> <Component>(\[<PID>\])?: <Content>",
        "regex": [r"(\d+\.){3}\d+"],
        "threshold": 0.61,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "Windows": {
        "log_file": "Windows/Windows_2k.log",
        "log_format": "<Date> <Time>, <Level> <Component> <Content>",
        "regex": [r"0x.*?\s"],
        "threshold": 0.7,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "Linux": {
        "log_file": "Linux/Linux_2k.log",
        "log_format": "<Month> <Date> <Time> <Level> <Component>(\[<PID>\])?: <Content>",
        "regex": [],
        "threshold": 0.65,
        "mask_digits": False,
        "delimiters": [r'\s+', r'\(', r'\)', r'\_'],
    },
    "Android": {
        "log_file": "Android/Android_2k.log",
        "log_format": "<Date> <Time>  <Pid>  <Tid> <Level> <Component>: <Content>",
        "regex": [
            r"(/[\w-]+)+",
            r"([\w-]+\.){2,}[\w-]+",
            r"\b(\-?\+?\d+)\b|\b0[Xx][a-fA-F\d]+\b|\b[a-fA-F\d]{4,}\b",
        ],
        "threshold": 0.1,
        "mask_digits": False,
        "delimiters": [r'\s+', r'\_'],
    },
    "HealthApp": {
        "log_file": "HealthApp/HealthApp_2k.log",
        "log_format": "<Time>\|<Component>\|<Pid>\|<Content>",
        "regex": [],
        "threshold": 0.1,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "Apache": {
        "log_file": "Apache/Apache_2k.log",
        "log_format": "\[<Time>\] \[<Level>\] <Content>",
        "regex": [r"(\d+\.){3}\d+", r"^(/[^/]+)+/[^/]+\.[a-zA-Z0-9]+$"],
        "threshold": 0.7,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "Proxifier": {
        "log_file": "Proxifier/Proxifier_2k.log",
        "log_format": "\[<Time>\] <Program> - <Content>",
        "regex": [
            r"([\w-]+\.)+[\w-]+(:\d+)?",
            r"\d{2}:\d{2}(:\d{2})*",
        ],
        "threshold": 0.7,
        "mask_digits": True,
        "delimiters": [r'\s+'],
    },
    "OpenSSH": {
        "log_file": "OpenSSH/OpenSSH_2k.log",
        "log_format": "<Date> <Day> <Time> <Component> sshd\[<Pid>\]: <Content>",
        "regex": [r'ssh2', r"([\w-]+\.){2,}[\w-]+"],
        "threshold": 0.75,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "OpenStack": {
        "log_file": "OpenStack/OpenStack_2k.log",
        "log_format": "<Logrecord> <Date> <Time> <Pid> <Level> <Component> \[<ADDR>\] <Content>",
        "regex": [r"((\d+\.){3}\d+,?)+", r"/.+?\s", r"\d+"],
        "threshold": 0.9,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
    "Mac": {
        "log_file": "Mac/Mac_2k.log",
        "log_format": "<Month>  <Date> <Time> <User> <Component>\[<PID>\]( \(<Address>\))?: <Content>",
        "regex": [r"([\w-]+\.){2,}[\w-]+"],
        "threshold": 0.78,
        "mask_digits": False,
        "delimiters": [r'\s+'],
    },
}

benchmark_result = []
for dataset, setting in benchmark_settings.items():
    print("\n=== Evaluation on %s ===" % dataset)
    indir = os.path.join(input_dir, os.path.dirname(setting["log_file"]))
    log_file = os.path.basename(setting["log_file"])
    # (bz2", "lzma", "zlib",zstd", "brotli","gzip")
    compressor = DefaultCompressor("gzip")
    mask_digits = setting.get("mask_digits", False)
    delimiters = setting.get("delimiters", [r'\s+'])
    parser = LogParser(
        log_format=setting["log_format"],
        indir=indir,
        outdir=output_dir,
        rex=setting["regex"],
        threshold=setting["threshold"],
        mask_digits=mask_digits,
        compressor_instance=compressor,
        delimiters=delimiters
    )
    start_time = time.time()
    parser.parse(log_file)
    parsing_time = time.time() - start_time
    parsing_time = round(parsing_time, 3)
    GA, FGA, PTA, RTA, FTA = evaluator.evaluate(
        groundtruth=os.path.join(indir, log_file + "_structured_rev.csv"),
        # groundtruth=os.path.join(indir, log_file + "_structured_corrected.csv"),
        parsedresult=os.path.join(output_dir, log_file + "_structured.csv"),
    )

    GA = round(GA, 3)
    FGA = round(FGA, 3)
    FTA = round(FTA, 3)
    PTA = round(PTA, 3)
    RTA = round(RTA, 3)

    benchmark_result.append([dataset, GA, FGA, PTA, RTA, FTA, parsing_time])

print("=== Overall evaluation results ===")
df_result = pd.DataFrame(benchmark_result, columns=["Dataset", "GA", "FGA", "PTA", "RTA", "FTA", "P_Time"])
df_result.set_index("Dataset", inplace=True)

average_GA = round(df_result["GA"].mean(), 3)
average_FGA = round(df_result["FGA"].mean(), 3)
average_PTA = round(df_result["PTA"].mean(), 3)
average_RTA = round(df_result["RTA"].mean(), 3)
average_FTA = round(df_result["FTA"].mean(), 3)
average_parsing_time = round(df_result["P_Time"].mean(), 3)

df_result.loc["Average"] = [average_GA, average_FGA, average_PTA,
                            average_RTA, average_FTA, average_parsing_time]
print(df_result)

output_csv_file = os.path.join(output_dir, "LogGzip_results.csv")
df_result.to_csv(output_csv_file)
print(f"Results have been saved to {output_csv_file}")
