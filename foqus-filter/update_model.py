'''

GENERAL INFORMATION :
=====================

This file contains one task, UpdateModel that will require the categorised data from the ClassifyProducts task,
and it will take the product with probability more them UPDATE_PROBA, and add those informations to the
TRAINING_DATA.json file that contains all the products for training.

'''

import luigi
import pandas as pd
import numpy as np
import json
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.externals import joblib
from classify_products import ClassifyProducts

from tqdm import tqdm
tqdm.pandas()

UPDATE_PROBA = 0.9
# number of feature for data vectors
nb_feature = 2**14

class UpdateModel(luigi.Task):
    filePath = luigi.Parameter()
    nbLearn = luigi.IntParameter()

    def requires(self):
        return ClassifyProducts(self.filePath, self.nbLearn)

    def run(self):
        data = pd.DataFrame()
        vectorizer = HashingVectorizer(n_features = nb_feature)

        with self.input()[0].open() as json_buffer:
            data = pd.read_json(json_buffer)

        # open old training data
        data_train_old = pd.read_json("TRAINING_DATA.json")

        # select product with proba more then UPDATE_PROBA
        data_train_new = data[data["prob"] >= UPDATE_PROBA][["infos", "titleInfo", "categories"]]
        
        data_train_new["categories"] = data_train_new["categories"].progress_apply(lambda x : x[0])

        # add new training data to old training data
        data_train_all = data_train_old.append(data_train_new, ignore_index = True)

        self.save_all_trainingData(data_train_all)

        # load model
        model = joblib.load("model_classifier.pkl")

        # training infos
        train_data_from_infos = data_train_all["infos"].to_list()
        train_data_from_title = data_train_all["titleInfo"].to_list()
        # add the two training data
        train_data = train_data_from_infos + train_data_from_title
        
        # train tags
        train_tags = data_train_all["categories"].to_list()
        # double train tags for data_from_infos and data_from_title
        train_tags += train_tags

        print(" --------- INFO to VECTORS ---------")
        vectors = vectorizer.transform(train_data)
        print(" --------- DATA have been transformed to vectors ---------")


        print("------ TRAINING MODEL ---------")
        model.fit(vectors, train_tags)
        print("------ MODEL have been trained ---------")

        print("\n\n ------------ SAVING MODEL -----------")
        joblib.dump(model, "model_classifier.pkl")
        

    def save_all_trainingData(self, data):
        f = open("TRAINING_DATA.json", "w")
        s = data.to_json(orient = "records").replace("{", "\n{")
        f.write(s)
        f.close()
        


if __name__ == "__main__":
    luigi.run()     
