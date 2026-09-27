def parse_sanitarium(url):

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from bs4 import BeautifulSoup
    import pandas as pd

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=options)

    driver.get("https://wrecx.github.io/tms/")

    # Wait up to 3 seconds for the table body to be present in the DOM
    wait = WebDriverWait(driver, 3)
    table = wait.until(EC.presence_of_element_located((By.ID, "modsTable")))

    # Once the table is loaded, grab the rows
    entries = table.find_elements(By.TAG_NAME, "tr")
    data = []
    for entry in entries:
        # Extract text from each cell (td)
        cols = entry.find_elements(By.TAG_NAME, "td")
        row = []
        for col in cols:
            if col.text=='Download':
                temp = col.get_attribute('outerHTML')
                row.append(BeautifulSoup(temp, 'html.parser').a.attrs['href'])
            else:
                row.append(col.text)
        data.append(row)

    driver.quit()
    return pd.DataFrame(data, columns=['0', '1', 'title',	'author', 'released', 'type', 'url']).drop(labels=['0', '1'], axis=1)[1:]

def name_formatter(string, return_nickname=False):
    string = string.replace('-', ' ')
    string = string. replace('_', ' ')
    string = string.replace('(', ' (')
    string = string.replace(')', ') ')
    name_parts = string.split(sep=' ')
    if return_nickname:
        try:
            for part in name_parts:
                if ('(' in part and ')' in part) or ('"' in part):
                    return part[1:-1].lower()
            return None
        except:
            return None
    result = ''
    try:
        for part in name_parts:
            if not (('(' in part and ')' in part) or ('"' in part)):
                result = result + part.lower()
        return result
    except:
        return None

def get_nickname(string):
    return name_formatter(string, return_nickname=True)  

def get_moddb_data(url, wait_time):
    if 'moddb' in url:

        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        try:
            download_url = driver.find_element(By.ID, 'downloadmirrorstoggle').get_attribute('href')
        except:
            download_url = None
        try:
            size = driver.find_element(By.CLASS_NAME, 'buttoncount').text
        except:
            size = None
        try:
            moddb_downloads = driver.find_elements(By.CLASS_NAME, 'thickbox')[0].text.split()[0]
        except:
            moddb_downloads = None
        driver.quit()
        return (download_url, size, moddb_downloads)
    else:
        return (None, None, None)  

def parse_urls_to_csv_vectorized(urls, csv_file_path, header=None, parsing_func=get_moddb_data, columns_num=3, wait_time=None):
    import time
    from concurrent.futures import ThreadPoolExecutor
    import pandas as pd
    def worker_task(url):
        parsing_results = parsing_func(url, wait_time)
        row_elements = [str(url)] + [str(parsing_results[i]) for i in range(columns_num)]
        return ";".join(row_elements) + "\n"
    with open(csv_file_path, mode='a', newline='', encoding='utf-8') as f:
        if header is not None:
            f.write(header + "\n")   
        with ThreadPoolExecutor(max_workers=10) as executor:
            for csv_row in executor.map(worker_task, urls):
                f.write(csv_row)
                
    return None

def analyse_mod_archive(name, storage_dir):

    import os
    import py7zr
    import zipfile
    import rarfile
    import tempfile

    try:
        file_found = False
        for extension in ['.zip', '.rar', '.7z']:
            archive_path = os.path.join(storage_dir, name + extension)
            if os.path.exists(archive_path):
                file_found = True
                break
                
        if not file_found:
            raise FileNotFoundError

        archive_size_mb = round(os.path.getsize(archive_path) / 1048576, 2)

        with tempfile.TemporaryDirectory() as extract_dir:       
            try:
                with rarfile.RarFile(archive_path, 'r') as rar_ref:
                    rar_ref.extractall(extract_dir)
                                    
            except:
                try:
                    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                except:
                    with py7zr.SevenZipFile(archive_path, mode='r') as sz_ref:
                        sz_ref.extractall(extract_dir)

            extract_size_mb = round(get_dir_size(extract_dir) / 1048576, 2)

            map_count = 0
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith('.map'):
                        map_count += 1

            description = get_custom_story_description(extract_dir)
            ingame_text_lines = count_ingame_text_lines(extract_dir)
            has_title_screen = has_title_image(extract_dir)
            custom_models = list_custom_models(extract_dir)
            custom_sounds = list_custom_sounds(extract_dir)
                    
            return (archive_size_mb, extract_size_mb, map_count, description, 
                    ingame_text_lines, has_title_screen, custom_models, custom_sounds)
                    
    except Exception as e:
        print(f"An error occurred: {e}")
        return (None, None, None, None, None, None, None, None)
    
