

from datetime import datetime
from collections import Counter
import os
import pandas as pd
import regex as re

RED = "\033[31m"
RESET = "\033[0m"
PINK = "\033[38;2;255;192;203m"


class LogParser:
    def __init__(
        self,
        logname,
        log_format,
        indir="./",
        outdir="./result/",
        threshold=2,
        delimeter=[],
        rex=[],
    ):
        self.logformat = log_format
        self.path = indir
        self.savePath = outdir
        self.rex = rex
        self.df_log = None
        self.logname = logname
        self.threshold = threshold
        self.delimeter = delimeter
        self.parsed_templates = []  # 用于存储解析的模板

    def parse(self, logName):
        print("Parsing file: " + os.path.join(self.path, logName))
        starttime = datetime.now()
        self.logName = logName

        self.load_data()

        sentences = self.df_log["Content"].tolist()


        group_len, tuple_vector, frequency_vector = self.get_frequecy_vector(
            sentences, self.rex, self.delimeter, self.logname
        )

        (
            sorted_tuple_vector,
            word_combinations,
            word_combinations_reverse,
        ) = self.tuple_generate(group_len, tuple_vector, frequency_vector)

        template_set = {}
        for key in group_len.keys():
            Tree = tupletree(
                sorted_tuple_vector[key],
                word_combinations[key],
                word_combinations_reverse[key],
                tuple_vector[key],
                group_len[key],
            )
            root_set_detail_ID, root_set, root_set_detail = Tree.find_root(0)

            root_set_detail_ID = Tree.up_split(root_set_detail_ID, root_set)
            parse_result = Tree.down_split(
                root_set_detail_ID, self.threshold, root_set_detail
            )
            template_set.update(output_result(parse_result))
        endtime = datetime.now()
        print("Parsing done...")
        print("Time taken   =   " + PINK + str(endtime - starttime) + RESET)

        if not os.path.exists(self.savePath):
            os.makedirs(self.savePath)

        self.generateresult(template_set, sentences)

    def get_parsed_templates(self):
        """获取解析后的模板列表"""
        return self.parsed_templates

    def generateresult(self, template_set, sentences):
        template_ = len(sentences) * [0]
        EventID = len(sentences) * [0]
        IDnumber = 0
        df_out = []
        for k1 in template_set.keys():
            df_out.append(["E" + str(IDnumber), k1, len(template_set[k1])])
            group_accuracy = {""}
            group_accuracy.remove("")
            for i in template_set[k1]:
                template_[i] = " ".join(k1)
                EventID[i] = "E" + str(IDnumber)
            IDnumber += 1

        self.df_log["EventId"] = EventID
        self.df_log["EventTemplate"] = template_
        self.df_log.to_csv(
            os.path.join(self.savePath, self.logName + "_structured.csv"), index=False
        )

        df_event = pd.DataFrame(
            df_out, columns=["EventId", "EventTemplate", "Occurrences"]
        )
        df_event.to_csv(
            os.path.join(self.savePath, self.logName + "_templates.csv"),
            index=False,
            columns=["EventId", "EventTemplate", "Occurrences"],
        )
        # 将模板保存到 parsed_templates
        self.parsed_templates = df_event["EventTemplate"].tolist()

    #这是一个预处理方法，接收一个参数line。方法通过遍历self.rex并对line进行预处理，将每个找到的模式替换为"<*>"。处理完成后的line作为结果返回。
    def preprocess(self, line):
        for currentRex in self.rex:
            line = re.sub(currentRex, "<*>", line)
        return line

    #使用generate_logformat_regex方法生成用于分析日志文件的正则表达式regex和标签列表headers。
    # 然后，它使用log_to_dataframe方法将日志文件转换成一个pandas的DataFrame。
    def load_data(self):
        headers, regex = self.generate_logformat_regex(self.logformat)
        self.df_log = self.log_to_dataframe(
            os.path.join(self.path, self.logName), regex, headers, self.logformat
        )

    #接收一个logformat（日志格式）作为参数，返回一个用于分割日志信息的正则表达式以及相应的标题列表。函数通过拆分logformat参数并构建正则表达式模式完成此任务。
    def generate_logformat_regex(self, logformat):
        """Function to generate regular expression to split log messages"""
        headers = []
        splitters = re.split(r"(<[^<>]+>)", logformat)
        regex = ""
        for k in range(len(splitters)):
            if k % 2 == 0:
                splitter = re.sub(" +", "\\\s+", splitters[k])
                regex += splitter
            else:
                header = splitters[k].strip("<").strip(">")
                regex += "(?P<%s>.*?)" % header
                headers.append(header)
        regex = re.compile("^" + regex + "$")
        return headers, regex

    #通用模块
    def log_to_dataframe(self, log_file, regex, headers, logformat):
        """Function to transform log file to dataframe"""
        log_messages = []
        linecount = 0
        with open(log_file, "r") as fin:
            for line in fin.readlines():
                try:
                    match = regex.search(line.strip())
                    message = [match.group(header) for header in headers]
                    log_messages.append(message)
                    linecount += 1
                except Exception as e:
                    pass
        logdf = pd.DataFrame(log_messages, columns=headers)
        logdf.insert(0, "LineId", None)
        logdf["LineId"] = [i + 1 for i in range(linecount)]
        return logdf

    def tuple_generate(self, group_len, tuple_vector, frequency_vector):
        """
        Generate word combinations
        Output:
            sorted_tuple_vector: each tuple in the tuple_vector will be sorted according their frequencies.
            word_combinations:  words in the log with the same frequency will be grouped as word combinations and will
                                be arranged in descending order according to their frequencies.
            word_combinations_reverse:  The word combinations in the log will be arranged in ascending order according
                                        to their frequencies.

        """
        sorted_tuple_vector = {}
        word_combinations = {}
        word_combinations_reverse = {}
        for key in group_len.keys():
            root_set = {""}
            for fre in tuple_vector[key]:
                sorted_fre_reverse = sorted(fre, key=lambda tup: tup[0], reverse=True)
                root_set.add(sorted_fre_reverse[0])
                sorted_tuple_vector.setdefault(key, []).append(sorted_fre_reverse)
            for fc in frequency_vector[key]:
                number = Counter(fc)
                result = number.most_common()
                sorted_result = sorted(result, key=lambda tup: tup[1], reverse=True)
                sorted_fre = sorted(result, key=lambda tup: tup[0], reverse=True)
                word_combinations.setdefault(key, []).append(sorted_result)
                word_combinations_reverse.setdefault(key, []).append(sorted_fre)
        return sorted_tuple_vector, word_combinations, word_combinations_reverse

    def get_frequecy_vector(self, sentences, filter, delimiter, dataset):
        """
        Counting each word's frequency in the dataset and convert each log into frequency vector
        Output:
            wordlist: log groups based on length
            tuple_vector: the word in the log will be converted into a tuple (word_frequency, word_character, word_position)
            frequency_vector: the word in the log will be converted into its frequency

        """
        group_len = {}
        set = {}
        line_id = 0
        for s in sentences:  # using delimiters to get split words
            for rgex in filter:
                s = re.sub(rgex, "<*>", s)
            for de in delimiter:
                s = re.sub(de, "", s)
            if dataset == "HealthApp":
                s = re.sub(":", ": ", s)
                s = re.sub("=", "= ", s)
                s = re.sub("\|", "| ", s)
            if dataset == "Android":
                s = re.sub("\(", "( ", s)
                s = re.sub("\)", ") ", s)
            if dataset == "Android":
                s = re.sub(":", ": ", s)
                s = re.sub("=", "= ", s)
            if dataset == "HPC":
                s = re.sub("=", "= ", s)
                s = re.sub("-", "- ", s)
                s = re.sub(":", ": ", s)
            if dataset == "BGL":
                s = re.sub("=", "= ", s)
                s = re.sub("\.\.", ".. ", s)
                s = re.sub("\(", "( ", s)
                s = re.sub("\)", ") ", s)
            if dataset == "Hadoop":
                s = re.sub("_", "_ ", s)
                s = re.sub(":", ": ", s)
                s = re.sub("=", "= ", s)
                s = re.sub("\(", "( ", s)
                s = re.sub("\)", ") ", s)
            if dataset == "HDFS":
                s = re.sub(":", ": ", s)
            if dataset == "Linux":
                s = re.sub("=", "= ", s)
                s = re.sub(":", ": ", s)
            if dataset == "Spark":
                s = re.sub(":", ": ", s)
            if dataset == "Thunderbird":
                s = re.sub(":", ": ", s)
                s = re.sub("=", "= ", s)
            if dataset == "Windows":
                s = re.sub(":", ": ", s)
                s = re.sub("=", "= ", s)
                s = re.sub("\[", "[ ", s)
                s = re.sub("]", "] ", s)
            if dataset == "Zookeeper":
                s = re.sub(":", ": ", s)
                s = re.sub("=", "= ", s)
            s = re.sub(",", ", ", s)
            s = re.sub(" +", " ", s).split(" ")
            s.insert(0, str(line_id))
            lenth = 0
            for token in s:
                set.setdefault(str(lenth), []).append(token)
                lenth += 1
            lena = len(s)
            group_len.setdefault(lena, []).append(
                s
            )  # first grouping: logs with the same length
            line_id += 1
        tuple_vector = {}
        frequency_vector = {}
        a = max(group_len.keys())  # a: the biggest length of the log in this dataset
        i = 0
        fre_set = {}  # saving each word's frequency
        while i < a:
            for word in set[str(i)]:  # counting each word's frequency
                word = str(i) + " " + word
                if word in fre_set.keys():  # check if the "word" in fre_set
                    fre_set[word] = fre_set[word] + 1  # frequency of "word" + 1
                else:
                    fre_set[word] = 1
            i += 1
        for (
            key
        ) in group_len.keys():  # using fre_set to generate frequency vector for the log
            for s in group_len[key]:  # in each log group with the same length
                position = 0
                fre = []
                fre_common = []
                skip_lineid = 1
                for word_character in s:
                    if skip_lineid == 1:
                        skip_lineid = 0
                        continue
                    frequency_word = fre_set[str(position + 1) + " " + word_character]
                    tuple = (
                        (frequency_word),
                        word_character,
                        position,
                    )  # tuple=(frequency,word_character, position)
                    fre.append(tuple)
                    fre_common.append((frequency_word))
                    position += 1
                tuple_vector.setdefault(key, []).append(fre)
                frequency_vector.setdefault(key, []).append(fre_common)
        return group_len, tuple_vector, frequency_vector


