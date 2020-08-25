import luigi
import pandas as pd
import numpy as np
from tqdm import tqdm
import urllib.request
import json
import os
from classify_products import ClassifyProducts


tqdm.pandas()


class DownloadImages(luigi.Task):
    filePath = luigi.Parameter()
    nbLearn = luigi.IntParameter()

    def requires(self):
        return ClassifyProducts(self.filePath, self.nbLearn)

    def run(self):
        data = pd.DataFrame()
        self.images = set()

        with open("DOWNLOADED_DATA.json") as json_file:
            hist_data = json.load(json_file)

        self.images, self.urls = set(hist_data["images"]), hist_data["products"]
        
        with self.input()[0].open() as json_buffer:
            data = pd.read_json(json_buffer)
        print("\n ------------------ DOWNLOADING IMAGES  ----------------- \n")
        data.progress_apply(self.download_images, axis = 1)

        
        with open("DOWNLOADED_DATA.json") as json_file:
            json.dump({"images": list(self.images), "products" : self.urls}, json_file)


    def download_images(self, row):
        url, images = row["url"], row["images"]
        categories = row["categories"]
        if url in self.urls:
            return
        counter = len(self.urls)
        self.urls.append(url)
        location = "data/"
        for cat in categories:
            location += cat
            try:
                os.mkdir(location)
            except FileExistsError:
                pass
            location += "/"

        for x in range(len(images)):
            if images[x] in self.images:
                continue
            try:
                urllib.request.urlretrieve(images[x], location + str(counter) + "_" + str(x) + ".jpg")
                self.images.add(images[x])
            except:
                pass
            



if __name__ == "__main__":
    luigi.run()
