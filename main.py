import sys
import requests
from bs4 import BeautifulSoup, PageElement
    
def get_jisho_url(characters: str) -> str:
    return f'https://jisho.org/search/{characters}20%23kanji'

def extract_individual_character_from_html(html: PageElement):
    kanji_element = html.find_next('h1', { 'class': 'character'})
    kanji = kanji_element.text

    meanings_element = html.find_next('div', { 'class': 'kanji-details__main-meanings' })
    meanings = meanings_element.text.strip().split(', ')
    print(meanings)

def extract_character_info_from_html(html: str):
    soup = BeautifulSoup(html, features = 'html.parser')

    results_list = soup.find(id = 'result_area')
    
    for child in results_list.children:
        if child.name == 'div':
            extract_individual_character_from_html(child)

def get_character_info(characters: str):
    print(f'Querying Jisho for characters: {characters}')

    jisho_url = get_jisho_url(characters)
    try:
        response = requests.get(jisho_url)
        extract_character_info_from_html(response.content)
    except ConnectionError as e:    
        print(f'Failed to GET {jisho_url}')
    
def process_file(filename: str):
    unique_chars = set()

    for line in lines:
        stripped_line = line.strip().replace(' ', '')
        for char in stripped_line:
            unique_chars.add(char)

    get_character_info(''.join(unique_chars))

args = sys.argv

if len(args) < 2:
    print('Requires input files.')
    exit(1)

files = args[1:]
print_skip_for_single_input = lambda x: print(f'{x} not found. Exiting.')
print_skip_for_multi_input = lambda x: print(f'{x} not found. Skipping.')
error_message_fn = print_skip_for_single_input if len(files) == 1 else print_skip_for_multi_input

files_processed = 0

for file in files:
    try:
        with open(file, 'r', encoding = 'utf-8') as lines:
            process_file(file)
            
            files_processed = files_processed + 1
    except OSError as e:
        error_message_fn(file)

if files_processed > 0:
    print(f'Finished. {files_processed} files processed.')
