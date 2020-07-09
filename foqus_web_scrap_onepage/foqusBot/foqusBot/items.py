# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class FoqusbotItem(Item):
    # primary fields
    image = Field()
    price = Field()
    title = Field()
    category = Field()

    # Houskeeping fields
    url = Field()
    project = Field()
    spider = Field()
    server = Field()
    date = Field()
