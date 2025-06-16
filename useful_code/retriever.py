# -*- coding: utf-8 -*-
# File: retrieve.py 

"""
该文件是调用其他向量化模型的代码，包括TF-IDF, BGE, GTE, BCE, M3, 可以无缝替换现有的召回模型，对于其他的模型，也同理。
"""

import os
import jieba
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.retrievers import BM25Retriever, TFIDFRetriever
from loader import ReadFiles
import torch


class BM25(object):
    # 遍历文档，首先做分词，然后把分词后的文档和全文文档建立索引和映射关系
    def __init__(self, documents):
        docs = []
        full_docs = []
        for idx, line in enumerate(documents):
            line = line.strip("\n").strip()
            if len(line) < 5:
                continue
            tokens = " ".join(jieba.cut_for_search(line))
            docs.append(Document(page_content=tokens, metadata={"id": idx}))
            words = line.split("\t")
            full_docs.append(Document(page_content=words[0], metadata={"id": idx}))

        self.documents = docs
        self.full_documents = full_docs
        self.retriever = self._init_bm25()

    def _init_bm25(self):
        # 初始化BM25的知识库
        return BM25Retriever.from_documents(self.documents)

    def GetBM25TopK(self, query, topk):
        # 获得得分在topk的文档和分数
        self.retriever.k = topk
        query = " ".join(jieba.cut_for_search(query))
        ans_docs = self.retriever.get_relevant_documents(query)
        ans = []
        for line in ans_docs:
            ans.append(self.full_documents[line.metadata["id"]])
        return ans


class TFIDF(object):

    def __init__(self, documents):
        docs = []
        full_docs = []
        for idx, line in enumerate(documents):
            line = line.strip("\n").strip()
            if len(line) < 5:
                continue
            tokens = " ".join(jieba.cut_for_search(line))
            docs.append(Document(page_content=tokens, metadata={"id": idx}))
            words = line.split("\t")
            full_docs.append(Document(page_content=words[0], metadata={"id": idx}))

        self.documents = docs
        self.full_documents = full_docs
        self.retriever = self._init_tfidf()

    def _init_tfidf(self):
        # 初始化TFIDF的知识库
        return TFIDFRetriever.from_documents(self.documents)

    def GetTFIDFTopK(self, query, topk):
        # 获得得分在topk的文档和分数
        self.retriever.k = topk
        query = " ".join(jieba.cut_for_search(query))
        ans_docs = self.retriever.get_relevant_documents(query)
        ans = []
        for line in ans_docs:
            ans.append(self.full_documents[line.metadata["id"]])
        return ans


class FaissRetriever(object):
    # 基于 langchain 中的 faiss 库的
    def __init__(self, model_path, data):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_path,
            model_kwargs={"device": "cuda"},
        )
        docs = []
        for idx, line in enumerate(data):
            line = line.strip("\n").strip()
            words = line.split("\t")
            docs.append(Document(page_content=words[0], metadata={"id": idx}))
        save_path = "./index/" + model_path.split("/")[-1] 
        if os.path.exists(save_path):
            # 如果之前已经有向量化的结果，直接用
            self.vector_store = FAISS.load_local(save_path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            self.vector_store = FAISS.from_documents(docs, self.embeddings)
            # 对向量结果做一个持久化
            self.vector_store.save_local(save_path)
        # 使用完模型后释放显存
        del self.embeddings
        torch.cuda.empty_cache()

    def GetTopK(self, query, k):
        # 获取top-K分数最高的文档块
        context = self.vector_store.similarity_search_with_score(query, k=k)
        return context

    # 返回faiss向量检索对象
    def GetvectorStore(self):
        return self.vector_store


if __name__ == "__main__":
    base = "."
    m3e = base + "/model/m3e-large"  # text2vec-large-chinese
    bge = base + "/model/bge-large-zh-v1.5"
    gte = base + "/model/nlp_gte_sentence-embedding_chinese-large"
    bce = base + "/model/bce-embedding-base_v1"
    m3 = base + "/model/bge-m3"

    dp = ReadFiles(path=base + "/data/train_a.pdf")
    dp.parse_block(max_seq=512)
    data = dp.data

    # faiss 召回: m3e-large
    m3e_faissretriever = FaissRetriever(m3e, data)
    m3e_faiss_ans = m3e_faissretriever.GetTopK("吉利汽车语音组手叫什么", 3)
    print(m3e_faiss_ans)

    # faiss 召回: bge-large
    bge_faissretriever = FaissRetriever(bge, data)
    bge_faiss_ans = bge_faissretriever.GetTopK("百米加速度", 3)
    print(bge_faiss_ans)

    # faiss 召回: gte-base
    gte_faissretriever = FaissRetriever(gte, data)
    gte_faiss_ans = gte_faissretriever.GetTopK("充电电压", 3)
    print(gte_faiss_ans)

    # faiss 召回: bce-base
    bce_faissretriever = FaissRetriever(bce, data)
    bce_faiss_ans = bce_faissretriever.GetTopK("续航", 3)
    print(bce_faiss_ans)

    # faiss 召回: bge-m3
    bce_faissretriever = FaissRetriever(bce, data)
    bce_faiss_ans = bce_faissretriever.GetTopK("加玻璃水", 3)
    print(bce_faiss_ans)

    # bm2.5 召回
    bm25 = BM25(data)
    bm25_res = bm25.GetBM25TopK("座椅加热", 3)
    print(bm25_res)

    # TFIDF 召回
    tfidf = TFIDF(data)
    tfidf_res = tfidf.GetTFIDFTopK("电池包", 3)
    print(tfidf_res)