def parse_titles_to_csv_vectorized(titles, csv_file_path, header=None, parsing_func=analyse_mod_archive, columns_num=8, storage_dir=None):

    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with open(csv_file_path, mode='a', newline='', encoding='utf-8') as f:
        if header is not None:
            f.write(header + "\n")   
            
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks to the executor
            future_to_title = {executor.submit(parsing_func, title, storage_dir): title for title in titles}
            
            # Process tasks as soon as they complete
            for future in as_completed(future_to_title):
                title = future_to_title[future]
                try:
                    parsing_results = future.result()
                    row_elements = [str(title)] + [str(parsing_results[i]) for i in range(columns_num)]
                    csv_row = ";".join(row_elements) + "\n"
                    f.write(csv_row)
                    f.flush()  # Force write to disk immediately
                except Exception as exc:
                    print(f'{title} generated an exception: {exc}')
                
    return None


def download_gdrive_mod(url, name, wait_time, storage_dir):
    
    import os
    import gdown

    url = url.replace('https://drive.google.com/file/d/', '')
    url = url.replace('/view', '')
    url = url.replace('?usp=drive_link', '')
    url = url.replace('?usp=sharing', '')

    archive_path = os.path.join(storage_dir, name+'.rar')
        
    for retry in range(4):
        if not os.path.exists(archive_path):
            gdown.download(id=url, output=archive_path, quiet=True)
        
    return None

def download_moddb_mod(url, name, wait_time, storage_dir):
    
    import os
    import undetected_chromedriver as uc
    import time

    options = uc.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    prefs = {
    "download.default_directory": storage_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True}
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(options=options, version_main=149)
    driver.get(url)

    download_button = driver.find_element(uc.By.TAG_NAME, "a")
    file_name = download_button.text.replace("download ", "")

    suffix = '.file'

    for extension in ['.zip', '.rar', '.7z']:
        if extension in file_name:
            suffix = extension

    download_path = os.path.join(storage_dir, file_name)
    crdownload_path = download_path + ".crdownload"
    elapsed_time = 0

    while elapsed_time < 900:
        if os.path.isfile(download_path) and not os.path.isfile(crdownload_path):
            try:
                os.rename(download_path, os.path.join(storage_dir, name + suffix))
                break
            except PermissionError:
                # Just in case Chrome is taking an extra millisecond to release the lock
                print("File still locked by Chrome. Retrying...")
        time.sleep(wait_time)
        elapsed_time += wait_time

    driver.quit()
    return None 

def get_dir_size(path='.'):
    import os
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_custom_story_description(directory_path):
    import xml.etree.ElementTree as ET
    import os

    # Recursively search for the lang file, ignoring case
    file_path = None
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower() == "extra_english.lang":
                file_path = os.path.join(root, file)
                break
        if file_path:
            break

    # If the file doesn't exist in the mod at all, fail gracefully instead of crashing
    if not file_path or not os.path.exists(file_path):
        return "Description not found (No lang file)."

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        xpath_query = ".//CATEGORY[@Name='CustomStoryMain']/Entry[@Name='Description']"
        target_entry = root.find(xpath_query)
            
        if target_entry is not None:
            return target_entry.text.strip() if target_entry.text else "Description not found."
    except Exception as e:
        return None
        
    return None

def count_ingame_text_lines(directory_path):
    import xml.etree.ElementTree as ET
    import os
    import re

    # Recursively search for the lang file, ignoring case
    file_path = None
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower() == "extra_english.lang":
                file_path = os.path.join(root, file)
                break
        if file_path:
            break

    # Graceful fallback if file is absent
    if not file_path or not os.path.exists(file_path):
        return 0

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        total_lines = 0
        for category in root.findall(".//CATEGORY"):
            if category.get("Name") == "Journal":
                for entry in category.findall("Entry"):
                    entry_name = entry.get("Name", "")
                    if entry_name.endswith("_text"):
                        text_content = entry.text.replace("[br]"," ") if entry.text else ""
                        sentence_count = len(re.findall(r'[.!?](?:\s|$)', text_content))
                        total_lines += sentence_count
            elif category.get("Name") not in ["CustomStoryMain", "Inventory", "Levels"]:
                for entry in category.findall("Entry"):
                    text_content = entry.text.replace("[br]"," ") if entry.text else ""
                    sentence_count = len(re.findall(r'[.!?](?:\s|$)', text_content))
                    total_lines += sentence_count
        
        return total_lines
    except:
        return 0
    
def has_title_image(directory_path):
    
    import os
    
    if len(os.listdir(directory_path))==1:
        directory_path = os.path.join(directory_path, os.listdir(directory_path)[0])

    try:
        for file in os.listdir(directory_path):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', 'tga')):
                return 1

        return 0
    except Exception as e:
        return e
    
def list_custom_models(directory_path):

    import os
    
    if len(os.listdir(directory_path))==1:
        directory_path = os.path.join(directory_path, os.listdir(directory_path)[0])

    model_list = []
    
    try:        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.dae'):
                    model_list.append(file)
                
    except Exception as e:
        return e
            
    return model_list
    
def list_custom_sounds(directory_path):

    import os
    
    if len(os.listdir(directory_path))==1:
        directory_path = os.path.join(directory_path, os.listdir(directory_path)[0])

    sound_list = []
    
    try:        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.ogg'):
                    sound_list.append(file)
                
    except Exception as e:
        return e
            
    return sound_list