'''

GENERAL INFORMATION :
=====================

This file contains two tasks, the first task is CheckJson, that will check the json
file, and output the file to the second task.
The second task is CleanProducts, this task will remove all the products that are not
of the same scraping method used by most of pages in the same sites, or not the same classes
used by the pages if the used method is the second one.

'''


import luigi
import pandas as pd
#from pandarallel import pandarallel
from urllib.parse import urlparse
import json

from tqdm import tqdm
tqdm.pandas()


#pandarallel.initialize(progress_bar = True)

class CheckJson(luigi.Task):
    filePath = luigi.Parameter()

    def run(self):
        pass

    def output(self):
        return luigi.LocalTarget(self.filePath)




class CleanProducts(luigi.Task):
    filePath = luigi.Parameter()
    nbLearn = luigi.IntParameter() # this is the number specified in the scrapping program to learn the method.

    def requires(self):
        return CheckJson(self.filePath)


    def run(self):
        data = pd.DataFrame()
        
        with self.input().open() as json_buffer:
            data = pd.read_json(json_buffer)
        data["urlBase"] = data["url"].progress_apply(url_base)
        urlBaseGrp = data.groupby("urlBase")

        clean_data, deleted_data1 = self.cleanByNumber(data, urlBaseGrp)
        clean_data, deleted_data2 = self.cleanByMethods(clean_data, urlBaseGrp)
        clean_data, deleted_data3 = self.cleanByClass(clean_data, urlBaseGrp)
        clean_data, deleted_data4 = self.cleanDuplicate(clean_data)
        
        deleted_data = deleted_data1.append(deleted_data2, ignore_index = True)
        deleted_data = deleted_data.append(deleted_data3, ignore_index = True)
        deleted_data = deleted_data.append(deleted_data4, ignore_index = True)
        deleted_data["categories"] = "deleted"

        with self.output()[0].open('w') as cleaned_json:
            s = clean_data.to_json(orient = 'records').replace("{", "\n{")
            cleaned_json.write(s)
            
        with self.output()[1].open('w') as deleted_json:
            s = deleted_data.to_json(orient = 'records').replace("{", "\n{")
            deleted_json.write(s)
        

    '''
        clean the products by the number of products for each website,
        if the number of products collected from a website is less then self.nbLearn,
        then we delete those data.
    '''
    def cleanByNumber(self, data, urlBaseGrp):
        deleted_rows = pd.DataFrame()
        cleaned_rows = pd.DataFrame()
        urlgrp = urlBaseGrp.count()["url"]
        print("\n\n -------------- CLEANING BY NUMBER -------------- ")
        cleaned_rows = data[data["urlBase"].progress_apply(lambda x : urlgrp[x] >= self.nbLearn)]
        deleted_rows = data[data["urlBase"].progress_apply(lambda x : urlgrp[x] < self.nbLearn)]
        deleted_rows.drop("method", axis = 1, inplace = True)
        deleted_rows.drop("classe", axis = 1, inplace = True)
        deleted_rows.drop("urlBase", axis = 1, inplace = True)
        return (cleaned_rows, deleted_rows)

    '''
        Clean the products by the methods used 
    '''
    def cleanByMethods(self, data, urlBaseGrp):
        deleted_rows = pd.DataFrame()
        cleaned_rows = pd.DataFrame()
        last_products = urlBaseGrp.tail(1)[["urlBase", "method"]]
        last_products.set_index("urlBase", inplace = True)
        print("\n\n ---------------- CLEANING BY METHOD ---------------- ")
        data["frequentMethod"] = data["urlBase"].progress_apply(lambda x : last_products.loc[x]["method"])
        cleaned_rows = data[data["method"] == data["frequentMethod"]]
        deleted_rows = data[data["method"] != data["frequentMethod"]]
        cleaned_rows.drop("frequentMethod", axis = 1, inplace = True)
        cleaned_rows.drop("method", axis = 1, inplace = True)
        deleted_rows.drop("frequentMethod", axis = 1, inplace = True)
        deleted_rows.drop("method", axis = 1, inplace = True)
        deleted_rows.drop("classe", axis = 1, inplace = True)
        deleted_rows.drop("urlBase", axis = 1, inplace = True)
        return (cleaned_rows, deleted_rows)

    '''
        Clean the products based on the most frequent class used for each product, if method is 2
    '''
    def cleanByClass(self, data, urlBaseGrp):
        deleted_rows = pd.DataFrame(columns = data.columns)
        cleaned_rows = pd.DataFrame(columns = data.columns)
        urlgrp = data.groupby("urlBase")
        last_products = urlgrp.tail(1)[["urlBase", "classe"]] # data frame of only the last product in each website
        last_products.set_index("urlBase", inplace = True)

        print("\n\n ------------------------ CLEANING BY CLASS ---------------------")
        data["frequentClass"] = data["urlBase"].progress_apply(lambda x : last_products.loc[x]["classe"])

        cleaned_rows = data[data["frequentClass"] == data["classe"]]
        deleted_rows = data[data["frequentClass"] != data["classe"]]
        
        
        cleaned_rows.drop("frequentClass", axis = 1, inplace = True)
        cleaned_rows.drop("classe", axis = 1, inplace = True)
        cleaned_rows.drop("urlBase", axis = 1, inplace = True)
        deleted_rows.drop("frequentClass", axis = 1, inplace = True)
        deleted_rows.drop("classe", axis = 1, inplace = True)
        deleted_rows.drop("urlBase", axis = 1, inplace = True)
        
        return (cleaned_rows, deleted_rows)

    '''
    Get only unique products, some products may have different links bu they are the same,
    we identitfy that they are the same by their titles and the list of images
    '''
    def cleanDuplicate(self, data):
        print("\n\n --------------------- CLEANING DUPLICATE -----------------------")
        data["title_img"] = data.progress_apply(lambda row : (row["title"], tuple(row["images"])), axis = 1)
        cleaned_rows = data.drop_duplicates("title_img", keep = "first")
        deleted_rows = data[~data.index.isin(cleaned_rows.index)]
        cleaned_rows.drop("title_img", axis = 1, inplace = True)
        deleted_rows.drop("title_img", axis = 1, inplace = True)

        return (cleaned_rows, deleted_rows)

    def output(self):
        return [luigi.LocalTarget("cleanedProducts_" + self.filePath), luigi.LocalTarget("deletedProducts_" + self.filePath)]

def url_base(url):
    base = urlparse(url).netloc
    base = ".".join(base.split(".")[-2:])
    return base

if __name__ == '__main__':
    luigi.run()
