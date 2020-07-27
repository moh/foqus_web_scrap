'''

GENERAL INFORMATION :
=====================

This file contains one task, CleanInfos, that will clean the informations in the
json file, it will eliminates the repeated infos.

'''

import luigi
import pandas as pd
#from pandarallel import pandarallel
from urllib.parse import urlparse
import json
import numpy as np
from itertools import chain
from collections import Counter
from clean_images import CleanImages
from filter_words import *

# test
from tqdm import tqdm
tqdm.pandas()

#pandarallel.initialize(progress_bar = True)
LIMIT_REPETITION = 29

class CleanInfos(luigi.Task):
    filePath = luigi.Parameter()
    nbLearn = luigi.IntParameter()

    def requires(self):
        return CleanImages(self.filePath, self.nbLearn)

    def run(self):
        data = pd.DataFrame()

        with self.input()[0].open() as json_buffer:
            data = pd.read_json(json_buffer)

        ## This part is to remove repeated informations between many products.
        ##
        data["urlBase"] = data["url"].progress_apply(url_base)
        print("\n\n ------------------ 2D TO 1D INFOS LIST ---------------------")
        data["infos"] = data["infos"].progress_apply(lambda x : list(chain.from_iterable(x)))#np.hstack(x))
        rep_infos = self.repeatedInfos(data)
        print("\n\n ------------------ CLEANING INFOS ------------------------")
        data["infos"] = data.progress_apply(lambda row : [y for y in row["infos"] if y not in rep_infos[row["urlBase"]]], axis = 1)
        data.drop("urlBase", axis = 1, inplace = True)

        ## This part is to obtain key words for each product based on the informations
        ##
        '''
        print("\n\n ------------------- INFO LIST to STR ----------------------")
        data["infos"] = data["infos"].progress_apply(lambda x : ' '.join(x))

        data["infos"] = data["infos"].apply(lambda x : x.lower())
        print("\n\n ------------------- REPLACING ACCENT -----------------------")
        data["infos"] = data["infos"].progress_apply(replaceAccent)
        
        print("\n\n ------------------- REMOVING PUNCTUATIONS ------------------")
        data["infos"] = data["infos"].progress_apply(removePunctuations)
        
        print("\n\n ------------------- SPLIT INFOS WORDS ----------------------")
        data["infos"] = data["infos"].progress_apply(lambda x : x.split())

        print("\n\n ------------------- REMOVING STOPWORDS ---------------------")
        data["infos"] = data["infos"].progress_apply(removeFromList)

        '''

        ## other way to clean info, where we clean each list of info
        ## here we don't get a list of keywords, instead a list of phrase
        data["infos"] = data["infos"].progress_apply(lambda lst : [replaceAccent(x) for x in lst])
        data["infos"] = data["infos"].progress_apply(lambda lst : [removePunctuations(x) for x in lst])
        data["infos"] = data["infos"].progress_apply(lambda lst : [x.lower() for x in lst])
        data["infos"] = data["infos"].progress_apply(lambda lst : [cleanStr(x) for x in lst])
        data["infos"] = data["infos"].progress_apply(lambda lst : list(set(lst)))
        # only keep string of length more then 3
        data["infos"] = data["infos"].progress_apply(lambda lst : [x for x in lst if len(x.split()) >= 3])
        data["infos"] = data["infos"].progress_apply(lambda lst : " ".join(lst))
        

        ## This part is to obtain key words from the title
        ##
        print("\n\n ===== TITLE CLEANING =====")
        print("\n\n ------------------- CLEANING TITLE AND PLACING IN titleInfo COLUMN --------------------------")
        data["titleInfo"] = data["title"].progress_apply(removePunctuations)
        data["titleInfo"] = data["titleInfo"].progress_apply(lambda x : x.lower())
        data["titleInfo"] = data["titleInfo"].progress_apply(replaceAccent)
        data["titleInfo"] = data["titleInfo"].progress_apply(lambda x : x.split())
        data["titleInfo"] = data["titleInfo"].progress_apply(removeFromList)
        data["titleInfo"] = data["titleInfo"].progress_apply(lambda lst : " ".join(lst))
        
        with self.output()[0].open('w') as cleaned_json:
            s = data.to_json(orient = 'records').replace("{", "\n{")
            cleaned_json.write(s)


    def repeatedInfos(self, data):
        grpurl = data.groupby("urlBase")
        # get unique url bases
        urlBases = data["urlBase"].unique()
        infoRept = dict()
        for x in urlBases:
            infos = list(chain.from_iterable(grpurl.get_group(x)["infos"].to_list()))
            unique = list(Counter(infos).keys())
            counts = list(Counter(infos).values())
            #unique, counts = np.unique(infos, return_counts = True)
            # we use set because it is faster to check membership
            infoRept[x] = set(unique[ind] for ind in range(len(unique)) if counts[ind] >= LIMIT_REPETITION)
        return infoRept


    def output(self):
        return [luigi.LocalTarget("cleanInfo_" + self.filePath)]



def url_base(url):
    base = urlparse(url).netloc
    base = ".".join(base.split(".")[-2:])
    return base


if __name__ == '__main__':
    luigi.run()