class tupletree:
    """
    tupletree(sorted_tuple_vector[key], word_combinations[key], word_combinations_reverse[key], tuple_vector[key], group_len[key])

    """

    def __init__(
        self,
        sorted_tuple_vector,
        word_combinations,
        word_combinations_reverse,
        tuple_vector,
        group_len,
    ):
        self.sorted_tuple_vector = sorted_tuple_vector
        self.word_combinations = word_combinations
        self.word_combinations_reverse = word_combinations_reverse
        self.tuple_vector = tuple_vector
        self.group_len = group_len

    def find_root(self, threshold_per):
        root_set_detail_ID = {}
        root_set_detail = {}
        root_set = {}
        i = 0
        for fc in self.word_combinations:
            count = self.group_len[i]
            threshold = (max(fc, key=lambda tup: tup[0])[0]) * threshold_per
            m = 0
            for fc_w in fc:
                if fc_w[0] >= threshold:
                    a = self.sorted_tuple_vector[i].append((int(count[0]), -1, -1))
                    root_set_detail_ID.setdefault(fc_w, []).append(
                        self.sorted_tuple_vector[i]
                    )
                    root_set.setdefault(fc_w, []).append(
                        self.word_combinations_reverse[i]
                    )
                    root_set_detail.setdefault(fc_w, []).append(self.tuple_vector[i])
                    break
                if fc_w[0] >= m:
                    candidate = fc_w
                    m = fc_w[0]
                if fc_w == fc[len(fc) - 1]:
                    a = self.sorted_tuple_vector[i].append((int(count[0]), -1, -1))
                    root_set_detail_ID.setdefault(candidate, []).append(
                        self.sorted_tuple_vector[i]
                    )
                    root_set.setdefault(candidate, []).append(
                        self.word_combinations_reverse[i]
                    )
                    root_set_detail.setdefault(fc_w, []).append(self.tuple_vector[i])
            i += 1
        return root_set_detail_ID, root_set, root_set_detail

    def up_split(self, root_set_detail, root_set):
        for key in root_set.keys():
            tree_node = root_set[key]
            father_count = []
            for node in tree_node:
                pos = node.index(key)
                for i in range(pos):
                    father_count.append(node[i])
            father_set = set(father_count)
            for father in father_set:
                if father_count.count(father) == key[0]:
                    continue
                else:
                    for i in range(len(root_set_detail[key])):
                        for k in range(len(root_set_detail[key][i])):
                            if father[0] == root_set_detail[key][i][k]:
                                root_set_detail[key][i][k] = (
                                    root_set_detail[key][i][k][0],
                                    "<*>",
                                    root_set_detail[key][i][k][2],
                                )
                    break
        return root_set_detail

    def down_split(self, root_set_detail_ID, threshold, root_set_detail):
        for key in root_set_detail_ID.keys():
            thre = threshold
            detail_order = root_set_detail[key]
            m = []
            child = {}
            variable = {""}
            variable.remove("")
            variable_set = {""}
            variable_set.remove("")
            m_count = 0
            fist_sentence = detail_order[0]
            for det in fist_sentence:
                if det[0] != key[0]:
                    m.append(m_count)
                m_count += 1
            for i in m:
                for node in detail_order:
                    if i < len(node):
                        child.setdefault(i, []).append(node[i][1])
            v_flag = 0
            for i in m:
                next = {""}
                next.remove("")
                result = set(child[i])
                freq = len(result)
                if freq >= thre:
                    variable = variable.union(result)
                v_flag += 1
            i = 0
            while i < len(root_set_detail_ID[key]):
                j = 0
                while j < len(root_set_detail_ID[key][i]):
                    if isinstance(root_set_detail_ID[key][i][j], tuple):
                        if root_set_detail_ID[key][i][j][1] in variable:
                            root_set_detail_ID[key][i][j] = (
                                root_set_detail_ID[key][i][j][0],
                                "<*>",
                                root_set_detail_ID[key][i][j][2],
                            )
                    j += 1
                i += 1
        return root_set_detail_ID


