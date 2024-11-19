#LogGzip_template.py：
import json
import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.metrics.pairwise import cosine_similarity
from logparser.LogGzip.src import template
from importlib import import_module
import re
import pickle
import os
import hashlib


def NCD(c1: float, c2: float, c12: float) -> float:
    distance = max((c12 - c1) / c2 , (c12 - c2) / c1)
    return distance
def agg_by_concat_space(t1: str, t2: str) -> str:
    return t1 + " " + t2


class LenmaTemplate(template.Template):
    def __init__(self, index=None, words=None, logid=None, json=None, compressor=None, mask_digits=False):  # Corrected parameter name
        if json is not None:
            # restore from the jsonized data.
            self._restore_from_json(json)
        else:
            # initialize with the specified index and words values.
            assert(index is not None)
            assert(words is not None)
            self._index = index
            self._words = words
            self._nwords = len(words)
            self._wordlens = [len(w) for w in words]
            self._counts = 1
            self._logid = [logid]
            self.compressor = compressor
            self.mask_digits = mask_digits
            assert self.compressor is not None, "Compressor instance is None in LenmaTemplate"

    @property
    def wordlens(self):
        return self._wordlens

    def _dump_as_json(self):
        description = str(self)
        return json.dumps([self.index, self.words, self.nwords, self.wordlens, self.counts])

    def _restore_from_json(self, data):
        (self._index,
         self._words,
         self._nwords,
         self._wordlens,
         self._counts) = json.loads(data)

    def _try_update(self, new_words):
        try_update = [self.words[idx] if self._words[idx] == new_words[idx]
                      else '' for idx in range(self.nwords)]
        if (self.nwords - try_update.count('')) < 3:
            return False
        return True

    def _get_accuracy_score(self, new_words):

        fill_wildcard = [self.words[idx] if self.words[idx] != ''
                         else new_words[idx] for idx in range(self.nwords)]
        ac_score = accuracy_score(fill_wildcard, new_words)
        return ac_score

    def _get_wcr(self):
        return self.words.count('') / self.nwords

    def _get_accuracy_score2(self, new_words):
        wildcard_ratio = self._get_wcr()
        ac_score = accuracy_score(self.words, new_words)
        return (ac_score / (1 - wildcard_ratio), wildcard_ratio)


    def _count_same_word_positions(self, new_words):
        c = 0
        for idx in range(self.nwords):
            if self.words[idx] == new_words[idx]:
                c = c + 1
        return c

    def get_compression_distance(self, new_words):
        compressed_template = self.compressor.get_compressed_len(" ".join(self._words))
        compressed_new_words = self.compressor.get_compressed_len(" ".join(new_words))
        combined_text = agg_by_concat_space(" ".join(self._words), " ".join(new_words))
        compressed_combined = self.compressor.get_compressed_len(combined_text)

        distance = NCD(compressed_template, compressed_new_words, compressed_combined)
        return 1 - distance

    def get_similarity_score(self, new_words):
        if self._words[0] != new_words[0]:
            return 0

        ac_score = self._get_accuracy_score(new_words)
        if ac_score == 1:
            return 1

        comp_distance = self.get_compression_distance(new_words)
        return comp_distance

    def update(self, new_words, logid):
        if self.mask_digits:
            digit_regex = re.compile(r'\b\d+\b|\b\w*\d+\w*\b')
            new_words = [digit_regex.sub('<*>', word) for word in new_words]
        self._counts += 1
        self._wordlens = [len(w) for w in new_words]
        self._words = [self.words[idx] if self._words[idx] == new_words[idx]
                       else '<*>' for idx in range(self.nwords)]
        self._logid.append(logid)

    def print_wordlens(self):
        print('{index}({nwords})({counts}):{vectors}'.format(
            index=self.index,
            nwords=self.nwords,
            counts=self._counts,
            vectors=self._wordlens))

    def get_logids(self):
        return self._logid


class LenmaTemplateManager(template.TemplateManager):
    def __init__(self, threshold=0.9, predefined_templates=None, compressor_module=None, compressor_instance=None):
        super().__init__()
        self._threshold = threshold
        self.compressor_instance = compressor_instance
        self.compression_dict = {}

        # 确保compressor_instance在传递之前不是None
        assert compressor_instance is not None, "Compressor instance is None before passing to LenmaTemplateManager"

    def infer_template(self, words, logid, mask_digits=False):
        nwords = len(words)
        template_key = hashlib.md5(" ".join(words).encode("utf-8")).hexdigest()

        if template_key in self.compression_dict:
            existing_template = self.compression_dict[template_key]


            if not isinstance(existing_template, LenmaTemplate):
                print(f"Error: Expected LenmaTemplate, but got {type(existing_template)}")
                return None

            existing_template.update(words, logid)
            return existing_template

        candidates = []
        for (index, template) in enumerate(self.templates):
            if nwords != template.nwords:
                continue
            score = template.get_similarity_score(words)
            if score < self._threshold:
                continue
            candidates.append((index, score))
        candidates.sort(key=lambda c: c[1], reverse=True)

        if len(candidates) > 0:
            index = candidates[0][0]
            self.templates[index].update(words, logid)
            self.compression_dict[template_key] = self.templates[index]
            return self.templates[index]

        new_template = self._append_template(
            LenmaTemplate(index=len(self.templates), words=words, logid=logid, compressor=self.compressor_instance,
                          mask_digits=mask_digits)
        )
        self.compression_dict[template_key] = new_template
        return new_template

    def dump_template(self, index):
        return self.templates[index]._dump_as_json()

    def restore_template(self, data):
        return LenmaTemplate(json=data)

