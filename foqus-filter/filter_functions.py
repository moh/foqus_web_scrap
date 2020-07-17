'''

GENERAL INFOMRATION:
====================

This file will only contains the functions to clean the images of each website,
the function will take the url in parameter and change it to get a url of large image.

imageFilter is a dictionary that link the urlBase with its specific function.
It always should have the key '*', wich will be used as default function
if the urlBase is not written.

'''


# default function for websites
def default_clean(url):
    return url


# clean function for lapiscine
def lapiscine_clean(url):
    l = url.split("/")
    l[-2] = l[-2].replace("small", "large")
    l[-2] = l[-2].replace("medium", "large")
    # if large is not in the url even after replace, then return false
    if "large" not in l[-2]:
        return False
    return "/".join(l)


def basalt_clean(url):
    try:
        l = url.split("_")
        t = l[-1].split("x")
        t[0] = "250"
        l[-1] = "x".join(t)
        return "_".join(l)
    except:
        return url



imageFilter = {"*" : default_clean, "lapiscine-paris.fr" : lapiscine_clean,
               "jadium.fr" : lapiscine_clean, "basalt.fr" : basalt_clean}
