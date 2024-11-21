from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import argparse

#initialize argparse 
parser = argparse.ArgumentParser()

#define arguments
parser.add_argument("file_list", metavar="file_path", type=str, nargs= "+", help="path of txt file(s) to be read")

args = parser.parse_args()

options = Options()
options.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=options)

input_code = driver.find_elements(by='xpath', value="(//input[contains(@class, 'lottery-input__input form-control dropdown-toggle')])")[0]

for file in args.file_list:
    txt_file = open(file, "r")
    lines = txt_file.readlines()
    txt_file.close()

    txt_file = open(file, "w")

    for line in lines:
        if "done" in line:
            txt_file.write(line)
        else:           
            input_code.clear()
            input_code.send_keys(line.strip())
            input_code.send_keys(Keys.RETURN)
            time.sleep(3)
            ungultig = driver.find_elements(by='xpath', value='//span[contains(text(), "Dieser Code ist ungültig")]')
            if len(ungultig) == 0:
                txt_file.write(line.strip() + " - done\n")
            else:
                txt_file.write(line.strip() + " - ungültig\n")
    txt_file.close()




