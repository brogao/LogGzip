import pandas as pd
import numpy as np
from tqdm import tqdm
from scipy.special import comb
from sklearn.metrics import accuracy_score
import regex as re
import sys


def post_process_tokens(tokens, punc):
    excluded_str = ['=', '|', '(', ')']
    for i in range(len(tokens)):
        if tokens[i].find("<*>") != -1:
            tokens[i] = "<*>"
        else:
            new_str = ""
            for s in tokens[i]:
                if (s not in punc and s != ' ') or s in excluded_str:
                    new_str += s
            tokens[i] = new_str
    return tokens

def message_split(message):
    punc = "!\"#$%&'()+,-/:;=?@.[\]^_`{|}~"
    splitters = "\s\\" + "\\".join(punc)
    splitter_regex = re.compile("([{}]+)".format(splitters))
    tokens = re.split(splitter_regex, message)
    tokens = list(filter(lambda x: x != "", tokens))
    tokens = post_process_tokens(tokens, punc)
    tokens = [token.strip() for token in tokens if token != "" and token != ' ']
    tokens = [token for idx, token in enumerate(tokens) if not (token == "<*>" and idx > 0 and tokens[idx - 1] == "<*>")]
    return tokens

def calculate_similarity(template1, template2):
    template1 = message_split(template1)
    template2 = message_split(template2)
    intersection = len(set(template1).intersection(set(template2)))
    union = (len(template1) + len(template2)) - intersection
    return intersection / union

def evaluate_template_level(dataset, df_groundtruth, df_parsedresult, filter_templates=None):
    correct_parsing_templates = 0
    if filter_templates is not None:
        filter_identify_templates = set()
    null_logids = df_groundtruth[~df_groundtruth['EventTemplate'].isnull()].index
    df_groundtruth = df_groundtruth.loc[null_logids]
    df_parsedresult = df_parsedresult.loc[null_logids]
    series_groundtruth = df_groundtruth['EventTemplate']
    series_parsedlog = df_parsedresult['EventTemplate']
    series_groundtruth_valuecounts = series_groundtruth.value_counts()

    df_combined = pd.concat([series_groundtruth, series_parsedlog], axis=1, keys=['groundtruth', 'parsedlog'])
    grouped_df = df_combined.groupby('parsedlog')

    for identified_template, group in tqdm(grouped_df):
        corr_oracle_templates = set(list(group['groundtruth']))
        if filter_templates is not None and len(corr_oracle_templates.intersection(set(filter_templates))) > 0:
            filter_identify_templates.add(identified_template)

        if corr_oracle_templates == {identified_template}:
            if (filter_templates is None) or (identified_template in filter_templates):
                correct_parsing_templates += 1

    if filter_templates is not None:
        PTA = correct_parsing_templates / len(filter_identify_templates)
        RTA = correct_parsing_templates / len(filter_templates)
    else:
        PTA = correct_parsing_templates / len(grouped_df)
        RTA = correct_parsing_templates / len(series_groundtruth_valuecounts)
    FTA = 0.0
    if PTA != 0 or RTA != 0:
        FTA = 2 * (PTA * RTA) / (PTA + RTA)
    print('PTA: {:.4f}, RTA: {:.4f} FTA: {:.4f}'.format(PTA, RTA, FTA))
    t1 = len(grouped_df) if filter_templates is None else len(filter_identify_templates)
    t2 = len(series_groundtruth_valuecounts) if filter_templates is None else len(filter_templates)
    print("Identify : {}, Groundtruth : {}".format(t1, t2))
    return t1, t2, FTA, PTA, RTA

def correct_lstm(groundtruth, parsedresult):
    tokens1 = groundtruth.split(' ')
    tokens2 = parsedresult.split(' ')
    tokens1 = ["<*>" if "<*>" in token else token for token in tokens1]
    return tokens1 == tokens2

def calculate_parsing_accuracy(groundtruth_df, parsedresult_df, filter_templates=None):
    if filter_templates is not None:
        groundtruth_df = groundtruth_df[groundtruth_df['EventTemplate'].isin(filter_templates)]
        parsedresult_df = parsedresult_df.loc[groundtruth_df.index]
    correctly_parsed_messages = parsedresult_df[['EventTemplate']].eq(groundtruth_df[['EventTemplate']]).values.sum()
    total_messages = len(parsedresult_df[['Content']])
    PA = float(correctly_parsed_messages) / total_messages
    print('Parsing_Accuracy (PA): {:.4f}'.format(PA))
    return PA

