import argparse
import os
import genanki
import googletrans
import re
import random
from nltk.tokenize import sent_tokenize, word_tokenize
import pysrt
import nltk

# Probably 'all' is not needed here. But it wil ldefinitely download everything whats needed
nltk.download('all')

def import_str(x):
    text_list = []
    subs = pysrt.open(x)
    for sub in subs:
        b_text = sub.text
        splitted_text = b_text.split("\n")
        s_texts = []
        for i in splitted_text:
            s_texts.append(re.sub(r'—', "-", re.sub(r'^[—\-]*', "", i)))
        text_list.append(" ".join(s_texts))
    return " ".join(text_list)


translate_to = None
translate_from = None
translator = googletrans.Translator()


def translate(original_text):
    return translator.translate(original_text, dest=translate_to, src=translate_from).text


words_counter = 0
sentence_counter = 0


class Word:
    def __init__(self, word):
        self.word = word


rr = re.compile(r'\w*')


class Sentence:
    def __init__(self, sentence):
        global words_counter
        self.sentence = sentence.strip()
        while self.sentence[-1] in ".,;:-_'*¨~!\"#¤%&/()=?`@£$€{[]}\\+´":
            self.sentence = self.sentence[0:-1]
        self.translation = translate(self.sentence)
        self.words = list(map(lambda x: Word(x.lower()), word_tokenize(self.sentence)))
        words_counter += len(self.words)
        # print(f'{len(self.words)} words in sentence')

    def get_words(self):
        words_to_return = {}
        for word in self.words:

            if rr.match(word.word) and word.word not in words_to_return:
                words_to_return[word.word] = {"word": word.word,
                                              "translation": "",
                                              "sentences": [
                                                  {"sentence": self.sentence, "translation": self.translation}]}
        return words_to_return


class Text:
    def __init__(self, original_text):
        self.text = original_text.replace("\n", " ").replace("\t", " ").replace("\r", " ").replace("  ", " ")
        self.sentences = list(map(lambda x: Sentence(x), sent_tokenize(self.text)))
        print(f'{len(self.sentences)} sentences and {words_counter} words in total')
        self.all_the_words = {}

        for sentence in self.sentences:
            for word, stuff in sentence.get_words().items():
                if word not in self.all_the_words:
                    self.all_the_words[word] = stuff
                    self.all_the_words[word]['translation'] = translate(self.all_the_words[word]['word'])
                    self.all_the_words[word]['sentences'] = {
                        self.all_the_words[word]['sentences'][0]['sentence']: self.all_the_words[word]['sentences'][0]}
                else:
                    if stuff["sentences"][0]['sentence'] not in self.all_the_words[word]['sentences']:
                        self.all_the_words[word]['sentences'][stuff["sentences"][0]['sentence']] = stuff["sentences"][0]

    def get_words(self):
        return self.all_the_words


class AnkiCards:
    def __init__(self, name):
        self.name = name
        self.notes = []
        self.my_model = genanki.Model(
            1,
            self.name,
            fields=[
                {'name': 'Question'},
                {'name': 'Answer'},
                {'name': 'Sentence'},
                {'name': 'SentenceTranslation'},
            ],
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': '<center><font size=60>{{Question}}',
                    'afmt': '{{FrontSide}}<hr id="answer"><b>{{Answer}}</b>'
                            '<br>Example:<br>{{Sentence}}<br><br>Translation:<br>{{SentenceTranslation}}',
                },
            ])
        self.my_deck = genanki.Deck(980765, self.name)

    def add_words(self, words):
        for word in words:
            self.add_word(words[word])

    def add_word(self, word):
        sentence = random.choice(list(word['sentences'].values()))
        word_options = [word["word"], word["word"].upper(), word['word'].capitalize()]

        def replace_options(word_to_replace):
            if word_to_replace in word_options:
                return f'<b>{word_to_replace}</b>'
            return word_to_replace

        splitted_sentence = list(map(replace_options, sentence['sentence'].split()))
        original_sentence = " ".join(splitted_sentence)
        # print(original_sentence)
        my_note = genanki.Note(
            model=self.my_model,
            fields=[word['word'], word['translation'], original_sentence, sentence['translation']]
        )
        self.notes.append(my_note)

    def generate_package(self, output):
        random.shuffle(self.notes)
        for note in self.notes:
            self.my_deck.add_note(note)
        genanki.Package(self.my_deck).write_to_file(output)


if __name__ == "__main__":
    argumenter = argparse.ArgumentParser(prog='Parse to anki',
                                         description='This stuff will parse your srt/text to anki cards')
    group = argumenter.add_mutually_exclusive_group(required=True)
    group.add_argument("--srt_file", default=None, help="if this one is used then it will be parsed as SRT file")
    group.add_argument("--text_file", help="if this one is used then it will be parsed as generic text file")
    argumenter.add_argument("--src_lng", default="sv")
    argumenter.add_argument("--dst_lng", default="en")
    argumenter.add_argument("--name", help="project name")
    argumenter.add_argument("--output",
                            default=os.path.dirname(__file__),
                            help="folder to output anki file to. "
                                 "The name will be PROJECT_NAME.apkg "
                                 "(Project name can be set with --project_name flag) "
                                 f"Default: {os.path.dirname(__file__)}")
    args = argumenter.parse_args()
    translate_from = args.src_lng
    translate_to = args.dst_lng
    text = ""
    if args.srt_file:
        text = import_str(args.srt_file)
    elif args.text_file:
        with open(args.text_file, 'r') as r:
            text = r.read()
    text = Text(text)
    ankiCards1 = AnkiCards(args.name)
    ankiCards1.add_words(text.get_words())
    ankiCards1.generate_package(os.path.join(args.output, f'{args.name}.apkg'))
