# -*- coding: utf-8 -*-
import os
import scrapy
import csv
from scrapy.http import Request
from urllib.parse import urlparse
from w3lib.html import remove_tags
import re
# common_words contain words used frequently by websites
from foqusBot.common_words import *

# MIN_RATIO is the min ratio where the page is still identified as home or product page
MIN_RATIO = 0.3

# UPDATE_RATIO : if the ratio of classes is more then those ratio then we are pretty sure about the nature of the page,
# so we add the classes found here to the list of the specified nature
UPDATE_RATIO = 0.8

class GeneralSpider(scrapy.Spider):
    name = 'generalFoqus'

    '''
    url_home_products: dict that have keys the base of the website, and value a list of links to the home page and product page.

    url_classes : dict that have keys the base of the website, and value two lists, that
    represents the list of class of home page, and the list of class of product page

    visited_urls : dict that have keys the base of the website, and value the links visited from that site.

    shared_product_info : dict that have keys the base of the website, and value the shared part of product
                        informations (usually it is related to general information about the website)
    '''
    def __init__(self, *a, **kw):
        super(GeneralSpider, self).__init__(*a, **kw)
        self.url_home_products = dict()
        self.url_classes = dict()
        self.visited_urls = dict()
        self.shared_product_info = dict()
        self.order = 0
        

    '''
    Here we override the method start_requests to start with the request of the home page,
    of the sites that are given in the csv file.
    
    '''
    def start_requests(self):
        with open("sites.csv", "r") as f:
            reader = csv.reader(f, delimiter = ",")
            for line in reader:
                # store the home and product page in the dict
                self.url_home_products[self.getUrlBase(line[0])] = line
                yield Request(line[0], callback = self.getHomeClasses)
                


    '''
    This method will extract the classes from the home page that is given in the csv file,
    it will help us to identify the pages that ressemble to the home page.

    NOTE : This method should be called before getProductClasses
    ======
    '''
    def getHomeClasses(self, response):
        classes = response.xpath("//@class").getall()
        # variable that will contain all the class names
        final_classes = set()

        for class_names in classes:
            final_classes = final_classes.union(set(class_names.split(" ")))

        # add the home classes to the dictionary
        self.url_classes[self.getUrlBase(response.url)] = [final_classes, set()]

        yield Request(self.url_home_products[self.getUrlBase(response.url)][1],
                      callback = self.getProductClasses)

    '''
    This method will extract the classes from the product page that is given in the csv file,
    then it will filter only the uniq classes in the home and product pages.

    NOTE : This method should be called after getHomeClasses
    ======
    '''
    def getProductClasses(self, response):
        classes = response.xpath("//@class").getall()
        final_classes = set()
        
        for class_names in classes:
            final_classes = final_classes.union(set(class_names.split(" ")))

        # this part to get the unique classes of home and product page
        homePageClasses = self.url_classes[self.getUrlBase(response.url)][0]
        product_classes = final_classes - homePageClasses
        home_classes = homePageClasses - final_classes

        self.url_classes[self.getUrlBase(response.url)] = [home_classes, product_classes]
        
        # call the home page to analyse links
        yield Request(self.url_home_products[self.getUrlBase(response.url)][0], dont_filter = True)
        

    '''
    The default method that is called after yield a request to a page
    '''
    def parse(self, response):
        infos = self.identifyPage(response)
        
        # the page is neither a home nor a product
        if (not(infos["is_home"]) and not(infos["is_product"])):
            return
        
        elif infos["is_product"]:
            print("\n================== is product : url ", response.url)
            print("ratios product / page ", infos["ratio_product"], "    ", infos["ratio_home"], "\n")
            yield self.getProductInfo(response, infos["product_shared"])
            
        else:
            print("\n ------------------ is PAGE : url ", response.url)
            print("ratios product / page ", infos["ratio_product"], "    ", infos["ratio_home"], "\n")
            
        links = self.getPageLinks(response)
        self.order -= 1
        for link in links:
            try:
                self.visited_urls[self.getUrlBase(link)].add(link)
            except: # if the website base is not a key
                self.visited_urls[self.getUrlBase(link)] = {link}
            yield Request(link, priority = self.order)
            
        
        
    """
    =================================================================================
        This part is for identifying pages and filtering pages And Additional method
    =================================================================================
    """

    '''
    This method is to identify the nature of the page, wether it is a home page or product pages.

    
    If both of the ratios are greater then UPDATE_RATIO then we consider that the page is neither a home page or product page

    If home ratio is greater then UPDATE_RATIO then we add the classes of the page to the home classes
    If product ratio is greater then UPDATE_RATIO then we add the classes of the page to the product classes
    
    it will return a dictionnary ::: product_shared: classes that are shared with product classes,
    home_shared : classes that are shared with home classes, is_home : if it is a home page,
    is_product: if it is a product page.
    
    '''
    def identifyPage(self, response):
        home_classes, product_classes = self.url_classes[self.getUrlBase(response.url)]

        # get the classes presented in the page
        classes = response.xpath("//@class").getall()
        page_classes = set()

        for class_names in classes:
            page_classes = page_classes.union(set(class_names.split(" ")))

        # number of classes in common with home page
        home_shared = page_classes.intersection(home_classes)
        # number of classes in common with product page
        product_shared = page_classes.intersection(product_classes)

        ratio_home = len(home_shared) / len(home_classes)
        ratio_product = len(product_shared) / len(product_classes)

        is_home = ratio_home > ratio_product
        is_product = ratio_home < ratio_product

        # if the two ratio are smaller then MIN_RATIO, then the page is neither a product nor a home page
        if( (ratio_home < MIN_RATIO) and (ratio_product < MIN_RATIO)):
            is_home = is_product = False

        '''
        # if it is only identical to product page
        # !!! NOTE this should be placed before home, because home look like the product too
        elif (ratio_product > UPDATE_RATIO):
            product_classes = product_classes.union(page_classes - home_classes)
            is_product, is_home = True, False
        # if it is only so identical to home page
        elif (ratio_home > UPDATE_RATIO):
            home_classes = home_classes.union(page_classes - product_classes)
        '''
        
        self.url_classes[self.getUrlBase(response.url)] = [home_classes, product_classes]
             
        return({"product_shared": product_shared, "home_shared" : home_shared,"is_home":is_home, "is_product":is_product
                , "ratio_home":ratio_home, "ratio_product" : ratio_product})
        # return ({"url" : response.url,"is_home":is_home, "is_product":is_product, "home_ratio":ratio_home, "product_ratio" : ratio_product})


    '''

    Get the information from the product page

    '''
    def getProductInfo(self, response, product_shared):
        print("PRODUCT_CLASSE : ", product_shared)
        product_classes = [x for x in product_shared if self.shareWithList(x, product_identifiers)]
        product_classes = [x for x in product_classes if len(response.css("." + x)) == 1]

        image_classes = [x for x in product_classes if self.shareWithList(x, images_identifiers)]
        infos_classes = [x for x in product_classes if self.shareWithList(x, infos_identifiers)]
        title_classes = [x for x in product_classes if self.shareWithList(x, title_identifiers)]
        
        images = self.getImgsFromClasses(response ,image_classes) # get the images
        titles = self.getTitle(response, title_classes)
        informations = self.getInfosFromClasses(response, infos_classes)
        all_informations = self.getAllInfosFromClasses(response, infos_classes)

        if len(images) == 0:
            images = self.getImgFromTitleDiv(response)
        
        return {"url" : response.url,"images" : images, "titles" : titles, "informations": informations, "all_informations":all_informations} #, "price" : price}
        
        #return {"url" : response.url, "product_classes" : product_classes, "product_shared" : product_shared , "image_classes" : gallery_classes, "infos_classes" : infos_classes}

    def getImgsFromClasses(self, response,classes):
        images = set()
        for classe in classes:
            imgs = set(response.css("." + classe)[0].xpath('descendant::img/@src').getall())
            images = images.union(imgs)

        # in some site, the url is not in a src attribute.
        if (len(images) == 0 and len(classes) != 0):
            for classe in classes:
                imgs = response.css("." + classe)[0].xpath("descendant::img").getall()
                images = images.union(self.extractUrlFromImgs(imgs))
            
        return [ response.urljoin(x) for x in images] # get the absolute urls

    def getTitle(self, response, classes):
        h1_title = response.css("h1") # usually title written in h1
        if len(h1_title) <= 2:
            titles = {remove_tags(x) for x in h1_title.getall()}
        else:
            titles = set()
            for classe in classes:
                titles.add(response.css("." + classe)[0].xpath('text()').get())
        if len(titles) == 1:
            return list(titles)[0]
        return list(titles)

    def getInfosFromClasses(self, response, classes):
        informations = []
        url_base = self.getUrlBase(response.url)
        for classe in classes:
            info_div = response.css("." + classe)[0]
            for tag in tag_info:
                infos = info_div.xpath("*//" + tag).getall() # select span and texts
                infos = [remove_tags(x) for x in infos]
                infos = [x.strip() for x in infos if self.textNotEmpty(x)]
                if infos != []: informations.append(infos) #informations.union(set(infos.split("\n")))

        # informations = [x.strip() for x in informations if self.textNotEmpty(x)]
        '''
        if url_base in self.shared_product_info:
            common_info = set(informations).intersection(self.shared_product_info[url_base])
            self.shared_product_info[url_base] = common_info
            informations = list(set(informations) - common_info)

        else: # if this is the first product from that website
            self.shared_product_info[url_base] = set(informations)
        '''
        return informations

    # this will return all the text found in the section
    def getAllInfosFromClasses(self, response, classes):
        resp = response.copy()
        scripts = resp.xpath("//script")
        informations = []
        # remove all script from response
        for script in scripts:
            script.remove()
        for classe in classes:
            info_div_str = resp.css("." + classe).get()
            infos = remove_tags(info_div_str)
            infos = [x.strip() for x in infos.split("\n") if self.textNotEmpty(x)]
            if infos != []: informations.append(infos)
        return informations

    # NOTE TO CHANGE THE MINE NUMBER 2, and test
    # 
    def getImgFromTitleDiv(self, response):
        title_div = response.css("h1") # get h1 div
        titles = {remove_tags(x) for x in title_div.getall()}
        # if we have multiple h1 with different contents
        if len(titles) > 1:
            return []
        title_div = title_div[-1] # select the last h1 div.
        title_div_parents = title_div.xpath("ancestor::*")
        div_parent, div_child = None, None
        for div in title_div_parents[::-1]:
            if len(div.css("img")) >= 2:
                div_parent = div
                break
        if div_parent == None: return []
        div_childrens = div_parent.xpath("*")
        for div in div_childrens:
            if len(div.css("img")) >= 2:
                div_child = div
                break
        if div_child == None: return []
        images = set(div_child.xpath("descendant::img/@src").getall())
        return [response.urljoin(x) for x in images]
        

    '''
    get the links presented in the page
    '''
    def getPageLinks(self, response):
        links = response.xpath(self.getXpathForLinks(response)).getall()
        try:
            links = {response.urljoin(x) for x in links if x not in self.visited_urls[self.getUrlBase(response.url)]}
        except: # if url base is not a key in dict then pass
            pass
        # filter the links, accept who has same domain and a valid extension
        links = {x for x in links if ((self.getUrlBase(response.url) in self.getUrlNetloc(x)) and self.isValidUrl(x))}
        return links

    
    """
    return the xpath query for all links with the condition to not contain the words in the common word list
    NOTE : links maybe relative so shouldn't check for base url before the join
    """
    def getXpathForLinks(self, response):
        xpath_query = "//a["
        for word in common_words:
            xpath_query += " not(contains(@href,'" + word + "')) and"
        # eliminate the last "and"
        if "and" in xpath_query:
            xpath_query = xpath_query[:-3]
            
        xpath_query += "]/@href"
        return xpath_query

    """
    get the base link of the website, for example : www.google.com ---> google.com , mail.google.com --> google.com
    
    """
    def getUrlBase(self, url):
        base = urlparse(url).netloc
        base = ".".join(base.split(".")[-2:])
        return base

    """
    getUrlNetloc get the net location from the url
    """
    def getUrlNetloc(self, url):
        return urlparse(url).netloc
        

    """
    A function that check if we had common words in class_name and words in word_list.
    """
    def shareWithList(self, class_name, word_list):
        for x in word_list:
            if x in class_name.lower():
                return True
        return False

    """
    
    """
    def isValidUrl(self, url):
        # valid extension for web page
        try:
            accepted_extensions = [".php", ".html", ".htm", ""]
            url_path = urlparse(url).path
            filename, extension = os.path.splitext(url_path)
            return extension in accepted_extensions
        except Exception as e:
            print(e)
            
        return False

    def textNotEmpty(self, x):
        emptyList = [" ", "\n", "\t", ".", ",", ";", "\r"]
        for y in emptyList:
            x = x.replace(y, "")
        return x != ""

    def extractUrlFromImgs(self, imgs):
        links = set()
        for img in imgs:
            links = links.union(set(re.findall(r'(https?://\S+)', img)))
        links = {x[:-1] for x in links} # because they will cotains " at the end
        return links
