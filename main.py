from dataclasses import dataclass
from distutils.command.upload import upload
from enum import unique
from typing import Collection, List
import sys
import requests
import json
from bs4 import BeautifulSoup, PageElement

ANKI_URL = 'http://localhost:8765'
NOTE_MODEL_NAME = 'Kanji'

@dataclass
class KanjiDetails:
    kanji: str
    meanings: List[str]
    kunyomi_readings: List[str]
    onyomi_readings: List[str]
    
def get_jisho_url(characters: str) -> str:
    return f'https://jisho.org/search/{characters}20%23kanji'

def get_meanings(html: PageElement) -> List[str]:
    container = html.find_next('div', { 'class': 'kanji-details__main-meanings' })
    meanings = container.text.strip().split(', ')
    return meanings

def get_onyomi_readings(html: PageElement) -> List[str]:
    readings_section = html.find_next('div', { 'class': 'kanji-details__main-readings' })
    container = readings_section.find_next('dl', { 'class': 'on_yomi' })
    list = container.find_next('dd', { 'class': 'kanji-details__main-readings-list' })
    readings = list.text.strip().split(', ')
    return readings

def get_kunyomi_readings(html: PageElement) -> List[str]:
    readings_section = html.find_next('div', { 'class': 'kanji-details__main-readings' })
    container = readings_section.find_next('dl', { 'class': 'kun_yomi' })
    list = container.find_next('dd', { 'class': 'kanji-details__main-readings-list' })
    readings = list.text.strip().split(', ')
    return readings

def extract_individual_character_from_html(html: PageElement) -> KanjiDetails:
    kanji_element = html.find_next('h1', { 'class': 'character'})
    kanji = kanji_element.text

    meanings = get_meanings(html)
    kunyomi  = get_kunyomi_readings(html)
    onyomi   = get_onyomi_readings(html)

    return KanjiDetails(kanji, meanings, kunyomi, onyomi)

def extract_character_info_from_html(html: str) -> List[KanjiDetails]:
    soup = BeautifulSoup(html, features = 'html.parser')

    results_list = soup.find(id = 'result_area')
    kanji_details = []
    
    for child in results_list.children:
        if child.name == 'div':
            kanji_details.append(extract_individual_character_from_html(child))

    return kanji_details

def query_jisho_for_characters(characters: Collection[str]) -> List[KanjiDetails]:
    character_string = ''.join(characters)

    print(f'Querying Jisho for characters: {character_string}')

    jisho_url = get_jisho_url(character_string)
    try:
        response = requests.get(jisho_url)
        return extract_character_info_from_html(response.content)
    except ConnectionError as e:    
        print(f'Failed to GET {jisho_url}')
    
def process_file(filename: str) -> List[KanjiDetails]:
    unique_chars = set()

    for line in lines:
        stripped_line = line.strip().replace(' ', '')
        for char in stripped_line:
            unique_chars.add(char)

    return query_jisho_for_characters(unique_chars)

def create_ankiconnect_request(action: str, **params) -> str:
    return json.dumps({ 
        'action':  action,
        'params':  params,
        'version': 6
    }).encode('utf-8')

def invoke(action: str, **params) -> object:
    request = create_ankiconnect_request(action, **params)
    response = requests.post(ANKI_URL, request)
    
    if response.status_code != 200:
        print(f'Failed to communicate with Anki Connect. Error code {response.status_code}')
    else:
        return json.loads(response.content)['result']

def check_deck_exists(deck: str) -> bool:
    decks = invoke('deckNames')
    return deck in decks

def convert_kanji_to_note(kanji: KanjiDetails, deck_name: str) -> object:
    return {
        'deckName': deck_name,
        'modelName': NOTE_MODEL_NAME,
        'fields': {
            'Kanji':            kanji.kanji,
            'Meanings':         ', '.join(kanji.meanings),
            'Kunyomi Readings': ', '.join(kanji.kunyomi_readings),
            'Onyomi Readings':  ', '.join(kanji.onyomi_readings)
        }
    }

def upload_kanji(kanji: List[KanjiDetails], deck_name: str):
    notes = list(map(lambda note: convert_kanji_to_note(note, deck_name), kanji))

    can_add_notes = invoke('canAddNotes', notes = notes)

    notes = filter(
        lambda x: x[1],
        zip(notes, can_add_notes)
    )

    notes = list(map(
        lambda x: x[0],
        notes
    ))

    num_added = len(list(filter(
        lambda x: x,
        can_add_notes
    )))

    num_skipped = len(list(filter(
        lambda x: not x,
        can_add_notes
    )))

    invoke('addNotes', notes = notes)

    print(f'Added {num_added} notes to {deck_name}. Skipped {num_skipped} notes.')

args = sys.argv

if len(args) < 2:
    print('Requires a target deck.')
    exit(1)

if len(args) < 3:
    print('Requires input files.')
    exit(1)

target_deck = args[1]

if not check_deck_exists(target_deck):
    print('Target deck does not exist.')
    exit(1)

files = args[2:]
print_skip_for_single_input = lambda x: print(f'{x} not found. Exiting.')
print_skip_for_multi_input = lambda x: print(f'{x} not found. Skipping.')
error_message_fn = print_skip_for_single_input if len(files) == 1 else print_skip_for_multi_input

files_processed = 0

for file in files:
    try:
        with open(file, 'r', encoding = 'utf-8') as lines:
            kanji_details = process_file(file)
            upload_kanji(kanji_details, target_deck)
            
            files_processed = files_processed + 1
    except OSError as e:
        error_message_fn(file)

if files_processed > 0:
    print(f'Finished. {files_processed} files processed.')