def calculate_parsing_accuracy_lstm(groundtruth_df, parsedresult_df, filter_templates=None):

    # parsedresult_df = pd.read_csv(parsedresult)
    # groundtruth_df = pd.read_csv(groundtruth)
    if filter_templates is not None:
        groundtruth_df = groundtruth_df[groundtruth_df['EventTemplate'].isin(filter_templates)]
        parsedresult_df = parsedresult_df.loc[groundtruth_df.index]
    # correctly_parsed_messages = parsedresult_df[['EventTemplate']].eq(groundtruth_df[['EventTemplate']]).values.sum()
    groundtruth_templates = list(groundtruth_df['EventTemplate'])
    parsedresult_templates = list(parsedresult_df['EventTemplate'])
    correctly_parsed_messages = 0
    for i in range(len(groundtruth_templates)):
        if correct_lstm(groundtruth_templates[i], parsedresult_templates[i]):
            correctly_parsed_messages += 1

    PA = float(correctly_parsed_messages) / len(groundtruth_templates)

    # similarities = []
    # for index in range(len(groundtruth_df)):
    #     similarities.append(calculate_similarity(groundtruth_df['EventTemplate'][index], parsedresult_df['EventTemplate'][index]))
    # SA = sum(similarities) / len(similarities)
    # print('Parsing_Accuracy (PA): {:.4f}, Similarity_Accuracy (SA): {:.4f}'.format(PA, SA))
    print('Parsing_Accuracy (PA): {:.4f}'.format(PA))
    return PA

def evaluate(groundtruth, parsedresult):
    df_groundtruth = pd.read_csv(groundtruth)
    df_parsedlog = pd.read_csv(parsedresult)
    # Remove invalid groundtruth event Ids
    non_empty_log_ids = df_groundtruth[~df_groundtruth["EventTemplate"].isnull()].index
    df_groundtruth = df_groundtruth.loc[non_empty_log_ids]
    df_parsedlog = df_parsedlog.loc[non_empty_log_ids]

    GA, FGA = get_accuracy(df_groundtruth["EventTemplate"], df_parsedlog["EventTemplate"])

    accuracy_exact_string_matching = accuracy_score(
        np.array(df_groundtruth.EventTemplate.values, dtype='str'),
        np.array(df_parsedlog.EventTemplate.values, dtype='str')
    )
    # PA = calculate_parsing_accuracy_lstm(df_groundtruth, df_parsedlog)


    _, _, FTA, PTA, RTA = evaluate_template_level(None, df_groundtruth, df_parsedlog)

    # 打印所有的评估指标
    print(
        "Grouping_Accuracy (GA): {:.4f},  FGA: {:.4f}, PTA: {:.4f}, RTA: {:.4f}, FTA: {:.4f}".format(
            GA, FGA, PTA, RTA, FTA
        )
    )
    return GA, FGA, FTA, PTA, RTA

def get_accuracy(series_groundtruth, series_parsedlog, filter_templates=None):
    series_groundtruth_valuecounts = series_groundtruth.value_counts()
    series_parsedlog_valuecounts = series_parsedlog.value_counts()
    df_combined = pd.concat([series_groundtruth, series_parsedlog], axis=1, keys=['groundtruth', 'parsedlog'])
    grouped_df = df_combined.groupby('groundtruth')
    accurate_events = 0 # determine how many lines are correctly parsed
    accurate_templates = 0
    if filter_templates is not None:
        filter_identify_templates = set()
    for ground_truthId, group in tqdm(grouped_df):
        series_parsedlog_logId_valuecounts = group['parsedlog'].value_counts()
        if filter_templates is not None and ground_truthId in filter_templates:
            for parsed_eventId in series_parsedlog_logId_valuecounts.index:
                filter_identify_templates.add(parsed_eventId)
        if series_parsedlog_logId_valuecounts.size == 1:
            parsed_eventId = series_parsedlog_logId_valuecounts.index[0]
            if len(group) == series_parsedlog[series_parsedlog == parsed_eventId].size:
                if (filter_templates is None) or (ground_truthId in filter_templates):
                    accurate_events += len(group)
                    accurate_templates += 1
    if filter_templates is not None:
        GA = float(accurate_events) / len(series_groundtruth[series_groundtruth.isin(filter_templates)])
        PGA = float(accurate_templates) / len(filter_identify_templates)
        RGA = float(accurate_templates) / len(filter_templates)
    else:
        GA = float(accurate_events) / len(series_groundtruth)
        PGA = float(accurate_templates) / len(series_parsedlog_valuecounts)
        RGA = float(accurate_templates) / len(series_groundtruth_valuecounts)
    FGA = 0.0
    if PGA != 0 or RGA != 0:
        FGA = 2 * (PGA * RGA) / (PGA + RGA)
    return GA, FGA

