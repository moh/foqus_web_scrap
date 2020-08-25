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

        # select product with all probas more then UPDATE_PROBA
        
        data_train_new = data[data["prob"].apply(lambda probs : all([x >= UPDATE_PROBA for x in probs]))][["infos", "titleInfo", "categories", "url"]]
        # urls of new data
        new_urls = data_train_new["url"]
        data_train_old = data_train_old[data_train_old["url"].apply(lambda x : x not in new_urls)] # if url exist in new_urls so we don't take the row

        # add new training data to old training data
        data_train_all = data_train_old.append(data_train_new, ignore_index = True)

        # drop the duplicated rows
        data_train_all.drop_duplicates(inplace = True)

        save_data(data_train_all)

        # load models
        model_cat = joblib.load("model_classifier.pkl")
        model_hf = joblib.load("model_HF.pkl")

        # test
        data_train_all["mix"] = data_train_all.apply(lambda row : row["infos"] + " " + row["titleInfo"], axis = 1)
        # training infos
        train_data_from_infos = data_train_all["infos"].to_list()
        train_data_from_title = data_train_all["titleInfo"].to_list()
        # add the two training data
        # test with training only on infos data
        train_data = data_train_all["mix"].to_list() #train_data_from_infos# + train_data_from_title
        
        # train tags
        train_tags = data_train_all["categories"].to_list()
        train_hf_tags = [x[0] for x in train_tags]
        train_cat_tags = [x[1] for x in train_tags]
        # double train tags for data_from_infos and data_from_title
        # train_tags += train_tags

        print(" --------- INFO to VECTORS ---------")
        vectors = vectorizer.transform(train_data)
        print(" --------- DATA have been transformed to vectors ---------")


        print("------ TRAINING MODEL ---------")
        print("TRAINING HF model ===== ")
        model_hf.fit(vectors, train_hf_tags)
        print("\n TRAINING CATEGORY model ===== ")
        model_cat.fit(vectors, train_cat_tags)
        print("------ MODEL have been trained ---------")

        print("\n\n ------------ SAVING MODEL -----------")
        joblib.dump(model_cat, "model_classifier.pkl")
        joblib.dump(model_hf, "model_HF.pkl")
        

def save_data(data):
    f = open("TRAINING_DATA.json", "w")
    s = data.to_json(orient = "records").replace("{", "\n{")
    f.write(s)
    f.close()
        


if __name__ == "__main__":
    luigi.run()     
