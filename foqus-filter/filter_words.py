"""

This file contains list of words and symbols that we will replace, and some
functions to filter the data.

"""

import unidecode
# spacy library to lemitize the words
#import spacy

# List of stopwords in english and french language

STOPWORDS = {'only', 'juste', 'ni', 'itself', 'who', 'au', 'until', 'mon', 'mais', 'through',
 'tres', 'quand', 'vu', 'il', 'tous', 'avoir', 'about', 'me', 'own', 'ses',
 'cannot', 'you', 'for', 'hers', 'chaque', 'him', 'if', 'aucuns', 'ton', 'off',
 'been', 'ce', 'son', 'an', 'leur', 'does', 'fois', 'moins', 'du', 'before',
 'ours', 'ourselves', 'avec', 'peu', 'a', 'fait', 'notre', 'did', 'his', 'theirs',
 'encore', 'was', 'under', 'our', 'i', 'this', 'do', 'most', 'why', 'eu', 'during',
 'of', 'quel', 'your', 'par', 'sous', 'pour', 'myself', 'her', 'dans', 'nor', 'on',
 'few', 'sur', 'themselves', 'are', 'as', 'both', 'vous', 'je', 'tu', 'meme',
 'dos', 'comme', 'below', 'there', 'we', 'ici', 'faites', 'alors', 'votre',
 'other', 'bon', 'too', 'with', 'them', 'etions', 'qui', 'down', 'ought',
 'avant', 'is', 'some', 'peut', 'from', 'such', 'sans', 'vont', 'their',
 'they', 'la', 'les', 'sont', 'then', 'dehors', 'between', 'very', 'after',
 'he', 'it', 'parce', 'into', 'dedans', 'the', 'en', 'font', 'when', 'sa',
 'sujet', 'tels', 'nommes', 'hors', 'trop', 'once', 'has', 'cela', 'autre',
 'at', 'ta', 'up', 'having', 'voient', 'yours', 'to', 'quelle', 'by', 'ci',
 'had', 'further', 'against', 'any', 'etre', 'while', 'than', 'no', 'where',
 'le', 'whom', 'essai', 'that', 'here', 'aussi', 'que', 'des', 'ou', 'si',
 'mes', 'again', 'tes', 'but', 'nous', 'out', 'she', 'all', 'quels', 'ca',
 'est', 'tandis', 'am', 'et', 'more', 'yourselves', 'plupart', 'depuis', 'be',
 'because', 'elle', 'mot', 'quelles', 'those', 'so', 'how', 'what', 'ces',
 'donc', 'etaient', 'above', 'soyez', 'ete', 'pas', 'mien', 'being', 'car',
 'could', 'same', 'or', 'himself', 'should', 'have', 'tellement', 'would',
 'ceux', 'doit', 'debut', 'ma', 'over', 'were', 'yourself', 'pourquoi',
 'its', 'sien', 'ils', 'these', 'seulement', 'tout', 'etat', 'my',
 'comment', 'and', 'which', 'maintenant', 'herself', 'doing', 'each', 'not',
 'elles', 'in', 'devrait', 'de', 'toute', 'toutes', 'plus', 'une', 'un'}


EXTRAWORDS = {'numero', 'article', 'produit', 'product','couleur', 'color', 'without'
              'system', 'taille' , 'code' , 'prix', 'promo', 'eur', 'EUR', 'ttc'}


PUNCTUATIONS = '!"#$%&\'()*+,./:;<=>?@[\\]^_`{|}~€£'

# load the french language,
# till now we suppose that all text is in french
#NLP = spacy.load("fr_core_news_md")

LIMIT_WORD_LEN = 3


ALLREMOVE = STOPWORDS.union(EXTRAWORDS)


## ------------------------------------
# Test class words

CLASSWORDS = {'bijoux': ['oreille', 'boucle', 'collier', 'chaine', 'creole'],
 'blazer': ['blazer'],
 'body': ['body', 'dentelle', 'bretelle', 'bodysuit'],
 'bonnet': ['bonnet', 'chapeau', 'bandeau'],
 'ceinture': ['ceinture', 'belt'],
 'chaussette': ['chaussette', 'socquette'],
 'chaussures': ['sandale', 'sandal'],
 'chemisier': ['chemise', 'manche'],
 'combinaison': ['combinaison'],
 'echarpe': ['echarpe', 'scarf'],
 'gilet': ['gilet', 'cardigan', 'maille'],
 'jean': ['jean', 'skinny', 'mi-haute'],
 'jupe': ['jupe', 'mini-jupe'],
 'legging': ['pantalon', 'jupe-culotte'],
 'lingerie': ['dentelle', 'soutien-gorge', 'body', 'bretelle'],
 'maillot': ['bikini', 'maillot', 'bain'],
 'pull': ['pull', 'pullover', 'cotele'],
 'robe': ['robe', 'robe-chemise'],
 'sac': ['sac', 'bandouliere'],
 'short': ['short', 'short'],
 't-shirt': ['t-shirt', 'top'],
 'top': ['top', 'blouse', 'debardeur'],
 'veste': ['veste']}

## ------------------------------------

'''

This function takes a list of words, and return a list without the STOPWORDS,
numeric words and words of length less then 3.

'''
def removeFromList(lst):
    # NLP(x)[0] to lemitize the words 
    return [x for x in lst if ((x not in ALLREMOVE) and not(x.isnumeric()) and len(x) >= LIMIT_WORD_LEN )]


'''

This function take a string as a parameter and replace the punctuations symbols
by a space.

'''
def removePunctuations(word):
    for sym in PUNCTUATIONS:
        word = word.replace(sym, " ")
    return word


'''

This function take a string as parameter, and replace the letters with accent by
letter without accent.

'''
def replaceAccent(word):
    return unidecode.unidecode(word)


def cleanStr(phrase):
    lst = phrase.split()
    lst = removeFromList(lst)
    return " ".join(lst)

