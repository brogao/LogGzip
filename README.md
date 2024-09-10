
# Logparser


We recommend installing the logparser package and requirements via pip install.
#### This project includes the baseline used in LogGzip.
Log parsers available:
Publication	Parser	Paper Title	Benchmark
QSIC'08	AEL	Abstracting Execution Logs to Execution Events for Enterprise Applications, by Zhen Ming Jiang, Ahmed E. Hassan, Parminder Flora, Gilbert Hamann.
CNSM'15	LenMa	Length Matters: Clustering System Log Messages using Length of Words, by Keiichi Shima.	↗️
CIKM'16	LogMine	LogMine: Fast Pattern Recognition for Log Analytics, by Hossein Hamooni, Biplob Debnath, Jianwu Xu, Hui Zhang, Geoff Jiang, Adbullah Mueen. [NEC]	↗️
ICDM'16	Spell	Spell: Streaming Parsing of System Event Logs, by Min Du, Feifei Li.	↗️
ICWS'17	Drain	Drain: An Online Log Parsing Approach with Fixed Depth Tree, by Pinjia He, Jieming Zhu, Zibin Zheng, and Michael R. Lyu.	↗️
TSE'20	Logram	Logram: Efficient Log Parsing Using n-Gram Dictionaries, by Hetong Dai, Heng Li, Che-Shao Chen, Weiyi Shang, and Tse-Hsun (Peter) Chen.	↗️
TSC'23	Brain	Brain: Log Parsing with Bidirectional Parallel Tree, by Siyu Yu, Pinjia He, Ningjiang Chen, Yifan Wu.	↗️

```

In particular, the package depends on the following requirements. Note that regex matching in Python is brittle, so we recommend fixing the regex library to version 2022.3.2.

+ python 3.8+
+ regex 2023.10.3
+ numpy
+ pandas
+ scipy
+ scikit-learn


### Get started

1. Run the benchmark:
  
    For each log parser, we provide a benchmark script to run log parsing on the [loghub_24 datasets](https://github.com/logpai/logparser/tree/main/data#loghub_2k) for evaluating parsing accuarcy. You can also use [other benchmark datasets for log parsing](https://github.com/logpai/logparser/tree/main/data#datasets).

    ```
    cd logparser/LogGzip
    python benchmark.py
    ```

