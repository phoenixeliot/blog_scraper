import nltk
nltk.download("popular")
# import spacy
# from spacy import displacy
# import tkinter

# Vocab list: https://stackoverflow.com/questions/29332851/what-does-nn-vbd-in-dt-nns-rb-means-in-nltk
parts_of_speech = {
    "CC": "Coordinating conjunction",
    "CD": "Cardinal number",
    "DT": "Determiner",
    "EX": "Existential there",
    "FW": "Foreign word",
    "IN": "Preposition or subordinating conjunction",
    "JJ": "Adjective",
    "VP": "Verb Phrase",
    "JJR": "Adjective, comparative",
    "JJS": "Adjective, superlative",
    "LS": "List item marker",
    "MD": "Modal",
    "NN": "Noun, singular or mass",
    "NNS": "Noun, plural",
    "PP": "Preposition Phrase",
    "NNP": "Proper noun, singular Phrase",
    "NNPS": "Proper noun, plural",
    "PDT": "Pre determiner",
    "POS": "Possessive ending",
    "PRP": "Personal/Possessive pronoun Phrase (which one?)",
    "RB": "Adverb",
    "RBR": "Adverb, comparative",
    "RBS": "Adverb, superlative",
    "RP": "Particle",
    "S": "Simple declarative clause",
    "SBAR": "Clause introduced by a (possibly empty) subordinating conjunction",
    "SBARQ": "Direct question introduced by a wh-word or a wh-phrase.",
    "SINV": "Inverted declarative sentence, i.e. one in which the subject follows the tensed verb or modal.",
    "SQ": "Inverted yes/no question, or main clause of a wh-question, following the wh-phrase in SBARQ.",
    "SYM": "Symbol",
    "VBD": "Verb, past tense",
    "VBG": "Verb, gerund or present participle",
    "VBN": "Verb, past participle",
    "VBP": "Verb, non-3rd person singular present",
    "VBZ": "Verb, 3rd person singular present",
    "WDT": "Wh-determiner",
    "WP": "(Possessive?) wh-pronoun",
    "WRB": "Wh-adverb",
}

# empty array#
contentArray = [
    "I favored the campus cops with my most wining Super Hero smile.",
]


def processContent():
    try:
        for item in contentArray:
            tokenized = nltk.word_tokenize(item)
            tagged = nltk.pos_tag(tokenized)
            
            verbose = []
            for tag_pair in tagged:
                new_tag = tag_pair[1]
                for pair in parts_of_speech.items():
                    [abbreviation, description] = pair
                    if (new_tag == abbreviation):
                        new_tag = new_tag.replace(abbreviation, description)
                        break
                verbose.append((tag_pair[0], new_tag))

            print(verbose)
                
            chunkGram = r"""Chunk: {<RB.?>*<VB.?>*<NNP>}"""
            chunkParser = nltk.RegexpParser(chunkGram)

            chunked = chunkParser.parse(tagged)
            print(chunked)
            # chunked.draw() # requires tkinter

            # https://towardsdatascience.com/visualizing-part-of-speech-tags-with-nltk-and-spacy-42056fcd777e
            # nlp = spacy.load("en_core_web_sm")
            # doc = nlp(text)
            # displacy.render(doc, style = "dep")


    except Exception as e:
        print(str(e))


processContent()

# from nltk.corpus import brown
# from nltk.tag import UnigramTagger
# tagger = UnigramTagger(brown.tagged_sents(categories='news')[:500])
# sent = ['Mitchell', 'decried', 'the', 'high', 'rate', 'of', 'unemployment']
# for word, tag in tagger.tag(sent):
#     print(word, '->', tag)
