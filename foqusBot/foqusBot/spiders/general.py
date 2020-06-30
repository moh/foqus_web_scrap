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

# the number of pages to learn from to extract wich method is used frequently, and wich class is detected in title div method ( for images)
LEARN_IMG_NB_PAGE = 20

class GeneralSpider(scrapy.Spider):
    name = 'generalFoqus'

    '''
    url_home_products: dict that have keys the base of the website, and value a list of links to the home page and product page.

    url_classes : dict that have keys the base of the website, and value two lists, that
    represents the list of class of home page, and the list of class of product page

    shared_product_info : dict that have keys the base of the website, and value the shared part of product
                        informations (usually it is related to general information about the website)

    methods_stat : dict that have keys the base of the website, and value a list that represent the number of time
    each method (of extracting images) is used on the website. ( first number represents the first method ( class
    name method), second number represents the second method ( title div method ))

    titleImg_method_classes : dict that have keys the base of the website, and value a dictionary that represents the
    class found of the div as a key and a list that contains the number of repetition of that class, and the
    score associated to it (score  = number of img found) as a value
    
    order : the order of excuting the request in parse method
    '''
    def __init__(self, *a, **kw):
        super(GeneralSpider, self).__init__(*a, **kw)
        self.url_home_products = dict()
        self.url_classes = dict()
        self.shared_product_info = dict()
        self.methods_stat = dict()
        self.titleImg_method_classes = dict()
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

        # initiate the method statistics to zeros
        self.methods_stat[self.getUrlBase(response.url)] = [0, 0]
        # call the home page to analyse links
        yield Request(self.url_home_products[self.getUrlBase(response.url)][0], dont_filter = True)
        

    '''
    The default method that is called after yield a request to a page
    '''
    def parse(self, response):
        infos = self.identifyPage(response)
        
        # the page is neither a home nor a product
        if (not(infos["is_home"]) and not(infos["is_product"])):
            print("\n================== is NOTHING :  url ", response.url)
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
        
        self.url_classes[self.getUrlBase(response.url)] = [home_classes, product_classes]
             
        return({"product_shared": product_shared, "home_shared" : home_shared,"is_home":is_home, "is_product":is_product
                , "ratio_home":ratio_home, "ratio_product" : ratio_product})

    '''

    Get the information from the product page

    '''
    def getProductInfo(self, response, product_shared):
        url_base = self.getUrlBase(response.url)
        method = ""
        nb_pages, ratio_first_method = sum(self.methods_stat[url_base]), 0
        product_classes = [x for x in product_shared if self.shareWithList(x, product_identifiers)]
        product_classes = [x for x in product_classes if len(response.xpath('//*[contains(@class, "'+x+'")]')) == 1]

        image_classes = [x for x in product_classes if self.shareWithList(x, images_identifiers)]
        # infos_classes = [x for x in product_classes if self.shareWithList(x, infos_identifiers)]
        title_classes = [x for x in product_classes if self.shareWithList(x, title_identifiers)]
        
        images = self.getImgsFromClasses(response ,image_classes) # get the images
        titles = self.getTitle(response, title_classes)
        # informations = self.getInfosFromClasses(response, infos_classes)
        # all_informations = self.getAllInfosFromClasses(response, infos_classes)

        if nb_pages != 0:
            ratio_first_method = self.methods_stat[url_base][0] / nb_pages
        
        # if ratio_first_method is less then half and the pages that we have tested are more then 10, then
        # we always do the second method
        if (len(images) <= 2 and nb_pages < LEARN_IMG_NB_PAGE) or (ratio_first_method < 0.5 and nb_pages >= LEARN_IMG_NB_PAGE):
            images = self.getImgFromTitleDiv(response)
            self.methods_stat[url_base][1] += 1 # update number related to second method.
            method = "2"
        else:
            self.methods_stat[url_base][0] += 1 # update number related to first method.
            method = "1"
            
        #print("\n Method statisticss !! :::: ", self.methods_stat[url_base])
        #return {"url" : response.url,"images" : images, "titles" : titles, "informations": informations,
        #       "all_informations":all_informations, "method":method, "stat":self.titleImg_method_classes} #, "price" : price}

        return {"url" : response.url,"images" : images, "titles" : titles, "method":method, "stat":self.titleImg_method_classes}
        
    '''

    Return the images src URL that are descendant of a div that have the classes in the list.
    classes is a list of classe that have some specific words like product, image ...
    
    '''
    def getImgsFromClasses(self, response, classes):
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

    '''

    Get the title of the product in the page.
    First we search for the h1 tags, as usually it contains the title.
    if we have h1 tags we return the text inside the first one.
    if not we search for the title using a list of classes related to product and title.
    
    '''
    def getTitle(self, response, classes):
        h1_title = response.css("h1") # usually title written in h1
        if len(h1_title) > 0:
            return remove_tags(h1_title.get())
        else:
            titles = set()
            for classe in classes:
                titles.add(response.css("." + classe)[0].xpath('text()').get())
        if len(titles) == 1:
            return list(titles)[0]
        return list(titles)

    '''

    Get the product informations using a list of classe related to product and informations.
    This method may not extract all the useful informations that we need, as the class may not
    contain the specific words that we have defined.
    it also select only the text inside the tags that are listed in tag_info.
    
    '''
    def getInfosFromClasses(self, response, classes):
        informations = []
        url_base = self.getUrlBase(response.url)
        for classe in classes:
            info_div = response.css("." + classe)[0]
            for tag in tag_info:
                infos = info_div.xpath("*//" + tag).getall() # select span and texts
                infos = [remove_tags(x) for x in infos]
                infos = [x.strip() for x in infos if self.textNotEmpty(x)]
                if infos != []: informations.append(infos)

        return informations

    '''

    This method is identical to getInfosFromClasses, but the difference is that we don't
    look at specific tag to extract the text inside of them, but instead we eliminate all the tags
    inside the div and return the data.
    It is also not so accurate.

    '''
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


    '''

    This method is an alternative way to extract images related to product, in case the
    first method based on class names didn't work.
    it looks for the h1 tag that contains the title, then search for the images by iterating the
    ancestor of the title, it relys on the number of images found. ( more then 1 )
    it also store the class of the child div found, and then if we have a repeated class over many page, we will
    suppose that in all the other page this div contain the searched images.
    
    '''
    def getImgFromTitleDiv(self, response):
        url_base = self.getUrlBase(response.url)

        try:
            stat_dict = self.titleImg_method_classes[url_base]
            # select the class that have maximum number of pages
            max_classe_ByNb = max(stat_dict, key = lambda x : stat_dict[x][0])

            # select the class that have maximum number of score ( nb of images )
            max_classe_ByScore = max(stat_dict, key = lambda x : stat_dict[x][1])
            
            nb_pages = sum([x[0] for x in stat_dict.values()]) # total number of pages
            total_scores = sum([x[1] for x in stat_dict.values()]) # total scores
            
            # if more them LEARN_IMG_NB_PAGE have been scraped then we try to follow old pages
            if nb_pages >= LEARN_IMG_NB_PAGE:
                selected_class = ""
                # if the class with max score have a score more then 0.5 of total score, and has been used in more then 0.4 of classes then we use it
                if (stat_dict[max_classe_ByScore][0]/nb_pages >= 0.4 and stat_dict[max_classe_ByScore][1]/total_scores >= 0.5):
                    selected_class = max_classe_ByScore
                    
                # if the most used class have a ration of more then 0.5 then we return images inside the div of that class
                elif stat_dict[max_classe_ByNb][0]/nb_pages >= 0.5:
                    selected_class = max_classe_ByNb
                if selected_class != "":
                    imgs = self.getImgsByClassedDiv(response, selected_class)
                    if len(imgs) > 0:
                        self.titleImg_method_classes[url_base][selected_class][0] += 1
                        self.titleImg_method_classes[url_base][selected_class][1] += len(imgs) # update the score 
                        return imgs
                    
        # in case url_base is not in dict then initialise it
        except KeyError:
            self.titleImg_method_classes[url_base] = dict()
            
        title_div = response.css("h1") # get h1 div
        if len(title_div) == 0: return [] # if no h1 tag found return empty list
        title_div = title_div[0] # select the first h1 div ( it should be the title )
        title_div_parents = title_div.xpath("ancestor::*")
        div_parent, div_child = None, None
        for div in title_div_parents[::-1]:
            if len(set(div.xpath("descendant::img/@src").getall())) >= 2:
                div_parent = div
                break
        # if no parent have more then 1 image we return []
        if div_parent == None: return []
        # search for the first descendant of div_parent that satisfies the condition
        div_childrens = div_parent.xpath("descendant::div")
        for div in div_childrens:
            nb_img = len(set(div.xpath("descendant::img/@src").getall()))
            if nb_img >= 2 and nb_img <= 10: # limit the number to between 2 and 10
                div_child = div
                break
        if div_child == None: return []
        images = set(div_child.xpath("descendant::img/@src").getall()) # get the src of images inside the div_child tag

        div_child_class = div_child.xpath("@class").get()
        try:
            self.titleImg_method_classes[url_base][div_child_class][0] += 1
            self.titleImg_method_classes[url_base][div_child_class][1] += len(images) # update the score 
        except: # div_child_class is not a key 
            self.titleImg_method_classes[url_base][div_child_class] = [1, len(images)] # initiate the number of pages to 1 and initiate the score.
        
        return [response.urljoin(x) for x in images]

    '''
    get the images inside the div elements that have class name = classe
    '''
    def getImgsByClassedDiv(self, response, classe):
        div_imgs = response.xpath("//div[@class = '" + classe + "']/descendant::img/@src").getall()
        return list({response.urljoin(x) for x in div_imgs})
        
        

        
    '''

    =============================================================================
                                    AIDE METHODS
    =============================================================================
    
    '''

    '''

    get the links presented in the page
    
    '''
    def getPageLinks(self, response):
        links = response.xpath(self.getXpathForLinks(response)).getall()
        links = {response.urljoin(x) for x in links} # get absolute url
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
    check if the url is a valid url, ie not image, pdf ... url
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

    """
    return true if the text is not empty, that it contains other caracters then the listed in emptyList
    """
    def textNotEmpty(self, x):
        emptyList = [" ", "\n", "\t", ".", ",", ";", "\r"]
        for y in emptyList:
            x = x.replace(y, "")
        return x != ""

    """
    extract the url that are in a list of string, in this code the list is a list of img tag.
    """
    def extractUrlFromImgs(self, imgs):
        links = set()
        for img in imgs:
            links = links.union(set(re.findall(r'(https?://\S+)', img)))
        links = {x[:-1] for x in links} # because they will cotains " at the end
        return links
