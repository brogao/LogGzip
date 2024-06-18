import pandas as pd
import os
import regex as re
import sys
sys.path.append("../")
# 定义修改模板的正则表达式
param_regex = [
    r'{([ :_#.\-\w\d]+)}',
    r'{}'
]

def correct_single_template(template, user_strings=None):

    # boolean = {}
    # default_strings = {}
    path_delimiters = {  # reduced set of delimiters for tokenizing for checking the path-like strings
        r'\s', r'\,', r'\!', r'\;', r'\:',
        r'\=', r'\|', r'\"', r'\'',
        r'\[', r'\]', r'\(', r'\)', r'\{', r'\}'
    }
    token_delimiters = path_delimiters.union({  # all delimiters for tokenizing the remaining rules
        r'\.', r'\-', r'\+', r'\@', r'\#', r'\$', r'\%', r'\&',
    })

    # if user_strings:
        # default_strings = default_strings.union(user_strings)

    # apply DS
    template = template.strip()
    template = re.sub(r'\s+', ' ', template)

    # tokenize for the remaining rules
    tokens = re.split('(' + '|'.join(token_delimiters) + ')', template)  # tokenizing while keeping delimiters
    new_tokens = []
    for token in tokens:
        # apply DG
        if re.match(r'^\d+$', token):
            token = '<*>'

        # apply WV
        if re.match(r'^[^\s\/]*<\*>[^\s\/]*$', token):
            if token != '<*>/<*>':  # need to check this because `/` is not a deliminator
                token = '<*>'

        # collect the result
        new_tokens.append(token)

    # make the template using new_tokens
    template = ''.join(new_tokens)

    # Substitute consecutive variables only if separated with any delimiter including "." (DV)
    while True:
        prev = template
        template = re.sub(r'<\*>\.<\*>', '<*>', template)
        if prev == template:
            break
    while True:
        prev = template
        template = re.sub(r'<\*><\*>', '<*>', template)
        if prev == template:
            break
    #print("CV: ", template)

    while " #<*># " in template:
        template = template.replace(" #<*># ", " <*> ")

    while " #<*> " in template:
        template = template.replace(" #<*> ", " <*> ")

    while "<*>:<*>" in template:
        template = template.replace("<*>:<*>", "<*>")

    while "<*>#<*>" in template:
        template = template.replace("<*>#<*>", "<*>")

    while "<*>/<*>" in template:
        template = template.replace("<*>/<*>", "<*>")

    while "<*>@<*>" in template:
        template = template.replace("<*>@<*>", "<*>")

    while "<*>.<*>" in template:
        template = template.replace("<*>.<*>", "<*>")

    while ' "<*>" ' in template:
        template = template.replace(' "<*>" ', ' <*> ')

    while " '<*>' " in template:
        template = template.replace(" '<*>' ", " <*> ")

    while "<*><*>" in template:
        template = template.replace("<*><*>", "<*>")
    return template

def modify_template(template_df):
    # 对模板文件中的每个模板进行修改
    template_df['EventTemplate'] = template_df['EventTemplate'].apply(correct_single_template)
    return template_df


# 数据集名称列表
dataset_names = ["Proxifier", "Linux", "Apache", "Zookeeper", "Mac", "OpenStack",
                 "HealthApp", "Hadoop", "HPC", "OpenSSH", "Android", "BGL",
                 "HDFS", "Spark", "Windows", "Thunderbird"]
# 获取当前脚本文件的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 基于脚本所在目录构建数据目录的路径
datasets_dir = os.path.join(script_dir, 'LogGzip', 'LogGzip_result')

# 遍历datasets_dir目录下的所有文件
for filename in os.listdir(datasets_dir):
    # 检查文件名是否符合特定格式：某个数据集名称后跟"_2k.log_structured.csv"
    if any(filename == f"{name}_2k.log_structured.csv" for name in dataset_names):
        # 构建完整的文件路径
        template_file = os.path.join(datasets_dir, filename)

        # 读取CSV文件
        template_df = pd.read_csv(template_file)

        # 修改模板
        modified_template_df = modify_template(template_df)

        # 构建输出文件的完整路径，这里简单地在原文件名后加上"_modified"
        output_file = os.path.join(datasets_dir, f"{os.path.splitext(filename)[0]}_modified.csv")

        modified_template_df.to_csv(output_file, index=False)