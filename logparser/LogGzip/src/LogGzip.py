#LogGzip.py
from logparser.LogGzip.src.LogGzip_template import LenmaTemplateManager
import pandas as pd
import regex as re
import os
import hashlib
from collections import defaultdict
from datetime import datetime
from logparser.LogGzip.compressors import DefaultCompressor



class LogParser(object):
    def __init__(
        self,
        indir,
        outdir,
        log_format,
        compressor_instance=None,
        threshold=0.9,
        predefined_templates=None,
        rex=[],
        mask_digits=False,
        delimiters=None,
    ):
        self.path = indir
        self.savePath = outdir
        self.logformat = log_format
        self.rex = rex
        self.wordseqs = []
        self.df_log = pd.DataFrame()
        self.wordpos_count = defaultdict(int)
        self.mask_digits = mask_digits
        self.logname = None
        self.compressor = compressor_instance
        self.delimiters = delimiters or [r'\s+']
        print(f"Received compressor_instance: {compressor_instance}")
        assert compressor_instance is not None, "Compressor instance is None inside LogParser __init__"

        self.templ_mgr = LenmaTemplateManager(
            threshold=threshold,
            predefined_templates=predefined_templates,
            compressor_instance=self.compressor,
        )

    def parse(self, logname):
        print("Parsing file: " + os.path.join(self.path, logname))
        self.logname = logname
        starttime = datetime.now()
        headers, regex = self.generate_logformat_regex(self.logformat)
        self.df_log = self.log_to_dataframe(
            os.path.join(self.path, self.logname), regex, headers, self.logformat
        )
        is_apache = "Apache" in logname
        digit_rex = re.compile(r'(?<!\d)\d{2,}(?!\d)|(?<!\d)\d(?!\d)')
        for idx, line in self.df_log.iterrows():
            line = line["Content"]
            line = self.preprocess(line)
            if self.mask_digits:
                line = re.sub(r'(\S+):(\S+)', '<*>:<*>', line)
                line = re.sub(r'\b\d+\b', '<*>', line)
                line = re.sub(r'\(<\*> <\*>\)', '', line)
            else:
                line = re.sub(r'(\b\d+:\d+\b)', '<*>', line)
                if not is_apache:
                    line = digit_rex.sub('<*>', line)
                line = re.sub(r'(?<=\s|\])([^\s]*\*){3,}[^\s*]*(?=\s\]|\s[^]]|$)', '<*>', line)

            words = self.tokenize(line, delimiters=self.delimiters)
            self.templ_mgr.infer_template(words, idx, self.mask_digits)
        self.dump_results()
        print("Parsing done. [Time taken: {!s}]".format(datetime.now() - starttime))

    def tokenize(self, line, delimiters):

        token_delimiters = '|'.join(delimiters)
        tokens = re.split('(' + token_delimiters + ')', line)

        tokens = [token for token in tokens if token.strip()]
        return tokens

    def dump_results(self):
        if not os.path.isdir(self.savePath):
            os.makedirs(self.savePath)

        event_dict = {}
        templates = [0] * self.df_log.shape[0]
        template_ids = [0] * self.df_log.shape[0]

        for t in self.templ_mgr.templates:
            template = " ".join(t.words)
            template = update_template(template)
            eventid = hashlib.md5(template.encode("utf-8")).hexdigest()[0:8]
            logids = t.get_logids()

            if template in event_dict:
                event_dict[template]["Occurrences"] += len(logids)
                event_id = event_dict[template]["EventId"]
            else:
                event_dict[template] = {"EventId": eventid, "Occurrences": len(logids)}
                event_id = eventid

            for logid in logids:
                templates[logid] = template
                template_ids[logid] = event_id

        df_event = [
            [info["EventId"], tpl, info["Occurrences"]]
            for tpl, info in event_dict.items()
        ]

        self.df_log["EventId"] = template_ids
        self.df_log["EventTemplate"] = templates

        pd.DataFrame(
            df_event, columns=["EventId", "EventTemplate", "Occurrences"]
        ).to_csv(
            os.path.join(self.savePath, self.logname + "_templates.csv"), index=False
        )
        self.df_log.to_csv(
            os.path.join(self.savePath, self.logname + "_structured.csv"), index=False
        )

    def preprocess(self, line):
        for currentRex in self.rex:
            line = re.sub(currentRex, "<*>", line)
        return line

    def log_to_dataframe(self, log_file, regex, headers, logformat):
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
                    print("Skip line: " + line)
        logdf = pd.DataFrame(log_messages, columns=headers)
        logdf.insert(0, "LineId", None)
        logdf["LineId"] = [i + 1 for i in range(linecount)]
        return logdf

    def generate_logformat_regex(self, logformat):
        headers = []
        splitters = re.split(r"(<[^<>]+>)", logformat)
        regex = ""
        for k in range(len(splitters)):
            if k % 2 == 0:
                splitter = re.sub(" +", "\\\\s+", splitters[k])
                regex += splitter
            else:
                header = splitters[k].strip("<").strip(">")
                regex += "(?P<%s>.*?)" % header
                headers.append(header)
        regex = re.compile("^" + regex + "$")
        return headers, regex
def update_template(template, user_strings=None):
    path_delimiters = {
        r'\s', r'\,', r'\!', r'\;', r'\:',
        r'\=', r'\|', r'\"', r'\'',
        r'\[', r'\]', r'\(', r'\)', r'\{', r'\}'
    }
    token_delimiters = path_delimiters.union({  r'\.', r'\-', r'\+', r'\@', r'\#', r'\$', r'\%', r'\&', })
    template = template.strip()
    template = re.sub(r'\s+', ' ', template)
    tokens = re.split('(' + '|'.join(token_delimiters) + ')', template)  # tokenizing while keeping delimiters
    new_tokens = []
    for token in tokens:
        if re.match(r'^[^\s\/]*<\*>[^\s\/]*$', token):
            if token != '<*>/<*>':
                token = '<*>'

        new_tokens.append(token)

    template = ''.join(new_tokens)

    while True:
        prev = template
        template = re.sub(r'<\*>\.<\*>', '<*>', template)
        if prev == template:
            break
    return template
