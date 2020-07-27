# -*- coding: utf-8 -*-
import os
import scrapy
from scrapy.http import Request
from scrapy import Selector
from scrapy import signals
from pydispatch import dispatcher
from urllib.parse import urlparse
from w3lib.html import remove_tags, remove_tags_with_content, remove_comments
import csv
import json
import re
import string
# common_words contain words used frequently by websites
from foqusBot.common_words import *

# MIN_RATIO is the min ratio where the page is still identified as home or product page
MIN_RATIO = 0.4

# the number of pages to learn from to extract wich method is used frequently, and wich class is detected in title div method ( for images)
LEARN_IMG_NB_PAGE = 30

class GeneralSpider(scrapy.Spider):
    name = 'generalFoqus'

    '''
    url_home_products: dict that have keys the base of the website, and value a list of links to the home page and product page.

    url_classes : dict that have keys the base of the website, and value two lists, that
    represents the list of class of home page, and the list of class of product page

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
        dispatcher.connect(self.spider_quit, signals.spider_closed)
        self.url_home_products = dict()
        self.url_classes = dict()
        self.methods_stat = dict()
        self.titleImg_method_classes = dict()
        self.order = 0
        self.getStoredData()

    '''

    update the spider attributes from previous scraping, if the file INFORESUME.json already exist 
    
    '''
    def getStoredData(self):
        try:
            with open("INFORESUME.json", "r") as f:
                print("\n !!!!!!!!!!!!!!!!!!!!!!!!!\n Getting data \n !!!!!!!!!!!!!!!!!!!!!!! \n")
                data = json.loads(f.read())
                self.url_home_products = data["url_home_products"]
                self.url_classes = data["url_classes"]
                self.methods_stat = data["methods_stat"]
                self.titleImg_method_classes = data["titleImg_method_classes"]
                self.order = data["order"]
                self.url_classes = {x : [set(y) for y in self.url_classes[x]] for x in self.url_classes}
        except FileNotFoundError:
            pass

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
        url_base = self.getUrlBase(response.url)
        final_classes = set()
        
        for class_names in classes:
            final_classes = final_classes.union(set(class_names.split(" ")))

        # this part to get the unique classes of home and product page
        homePageClasses = self.url_classes[url_base][0]
        product_classes = final_classes - homePageClasses
        home_classes = homePageClasses - final_classes

        self.url_classes[url_base] = [home_classes, product_classes]

        # initiate the method statistics to zeros
        self.methods_stat[url_base] = [0, 0]

        yield Request(response.url, dont_filter = True)
        
        home_links = [self.url_home_products[url_base][0]] + self.url_home_products[url_base][2:]
        # call the home pages to analyse links
        for link in home_links:
            yield Request(link, dont_filter = True)
        

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
        method, used_class = "", ""
        ids = response.xpath("//@id").getall() # get all the id in the document
        
        nb_pages, ratio_first_method = sum(self.methods_stat[url_base]), 0
        product_classes = [x for x in product_shared if self.shareWithList(x, product_identifiers)]
        product_classes = [x for x in product_classes if len(response.xpath('//*[contains(@class, "' + x + '")]')) == 1]
        
        
        image_classes = [x for x in product_classes if self.shareWithList(x, images_identifiers)]
        # get info classes with uniq associated div
        infos_classes = [x for x in product_shared if self.shareWithList(x, infos_identifiers)]
        infos_classes = [x for x in infos_classes if len(response.xpath('//*[contains(@class, "' + x + '")]')) == 1]
        infos_ids = [x for x in ids if self.shareWithList(x, infos_identifiers)]

        title_classes = [x for x in product_classes if self.shareWithList(x, title_identifiers)]
        prices_classes = [x for x in product_classes if self.shareWithList(x, prices_identifiers)]

        print("\n product shared = ", product_shared)
        print("\n infos classes = ", infos_classes)
        
        images = self.getImgsFromClasses(response ,image_classes) # get the images
        title = self.getTitle(response, title_classes).strip()
        infos = self.getAvailableInfos(response, infos_classes, ids) # get the infos by class and ids.
        
        price = self.getPriceFromClasses(response, prices_classes)

        if nb_pages != 0:
            ratio_first_method = self.methods_stat[url_base][0] / nb_pages
        
        # if ratio_first_method is less then half and the pages that we have tested are more then 10, then
        # we always do the second method
        if (len(images) <= 2 and nb_pages < LEARN_IMG_NB_PAGE) or (ratio_first_method < 0.5 and nb_pages >= LEARN_IMG_NB_PAGE):
            img_class = self.getImgFromTitleDiv(response)
            if len(img_class) == 0: return
            images, used_class = img_class
            self.methods_stat[url_base][1] += 1 # update number related to second method.
            method = "2"
        else:
            self.methods_stat[url_base][0] += 1 # update number related to first method.
            method = "1"

        try:
            stat = self.titleImg_method_classes[url_base]
        except:
            
            stat = {}
        return {"url" : response.url, "images" : images, "title" : title,
                "infos" : infos, "price" : price, "method" : method, "classe" : used_class}
        
    '''

    Return the images src URL that are descendant of a div that have the classes in the list.
    classes is a list of classe that have some specific words like product, image ...
    
    '''
    def getImgsFromClasses(self, response, classes):
        images = set()
        for classe in classes:
            imgs = set(response.xpath('//*[contains(concat(" " , @class, " "), " ' + classe + ' ")]')[0].xpath('descendant::img/@src').getall())
            images = images.union(imgs)

        # in some site, the url is not in a src attribute.
        if (len(images) == 0 and len(classes) != 0):
            for classe in classes:
                imgs = response.xpath('//*[contains(concat(" " , @class, " "), " ' + classe + ' ")]')[0].xpath("descendant::img").getall()
                images = images.union(self.extractUrlFromImgs(imgs))
            
        return [ response.urljoin(x) for x in images] # get the absolute urls

    '''
    
    Get the title of the product in the page.
    First we will try to get the title from the class name,
    if it is empty then we will return the first text inside h1 tag.
    
    '''
    def getTitle(self, response, classes):
        title_selectors, title_div_selectors = [], []
        title_datas = set()
        for classe in classes:
            title_selectors.extend(response.xpath('//*[contains(concat(" " , @class, " "), " ' + classe + ' ")]'))

        for selector in title_selectors:
            divs = selector.xpath("descendant::div[not(descendant::div)]")
            if len(divs) != 0:
                title_div_selectors.extend(divs)
            else:
                title_div_selectors.append(selector)
                
        for selector in title_div_selectors:
            t = selector.css("h1")
            if len(t) > 0: return remove_tags(t.get()) # if we find a h1 tag inside the title classes then we return its content directly
            
            title_datas.add(remove_tags(selector.get()))

        title_datas = {" ".join(x.strip().split()) for x in title_datas}
        title_datas = [x for x in title_datas if self.textNotEmpty(x)]
        if len(title_datas) > 0: # if we have collected data from classes then return the first one
            return title_datas[0]
        
        h1_title = response.css("h1") # usually title written in h1
        if len(h1_title) > 0:
            return remove_tags(h1_title.get())



    '''

    Function to get the available product informations in the page, it takes the classes that
    have the infos identifiers inside it from the classes and ids specific to product page.
    By using the method getParentSelector, we get the selectors where no one is the child of another one.
    We clean the html inside those selectors by removing script and style content, and remove some tags.
    Transform the resulted html text to scrapy selectors.
    Then we break those selectors into smaller divs selector and we extract those informations.
    
    '''

    def getAvailableInfos(self, response, classes, ids):
        texts_list, final_texts = [], set()
        div_children, new_selectors = [], []
        parents = self.getParentSelector(response, classes, ids)
        for div in parents:
            div_without = div.xpath("descendant::div[not(descendant::div)]")
            if len(div_without) != 0:
                div_children.extend(div_without) # select div that doesn't have a div descendant
            else:
                div_children.append(div)
        for div in div_children:
            text = div.get()
            # clean the texts
            text = remove_tags(text, which_ones = tags_remove)
            text = remove_comments(text)
            text = remove_tags_with_content(text, which_ones= tags_remove_content )
            # generate a selector from the cleaned text
            new_selectors.append(Selector(text = text))
        for selector in new_selectors:
            texts_list.append(selector.xpath("descendant::text()").getall())
        for txt in texts_list: # type(txt) = list
            cleaned_text = [" ".join(x.strip().split()) for x in txt]
            cleaned_text = [x for x in cleaned_text if self.textNotEmpty(x)]
            if len(cleaned_text) != 0:
                final_texts.add(tuple(cleaned_text))
            
        return final_texts

        

    '''

    Get the prices from the element that have specific class name 

    '''
    def getPriceFromClasses(self, response, classes):
        price_selectors, price_div_selectors = [], []
        price_datas = set()
        for classe in classes:
            price_selectors.extend(response.xpath('//*[contains(concat(" " , @class, " "), " ' + classe + ' ")]'))

        for selector in price_selectors:
            divs = selector.xpath("descendant::div[not(descendant::div)]")
            if len(divs) != 0:
                price_div_selectors.extend(divs)
            else:
                price_div_selectors.append(selector)

        for selector in price_div_selectors:
            price_datas.add(remove_tags(selector.get()))
        price_datas = {" ".join(x.strip().split()) for x in price_datas}
        price_datas = [x for x in price_datas if (self.textNotEmpty(x) and self.isValidPrice(x))]
        return price_datas

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
            if len(stat_dict) == 0: # if the dict is empty then raise error and exit the try
                raise KeyError
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
                    if selected_class != None:
                        imgs = self.getImgsByClassedDiv(response, selected_class)
                    else:
                        imgs = self.getImgsByClassedDiv(response, selected_class,
                                                        self.titleImg_method_classes[url_base][selected_class][2])
                    if len(imgs) > 0:
                        self.titleImg_method_classes[url_base][selected_class][0] += 1
                        self.titleImg_method_classes[url_base][selected_class][1] += len(imgs) # update the score 
                        return (imgs, selected_class)
                    
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
        if div_child == None:
            return []
        images = set(div_child.xpath("descendant::img/@src").getall()) # get the src of images inside the div_child tag

        div_child_class = div_child.xpath("@class").get()
        div_child_id = div_child.xpath("@id").get()
        try:
            self.titleImg_method_classes[url_base][div_child_class][0] += 1
            self.titleImg_method_classes[url_base][div_child_class][1] += len(images) # update the score
            if div_child_class == None:
                self.titleImg_method_classes[url_base][div_child_class][2].add(div_child_id)
        except: # div_child_class is not a key 
            if div_child_class == None:
                self.titleImg_method_classes[url_base][div_child_class] = [1, len(images), set()] # initiate the number of pages to 1 and initiate the score.
            else:
                self.titleImg_method_classes[url_base][div_child_class] = [1, len(images)]
        
        return ([response.urljoin(x) for x in images], div_child_class)

    '''
    get the images inside the div elements that have class name = classe
    if classe = None then we try to get the div by the id that we have collected

    Also if no div have excatly the same class names, we split the classe into the css classes ( we split by space ), and seach for unique div that have those classes, then we get the imgs.
    '''
    def getImgsByClassedDiv(self, response, classe, ids = set()):
        div_imgs = []
        final_classes = set()
        if classe != None:
            div_imgs = response.xpath("//div[@class = '" + classe + "']/descendant::img/@src").getall() # get the div that has exactly the same class name, it may contain space ( so many css class )
            if div_imgs == 0: # if no div found with exactly same classes name, we break it into many class names ( split " ")
                for class_names in classe:
                    final_classes = final_classes.union(set(class_names.split(" ")))
                final_div = {response.xpath('//*[contains(@class, "'+x+'")]')[0] for x in final_classes if len(response.xpath('//*[contains(@class, "'+x+'")]')) == 1} # get only the div that have unique class
                for div in final_div:
                    div_imgs.extend(div.xpath("descendant::img/@src")) # get the imgs inside the selected divs

        else: # if the classe is none then we get the images by id 
            for one_id in ids:
                if one_id != None:
                    div_imgs.extend(response.xpath("//div[@id = '" + one_id + "']/descendant::img/@src").getall())
        return list({response.urljoin(x) for x in div_imgs})
        
        
        
    '''

    =============================================================================
                                    AIDE METHODS
    =============================================================================
    
    '''

    '''

    Get the selectors that doesn't share childrens from the tag that contains the classes.
    Also we will extract the informations using the id.

    for part (1), the parameter classes is a list of class names that are resulted from splitting the whole class name by
    space, when we search for elements that contains those class names, we may get many same element, but they are represented
    as different selector, for example if classes = ['a', 'b'], and we have a div : <div class = 'a b' >
    then we will have these div two times, one for a and another for b, so the part (1) is to make a uniq list of selectors,
    if it is not uniq the method will consider this element to be its own child.
    we have added the if statement "if x != None" because we may have a div with id and no classes.
    
    '''
    def getParentSelector(self, response, classes, ids):
        selectors, parents = [], []
        selector_data, data = [], []
        for classe in classes:
            selectors.extend(response.xpath('//*[contains(concat(" " , @class, " "), " ' + classe + ' ")]'))

        for ide in ids:
            selectors.extend(response.xpath("//*[@id = '" + ide + "']")) # select by id
        # explenation of this part in method documentation (1)
        classes_selectors = {x.xpath("@class").get() for x in selectors} # get the set of classes classe, we may get None for div with id and no classes
        selectors = [response.xpath("//*[@class = '" + x + "']")[0] for x in classes_selectors if x != None] # get uniq selectors
        ##
        for select in selectors:
            selector_data.append((select, select.get()))
        data = [x[1] for x in selector_data]

        for i1 in range(len(selector_data)):
            not_child = True
            for i2 in range(len(data)):
                if (i1 != i2) and (data[i1] in data[i2]):
                    not_child = False # this selector is a child of some selector in the list
            if not_child:
                parents.append(selector_data[i1][0])
        return parents
    

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
        filtered_links = set()
        for img in imgs:
            links = links.union(set(re.findall(r'(https?://\S+)', img)))
        for x in links:
            if x[-1] in ["'", '"']:
                filtered_links.add(x[:-1])
            else:
                filtered_links.add(x)
        return filtered_links

    """

    Check that the price is valid, doesn't contain letters.

    """
    def isValidPrice(self, price):
        for x in string.ascii_letters:
            if x in price:
                return False
        return True

    """

    METHOD to be called when the spider will close
    
    """
    def spider_quit(self, spider):
        url_classes = {x : [list(y) for y in self.url_classes[x]] for x in self.url_classes }
        data = {"url_home_products":self.url_home_products, "url_classes" : url_classes,
                "methods_stat":self.methods_stat,
                "titleImg_method_classes": self.titleImg_method_classes, "order":self.order}
        print("\n ^^^^^^^^^^^^^^ \n STORING TO FILE \n ^^^^^^^^^^^^^^ \n")
        print("data = ", data)
        with open("INFORESUME.json", "w") as f:
            json.dump(data, f)
        print("\n ^^^^^^^^^^^^^^ \n DATA STORED, CLOSE SPIDER  \n ^^^^^^^^^^^^^^^ \n")