def output_result(parse_result):
    template_set = {}
    for key in parse_result.keys():
        for pr in parse_result[key]:
            sort = sorted(pr, key=lambda tup: tup[2])
            i = 1
            template = []
            while i < len(sort):
                this = sort[i][1]
                if bool("<*>" in this):
                    template.append("<*>")
                    i += 1
                    continue
                if exclude_digits(this):
                    template.append("<*>")
                    i += 1
                    continue
                template.append(sort[i][1])
                i += 1
            template = tuple(template)
            template_set.setdefault(template, []).append(pr[len(pr) - 1][0])
    return template_set


def save_result(dataset, df_output, template_set):
    df_output.to_csv("Parseresult/" + dataset + "result.csv", index=False)
    with open("Parseresult/" + dataset + "_template.csv", "w") as f:
        for k1 in template_set.keys():
            f.write(" ".join(list(k1)))
            f.write("  " + str(len(template_set[k1])))
            f.write("\n")
        f.close()

#用来检查一个字符串中的数字占比是否大于或等于 30%。
def exclude_digits(string):
    """
    exclude the digits-domain words from partial constant
    """
    pattern = r"\d"
    digits = re.findall(pattern, string)
    if len(digits) == 0:
        return False
    return len(digits) / len(string) >= 0.3


