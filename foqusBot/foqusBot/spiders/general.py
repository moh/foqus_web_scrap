# -*- coding: utf-8 -*-
import scrapy
import csv
from scrapy.http import Request
from urllib.parse import urlparse
# common_words contain words used frequently by websites
from foqusBot.common_words import common_words

# MIN_RATIO is the min ratio where the page is still identified as home or product page
MIN_RATIO = 0.05

class GeneralSpider(scrapy.Spider):
    name = 'generalFoqus'

    '''
    url_products: dict that have keys the base of the website, and value the link to a
    product page ( in the csv ) from this site

    url_classes : dict that have keys the base of the website, and value two lists, that
    represents the list of class of home page, and the list of class of product page

    
    '''
    def __init__(self, *a, **kw):
        super(GeneralSpider, self).__init__(*a, **kw)
        self.url_home_products = dict()
        self.url_classes = dict()
        self.visited_urls = set()
        self.resp_base = None

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

        self.url_classes[self.getUrlBase(response.url)] = [final_classes, set()]
        self.resp_base = response.url

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
    This method is to identify the nature of the page, wether it is a home page or product pages.

    JUST FOR TEST : it will return a dict describing the state of the page
    =============
    
    it will return a tuple (is_home, is_product)
    
    '''
    def identifyPage(self, response):
        home_classes, product_classes = self.url_classes[self.getUrlBase(response.url)]

        # get the classes presented in the page
        classes = response.xpath("//@class").getall()
        page_classes = set()

        for class_names in classes:
            page_classes = page_classes.union(set(class_names.split(" ")))

        # number of classes in common with home page
        home_shared = len(page_classes.intersection(home_classes))
        # number of classes in common with product page
        product_shared = len(page_classes.intersection(product_classes))

        ratio_home = home_shared / len(home_classes)
        ratio_product = product_shared / len(product_classes)

        is_home = ratio_home > ratio_product
        is_product = ratio_home < ratio_product

        # if the two ratio are smaller then MIN_RATIO, then the page is neither a product nor a home page
        if( (ratio_home < MIN_RATIO) and (ratio_product < MIN_RATIO)):
            is_home = is_product = False
        
        return({"url": response.url ,"ratio_home": ratio_home, "ratio_product": ratio_product,
                "is_home":is_home, "is_product":is_product})

    '''
    The default method that is called after yield a request to a page
    '''
    def parse(self, response):
        infos = self.identifyPage(response)
        yield infos

        links = self.getPageLinks(response)
        for link in links:
            self.visited_urls.add(link)
            yield Request(link)

    def parse_item(self, response):
        response = self.cleanResponse(response)
        
        # if this page is not a product page then yield request with callback = self.parse
        product = self.isProductPage(response)
        if not(product):
            yield scrapy.Request(response.url, self.parse)
            return
        
        l = ItemLoader(item = FoqusbotItem(), selector = product)
        l.add_css("price", ".price", MapCompose(remove_tags))
        l.add_css("title", ".product_title::text")
        l.add_css("category", ".posted_in a::text")
        l.add_xpath("image", "//*[contains(concat(' ',normalize-space(@class),' '),' top-content ')]//img/@src", TakeFirst())
        l.add_value("url", response.url)
        yield l.load_item()
        
        
        
    """
    ===========================================================
        This part is for identifying pages and filtering pages
    ===========================================================
    """

    """
    Clean the received response, it will remove the header and footer part of the repsonse,
    as most of the links in those two sections aren't related to products.
    """
    def cleanResponse(self, response):
        try:
            # remove header
            response.css("header")[0].remove()
            # remove Footer
            response.css("footer")[0].remove()
        except Exception as e:
            pass
        
        return response

    '''
    get the links presented in the page
    '''
    def getPageLinks(self, response):
        links = response.xpath(self.getXpathForLinks(response)).getall()
        links = {response.urljoin(x) for x in links if x not in self.visited_urls}
        return links

    
    """
    return the xpath query for all links with the condition to not contain the words in the common word list
    NOTE : links maybe relative so shouldn't check for base url before the join
    """
    def getXpathForLinks(self, response):
        xpath_query = "//a[contains(@href, '" + self.getUrlBase(response.url) + "')"
        for word in common_words:
            xpath_query += " and not(contains(@href,'" + word + "'))"

        xpath_query += "]/@href"
        return xpath_query

    """
    get the base link of the website, for example : www.google.com ---> google.com , mail.google.com --> google.com
    
    """
    def getUrlBase(self, url):
        base = urlparse(url).netloc
        base = ".".join(base.split(".")[-2:])
        return base
