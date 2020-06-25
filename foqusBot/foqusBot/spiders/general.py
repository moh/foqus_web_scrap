# -*- coding: utf-8 -*-
import os
import scrapy
import csv
from scrapy.http import Request
from urllib.parse import urlparse
from w3lib.html import remove_tags
# common_words contain words used frequently by websites
from foqusBot.common_words import *

# MIN_RATIO is the min ratio where the page is still identified as home or product page
MIN_RATIO = 0.2

# UPDATE_RATIO : if the ratio of classes is more then those ratio then we are pretty sure about the nature of the page,
# so we add the classes found here to the list of the specified nature
UPDATE_RATIO = 0.8

class GeneralSpider(scrapy.Spider):
    name = 'generalFoqus'

    '''
    url_home_products: dict that have keys the base of the website, and value a list of links to the home page and product page.

    url_classes : dict that have keys the base of the website, and value two lists, that
    represents the list of class of home page, and the list of class of product page

    
    '''
    def __init__(self, *a, **kw):
        super(GeneralSpider, self).__init__(*a, **kw)
        self.url_home_products = dict()
        self.url_classes = dict()
        self.visited_urls = dict()
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
            yield self.getProductInfo(response, infos["product_shared"])
            
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

        # if it is only so identical to home page
        elif (ratio_home > UPDATE_RATIO):
            home_classes = home_classes.union(page_classes - product_classes)
        # if it is only identical to home page
        elif (ratio_product > UPDATE_RATIO):
            product_classes = product_classes.union(page_classes - home_classes)

        self.url_classes[self.getUrlBase(response.url)] = [home_classes, product_classes]
             
        return({"product_shared": product_shared, "home_shared" : home_shared,"is_home":is_home, "is_product":is_product})
        # return ({"url" : response.url,"is_home":is_home, "is_product":is_product, "home_ratio":ratio_home, "product_ratio" : ratio_product})


    '''

    Get the information from the product page

    '''
    def getProductInfo(self, response, product_shared):
        product_classes = [x for x in product_shared if self.shareWithList(x, product_identifiers)]
        product_classes = [x for x in product_classes if len(response.css("." + x)) == 1]

        image_classes = [x for x in product_classes if self.shareWithList(x, images_identifiers)]
        infos_classes = [x for x in product_classes if self.shareWithList(x, infos_identifiers)]
        title_classes = [x for x in product_classes if self.shareWithList(x, title_identifiers)]

        images = self.getImgsFromClasses(response ,image_classes) # get the images
        titles = self.getTitle(response, title_classes)
        
        '''
        imgs = set()
        for classe in gallery_classes:
            local_imgs = set(response.css("." + classe)[0].xpath('descendant::img/@src').getall())
            imgs = imgs.union(local_imgs)
            
        titles = [response.css("." + x).xpath("text()").get() for x in title_classes]
        price = []
        for classe in infos_classes:
            # select all classes inside the element of class = classe
            try:
                cls = response.css("." + classe)[0].xpath("descendant::*/@class").getall()
                cls = [x for x in cls if "price" in x.lower()][0]
                price.append(response.css("." + cls)[0].xpath("descendant::text()").getall())
            except:
                pass
        '''
        return {"url" : response.url,"images" : images, "titles" : titles} #, "price" : price}
        
        #return {"url" : response.url, "product_classes" : product_classes, "product_shared" : product_shared , "image_classes" : gallery_classes, "infos_classes" : infos_classes}

    def getImgsFromClasses(self, response,classes):
        images = set()
        for classe in classes:
            imgs = set(response.css("." + classe)[0].xpath('descendant::img/@src').getall())
            images = images.union(imgs)

        return list(images)

    def getTitle(self, response, classes):
        h1_title = response.css("h1") # usually title written in h1
        if len(h1_title) == 1:
            return remove_tags(h1_title.get())
        else:
            titles = set()
            for classe in classes:
                titles.add(response.css("." + classe)[0].xpath('text()').get())
            return list(titles)
            

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
            print("\n /\/\/\/\/\/\/\/\/\/\/\/\/\ Error /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\ \n")
            print(e)
            print("\n /\/\/\/\/\/\/\/\/\/\/\/\/\ Error /\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\ \n")
            
            return False
