# -*- coding: utf-8 -*-
from collections import defaultdict
from pathlib import Path
import re
import os

OUT_FILE = "query_out.log"
QUERY_LOG_FILE = "query.log_parse_split"

def parse_query(query):

    qdic = defaultdict(list)
    query_split = [param.split('=') for param in query.split('&')]
    for param in query_split:
        qdic[param[0]].append(param[1])

    return qdic

def queryParamBuilder(qdic):
    #import pdb; pdb.set_trace()

    NGRAM_FIELDS = {'kp_tri':'0',
                    'productname_tri':'1'}
    OTHER_FIELDS = {'lower_categoryname_sen':'100000000',
                    'category_pankuzu_sen':'1000000',
                    'seriesname_sen':'200000',
                    'makername_sen':'100000',
                    'productname_sen':'100',
                    'jan':'10'}

    NGRAM_PATTERN = re.compile('[a-z0-9]+_tri:')
    MORPHE_PATTERN = re.compile('[a-z0-9]+_sen:')

    q_param = str(qdic.get('q'))
    if not q_param:
        return {}

    splited_query = _split_with_parentheses(q_param)
    ngram_query = extract_query_word(splited_query, NGRAM_PATTERN)
    morphe_query = extract_query_word(splited_query, MORPHE_PATTERN)

    ngram_list = []
    for field, boost in NGRAM_FIELDS.items():
        ngram_list.append('{0}:{1}^{2}'.format(field, ngram_query, boost))

    normal_list = []
    for field, boost in OTHER_FIELDS.items():
        normal_list.append('{0}:{1}^{2}'.format(field, morphe_query, boost))


    # ngramクエリとngram以外のクエリを結合
    ngram_list.extend(normal_list)

    # qdicのqパラメータ更新
    qdic['q'] = ['+OR+'.join(ngram_list)]
    #return '+OR+'.join(ngram_list)

    return qdic


def qdic_to_query(qdic):
    query = ""
    for param, values in qdic.items():
        # 同一パラメータが複数ある場合はここでバラす
        if len(values) > 1:
            for v in values:
                query += '{0}={1}&'.format(param, v)
        else:
            query += '{0}={1}&'.format(param, ','.join(values))

    return query.rstrip('&')

def extract_query_word(splited_query, pattern):
    #pattern = re.compile('[a-z0-9]+_tri:')
    depth = 0
    key = ''
    query = ''
    for w in splited_query:
        match = pattern.search(w)
        if match:
            key = match.group()
        elif key:
            if w == u'(':
                depth += 1
                query += w
            elif w == u')':
                depth -= 1
                query += w
                if depth == 0:
                     return query
            else:
                query += w

def _split_with_parentheses(query):
    SEP = u'\t'
    query = query.replace(u'(', SEP + u'(' + SEP)
    query = query.replace(u')', SEP + u')' + SEP)
    return [ c for c in query.split(SEP) if c ]

def remove_param(qdic, param):
    del_p = qdic.get(param)
    if not del_p:
        return qdic
    del qdic[param]
    return qdic


def rename_field(qdic, param, name_before, name_after):
    rep_p = qdic.get(param)
    rep_query = []
    if not rep_p:
        return qdic
    for p in rep_p:
        rep_query.append(p.replace(name_before, name_after))
    qdic[param] = rep_query
    return qdic


if __name__ == '__main__':

    if Path(OUT_FILE).exists():
        os.remove(OUT_FILE)
    fh_out = open(OUT_FILE, 'a')

    fh = open(QUERY_LOG_FILE, "r", encoding="UTF-8")
    for line in fh:
        # boost_qが含まれなければ置換対象外のためそのまま出力
        if line.find('boost_q') == -1:
            fh_out.write(line)
            continue
        #print(parse_query(line))
        # パラメータ:valueの辞書形式に変換
        qdic = parse_query(line)
        # 不要パラメータ削除
        qdic = remove_param(qdic, 'boost_q')
        qdic = remove_param(qdic, 'boost_score')
        # sortパラメータの置換
        qdic = rename_field(qdic, 'sort', '$boost_score', 'score')
        # flパラメータの置換
        qdic = rename_field(qdic, 'fl', '$boost_score', 'score')
        # q=パラメータの置換
        qdic = queryParamBuilder(qdic)
        fh_out.write(qdic_to_query(qdic) + '\n')
