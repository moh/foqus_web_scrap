'''

GENERAL INFORMATION :
=====================

This file contains one task, CleanImages, that will clean the images in the json
file, based on the urlBase.

filter_functions is a file that contains the function to clean the images for
each website.

'''


import luigi
import pandas as pd
#from pandarallel import pandarallel
from urllib.parse import urlparse
import json
from initiate_data import CleanProducts
import numpy as np
from filter_functions import imageFilter
from itertools import chain
from collections import Counter

from tqdm import tqdm
tqdm.pandas()

#pandarallel.initialize(progress_bar = True)

class CleanImages(luigi.Task):
    filePath = luigi.Parameter()
    nbLearn = luigi.IntParameter() # this is the number specified in the scrapping program to learn the method.

    def requires(self):
        return CleanProducts(self.filePath, self.nbLearn)

    def run(self):
        data = pd.DataFrame()

        with self.input()[0].open() as json_buffer:
            data = pd.read_json(json_buffer)
            
        data["urlBase"] = data["url"].progress_apply(url_base)
        rep_imgs = self.repeatedImgs(data)

        print("\n\n ------------------- CLEANING IMAGES ---------------------")
        data["images"] = data.progress_apply(lambda row : self.cleanImgs(row["urlBase"], row["images"], rep_imgs), axis = 1)

        # for test
        #data["categories"] = "a"
        with self.output()[0].open('w') as cleaned_json:
            s = data.to_json(orient = 'records').replace("{", "\n{")
            cleaned_json.write(s)

    def repeatedImgs(self, data):
        grpurl = data.groupby("urlBase")
        # get unique url bases
        urlBases = data["urlBase"].unique()
        imgRept = dict()
        for x in urlBases:
            images = list(chain.from_iterable(grpurl.get_group(x)["images"].to_list()))
            unique = list(Counter(images).keys())
            counts = list(Counter(images).values())
            #unique, counts = np.unique(images, return_counts = True)
            # we use set because it is faster to check membership
            imgRept[x] = set(unique[ind] for ind in range(len(unique)) if counts[ind] > 2)
        return imgRept

    def cleanImgs(self,urlBase, images, imgRept):
        new_images = set()
        for img in images:
            if img not in imgRept[urlBase]:
                if urlBase in imageFilter:
                    n_img = imageFilter[urlBase](img)
                else:
                    n_img = imageFilter["*"](img)
                if n_img != False: # if the filter returned a url
                    new_images.add(n_img)

        return list(new_images)

    def output(self):
        return [luigi.LocalTarget("cleanImgs_" + self.filePath)]


def url_base(url):
    base = urlparse(url).netloc
    base = ".".join(base.split(".")[-2:])
    return base


if __name__ == '__main__':
    luigi.run()
