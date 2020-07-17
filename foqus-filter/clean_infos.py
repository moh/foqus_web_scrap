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

# test
from tqdm import tqdm
tqdm.pandas()

#pandarallel.initialize(progress_bar = True)
LIMIT_REPETITION = 5

class CleanInfos(luigi.Task):
    filePath = luigi.Parameter()
    nbLearn = luigi.IntParameter()

    def requires(self):
        return CleanImages(self.filePath, self.nbLearn)

    def run(self):
        data = pd.DataFrame()

        with self.input()[0].open() as json_buffer:
            data = pd.read_json(json_buffer)

        data["urlBase"] = data["url"].progress_apply(url_base)
        print("\n\n ------------------ 2D TO 1D INFOS LIST ---------------------")
        data["infos"] = data["infos"].progress_apply(lambda x : list(chain.from_iterable(x)))#np.hstack(x))
        rep_infos = self.repeatedInfos(data)
        print("\n\n ------------------ CLEANING INFOS ------------------------")
        data["infos"] = data.progress_apply(lambda row : [y for y in row["infos"] if y not in rep_infos[row["urlBase"]]], axis = 1)
        data.drop("urlBase", axis = 1, inplace = True)
        
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
