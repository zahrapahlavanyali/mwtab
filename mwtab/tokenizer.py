#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mwtab.tokenizer
~~~~~~~~~~~~~~~

This module provides the :func:`~mwtab.tokenizer.tokenizer` lexical analyzer for
`mwTab` format syntax. It is implemented as Python generator-based state
machine which generates (yields) tokens one at a time when :py:func:`next()`
is invoked on :func:`~mwtab.tokenizer.tokenizer` instance.

Each token is a tuple of "key-value"-like pairs, tuple of
``SUBJECT_SAMPLE_FACTORS`` or tuple of data deposited between
``*_START`` and ``*_END`` blocks.
"""

from __future__ import print_function, division, unicode_literals
from collections import deque, namedtuple


KeyValue = namedtuple("KeyValue", ["key", "value"])
SubjectSampleFactors = namedtuple("SubjectSampleFactors", ["key", "subject_type", "local_sample_id", "factors", "additional_sample_data"])
KeyValueExtra = namedtuple("KeyValueExtra", ["key", "value", "extra"])


def tokenizer(text):
    """A lexical analyzer for the `mwtab` formatted files.

    :param str text: `mwtab` formatted text.
    :return: Tuples of data.
    :rtype: py:class:`~collections.namedtuple`
    """

    stream = deque(text.split("\n"))

    while len(stream) > 0:
        line = stream.popleft()

        # header
        if line.startswith("#METABOLOMICS WORKBENCH"):
            yield KeyValue("#METABOLOMICS WORKBENCH", "\n")

            try:
                for identifier in line.split(" "):
                    if ":" in identifier:
                        key, value = identifier.split(":")
                        yield KeyValue(key, value)
            except ValueError as e:
                raise ValueError("LINE WITH ERROR:\n\t", repr(line), e)

        # SUBJECT_SAMPLE_FACTORS header (reached new section)
        elif line.startswith("#SUBJECT_SAMPLE_FACTORS:"):
            yield KeyValue("#ENDSECTION", "\n")
            yield KeyValue("#SUBJECT_SAMPLE_FACTORS", "\n")

        # section header (reached new section)
        elif line.startswith("#"):
            yield KeyValue("#ENDSECTION", "\n")
            yield KeyValue(line.strip(), "\n")

        # SUBJECT_SAMPLE_FACTORS line
        elif line.startswith("SUBJECT_SAMPLE_FACTORS"):
            try:
                key, subject_type, local_sample_id, factors, additional_sample_data = line.split("\t")
                factors = {factor_item.split(":")[0].strip(): factor_item.split(":")[1].strip() for factor_item in factors.split("|")}
                additional_sample_dict = dict()
                for item in additional_sample_data.split(";"):
                    if "=" in item:
                        k, v = item.split("=")
                        additional_sample_dict[k.strip()] = v.strip()
                yield SubjectSampleFactors(key.strip(), subject_type, local_sample_id, factors, additional_sample_dict)
            except ValueError as e:
                raise ValueError("LINE WITH ERROR:\n\t", repr(line), e)

        # data start header
        elif line.endswith("_START"):
            yield KeyValue(line, "\n")

            # tokenize lines in data section till line ending with "_END" is reached
            while not line.endswith("_END"):
                line = stream.popleft()
                if line.endswith("_END"):
                    yield KeyValue(line.strip(), "\n")
                else:
                    data = line.split("\t")
                    yield KeyValue(data[0], tuple(data))

        # item line in item section (e.g. PROJECT, SUBJECT, etc..)
        else:
            if line:
                if "_RESULTS_FILE" in line:
                    line_items = line.split("\t")
                    if len(line_items) > 2:
                        extra_items = [tuple(extra_item.split(":")) for extra_item in line_items[2:] if ":" in extra_item]
                        yield KeyValueExtra(line_items[0].strip()[3:], line_items[1], extra_items)
                    else:
                        yield KeyValue(line_items[0].strip()[3:], line_items[1])
                else:
                    try:
                        key, value = line.split("\t")
                        if ":" in key:
                            if key.endswith("_METABOLITE_DATA:UNITS"):
                                yield KeyValue("Units", value)
                            else:
                                yield KeyValue(key.strip()[3:], value)
                        else:
                            yield KeyValue(key.strip(), value)
                    except ValueError as e:
                        raise ValueError("LINE WITH ERROR:\n\t", repr(line), e)

    # end of file
    yield KeyValue("#ENDSECTION", "\n")
    yield KeyValue("!#ENDFILE", "\n")  # This is to ensure that tokenizer terminates when #END is missing.
