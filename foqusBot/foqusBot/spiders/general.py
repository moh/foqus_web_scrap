# -*- coding: utf-8 -*-
import scrapy
from foqusBot.items import FoqusbotItem
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from scrapy.loader.processors import TakeFirst, MapCompose
from urllib.parse import urlparse

class GeneralSpider(scrapy.Spider):
    name = 'generalFoqus'
    #allowed_domains = ['tryn.fit/']
    start_urls = ['https://tryn.fit/']

    # a list that contain common words used in links that are always related to site not product, ex : contact ...
    common_words = ["contact", "faq", "wishlist", "wish_list", "my-account", "login", "sign", "subscribe",
                    "privacy", "policy", "customer-service", "product-support", "terms-conditions", "about-us", "setting"]

    def __init__(self, *a, **kw):
        super(BasicSpider, self).__init__(*a, **kw)
        self.visited_urls = set()
        self.item_links = set()
        self.page_links = set()

    def parse_item(self, response):
        response = self.cleanResponse(response)
        
        # if this page is not a product page then yield request with callback = self.parse
        product = self.isProductPage(response)
        if not(product):
            yield scrapy.Request(response.url, self.parse)
            return
        
        l = ItemLoader(item = TestScrapyItem(), selector = product)
        l.add_css("price", ".price", MapCompose(remove_tags))
        l.add_css("title", ".product_title::text")
        l.add_css("category", ".posted_in a::text")
        l.add_xpath("image", "//*[contains(concat(' ',normalize-space(@class),' '),' top-content ')]//img/@src", TakeFirst())
        l.add_value("url", response.url)
        yield l.load_item()
        
        

    def parse(self, response):
        # remove header and footer
        response = self.cleanResponse(response)
        
        product_links = self.getProductLinks(response)
        pages_links = self.getPageLinks(response)
        
        for x in pages_links:
            self.visited_urls.add(x)
            yield scrapy.Request(x, callback = self.parse)

        for x in product_links:
            self.visited_urls.add(x)
            yield scrapy.Request(x, callback = self.parse_item)
        
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


    """
    Extract product links from the response
    First Method :
        Extract all links that have an img as a child
    
    """
    def getProductLinks(self, response):
        links = response.xpath("//a[img]/@href").getall()
        links = {response.urljoin(x) for x in links if x not in self.visited_urls}
        self.item_links = links
        return links


    """
    Extract links to other pages
    First Method:
        Extract all links then eliminate the item_links
        NOTE : item_links should be called before this function
    """
    def getPageLinks(self, response):
        links = response.xpath(self.getXpathForLinks(response)).getall()
        links = {response.urljoin(x) for x in links if x not in self.visited_urls}
        links = links - self.item_links
        self.page_links = links
        return links

    """
    identify if the page is a product page, ie it displays the information about the products

    First Method :
        Method that will work only on tryn.fit website, it checks if top-content class exists
        
    """
    def isProductPage(self, response):
        product = response.css(".top-content")
        if(len(product) >= 1):
            return product[0]
        return False


    """
    return the xpath query for all links with the condition to not contain the words in the common word list
    NOTE : links maybe relative so shouldn't check for base url before the join
    """
    def getXpathForLinks(self, response):
        xpath_query = "//a[contains(@href, '" + self.getUrlBase(response) + "')"
        for word in self.common_words:
            xpath_query += " and not(contains(@href,'" + word + "'))"

        xpath_query += "]/@href"
        return xpath_query

    """
    get the base link of the website, for example : www.google.com ---> google.com , mail.google.com --> google.com
    
    """
    def getUrlBase(self, response):
        base = urlparse(response.url).netloc
        base = ".".join(base.split(".")[-2:])
        return base
