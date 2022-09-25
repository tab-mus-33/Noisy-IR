
<h1> Implementation Proactive Information Retrieval and other approaches on Spotify Podcast Dataset </h1>

The repository has code for implementing multiple approaches for IR on Noisy Data 

The implementatio provides gains in Early Precision on current state of the art approaches

Since the project involves around 400+ GB of additional data dependency, the files can be found on 
https://drive.google.com/drive/folders/1SdID4kNAE5y3MR2PuDXuCC8GfGQkihuW?usp=sharing


The Baselines and LTR approaches can be run through https://github.com/tab-mus-33/Noisy-IR/blob/main/Basleline_Runs_%2B_QE_%2B_LTR.ipynb
 
The file assumes conversion to TREC XML format from JSON files and can be done using https://github.com/tab-mus-33/Noisy-IR/blob/main/Convert_to_Trec_XML.ipynb
which in turn uses https://github.com/tab-mus-33/Noisy-IR/blob/main/converter.py

Neural Approaches :  https://github.com/tab-mus-33/Noisy-IR/blob/main/Nueral_Re_ranking.ipynb

NER Approaches with DCU Replication : https://github.com/tab-mus-33/Noisy-IR/blob/main/Named_Entity_Recognition.ipynb

Proactive IR Proposed on Podcast Small : https://github.com/tab-mus-33/Noisy-IR/blob/main/Proactive_IR_Experiments_train(Podcast_Small).ipynb

Proactive IR Proposed on Podcast SE : https://github.com/tab-mus-33/Noisy-IR/blob/main/Proactive_IR_Experiments_train(Podcast_Small).ipynb

The rest of the files include various other runs and dependencies including pre/post processing for the experiments. 

The hardware requirement for replication must be kept in mind. Recommended hardware Google Colab Pro + and above (uninterrupted access to a High Performance Cluster) 

Upto a Terrabyte of Storage and 50+ GB of RAM. 


Codes Referenced from :https://github.com/yasumori

https://github.com/sahanbull/context-agnostic-engagement/blob/0472e76c6bd00d686b235d844e2fb4d71649400c/context_agnostic_engagement/feature_extraction/_api_utils.py#L47

References:

https://trec.nist.gov/pubs/trec29/papers/DCU-ADAPT.P.pdf
