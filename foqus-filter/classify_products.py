'''

GENERAL INFORMATION :
=====================

This file contains one task, ClassifyProducts that will try to give each products a category,
if it can't we will give it the category other.

'''

import luigi
import pandas as pd
import numpy as np
import json
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.externals import joblib
from clean_infos import CleanInfos
from filter_words import *

from tqdm import tqdm
tqdm.pandas()

LIMIT_PROBA = 0.4
INFO_RATIO = 0.7

class ClassifyProducts(luigi.Task):
    filePath = luigi.Parameter()
    nbLearn = luigi.IntParameter()

    def requires(self):
        return CleanInfos(self.filePath, self.nbLearn)

    def run(self):
        data = pd.DataFrame()

        with self.input()[0].open() as json_buffer:
            data = pd.read_json(json_buffer)

        # vectorizer
        nb_feature = 2**14
        vectorizer = HashingVectorizer(n_features = nb_feature)
        # load saved model from model_classifier.pkl
        model = joblib.load("model_classifier.pkl")

        #print(" ----------- combining infos -----------------")
        #data["allInfo"] = data.progress_apply(lambda row : row["infos"] + " " + row["titleInfo"], axis = 1)

        print("----------------------------- Predicting Category ---------------------")
        data["categories"] = data.progress_apply(lambda row : self.get_categories(row, vectorizer, model), axis = 1)

        print("----------------------------- Splitting proba and categories --------------------")
        data["prob"] = data["categories"].progress_apply(lambda x : x[0][0])
        data["categories"] = data["categories"].progress_apply(lambda x : [x[0][1]])

        # drop the created allInfo
        #data.drop("allInfo", axis = 1, inplace = True)

        with self.output()[0].open("w") as cleaned_json:
            s = data.to_json(orient = 'records').replace("{", "\n{")
            cleaned_json.write(s)


    def output(self):
        return [luigi.LocalTarget("categorised_" + self.filePath)]


    def get_categories(self, row, vectorizer, model):
        classes = model.classes_
        infos, titleInfo = row["infos"], row["titleInfo"]
        vect_titleInfo = vectorizer.transform([titleInfo])
        vect_info = vectorizer.transform([infos])

        proba_titleInfo = model.predict_proba(vect_titleInfo)[0]
        proba_info = model.predict_proba(vect_info)[0]
        probas = proba_titleInfo * (1 - INFO_RATIO) + proba_info * INFO_RATIO
        prob_class = [(probas[x], classes[x]) for x in range(len(probas))]
        prob_class.sort()
        prob_class = prob_class[::-1]
        selected_class = prob_class[0]
        if selected_class[0] < LIMIT_PROBA:
            selected_class = (selected_class[0] ,"other")
        return [selected_class]
        

if __name__ == "__main__":
    luigi.run()
