import os
import sys
from pathlib import Path
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from dotenv import load_dotenv
from loguru import logger
load_dotenv()

chrome_options = Options()

options = [
    "--headless",
    "--disable-gpu",
    "--window-size=1920,1200",
    "--ignore-certificate-errors",
    "--disable-extensions",
    "--no-sandbox",
    "--disable-dev-shm-usage"
]

for option in options:
    chrome_options.add_argument(option)

# chrome_options.add_argument("--detach")


chrome_options.add_argument("--user-data-dir=/tmp/selenium")

chrome_service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())

driver = webdriver.Chrome(service=chrome_service, options=chrome_options)


def web_driver_wait(by: By, element: str, time: int = 10) -> WebElement:
    return WebDriverWait(driver, time).until(
        EC.presence_of_element_located((by, element))
    )


try:
    driver.get('https://portal.battlefield.com/experience/rules?playgroundId=a56cf4d0-c713-11ec-b056-e3dbf89f52ce')

    # handle login
    try:
        web_driver_wait(By.CLASS_NAME, 'blocklyWorkspace', 15)
        logger.debug("Already Logged in 😃")
    except TimeoutException:
        try:

            logger.debug('Not logged in....')
            web_driver_wait(By.CLASS_NAME, 'login-button').click()
            email = os.getenv('BFPORTAL_EMAIL', None)
            password = os.getenv('BFPORTAL_PASSWORD', None)
            if email is None or password is None:
                sys.exit("email and password to login not found")
            web_driver_wait(By.ID, 'email').send_keys(email)
            web_driver_wait(By.ID, 'password').send_keys(password)
            logger.debug('login info set....')
            web_driver_wait(By.ID, 'logInBtn').click()
            logger.debug("Trying to log in ....")
            try:
                web_driver_wait(By.CLASS_NAME, 'blocklyWorkspace')
                logger.debug('Login Successful')
            except TimeoutException:
                logger.debug('Login failed...Info was set')
                raise
        except TimeoutException:
            logger.debug('Login failed...')
            raise
        except ConnectionRefusedError:
            raise
    except ConnectionRefusedError:
        driver.quit()
        sys.exit("Unable to connect to portal.battlefield.com.. exiting")

except TimeoutException as e:
    logger.debug(f"element not loaded {e}")
    sys.exit()

except selenium.common.exceptions.InvalidArgumentException as e:
    logger.debug("e")
    sys.exit()


# wait till RULES tab is loaded
logger.debug("Waiting for RULES tab to load")
WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.ID, "blockly-1"))
)

# get all in blocklyToolboxCategory
toolbox_categories = driver.find_elements(By.CLASS_NAME, "blocklyToolboxCategory")[1:]
# 7 green
# 15 literals
# 17 vars
# 18 sub
# 19 control actions
logger.debug("Total cat:", len(toolbox_categories))
# click on each cat to load parameter type
for el in toolbox_categories:
    el.find_element(By.CLASS_NAME, "blocklyTreeRow").click()

for el_index, el in enumerate(toolbox_categories):
    el.find_element(By.CLASS_NAME, "blocklyTreeRow").click()
    cat_name = driver.execute_script("return arguments[0].textContent", el)
    #  [...
    #  document.getElementsByClassName("blocklyFlyout")[0].children[1].children[0].children
    #  ].filter(el => el.tagName == "rect")
    driver.execute_script(
        'arguments[0].setAttribute("style", "fill: rgb(54, 57, 62); fill-opacity: 1;")',
        driver.find_element(By.CLASS_NAME, 'blocklyFlyoutBackground')
    )
    blocks = driver.find_element(By.CLASS_NAME, "blocklyFlyout"). \
        find_element(By.CLASS_NAME, "blocklyWorkspace"). \
        find_element(By.CLASS_NAME, "blocklyBlockCanvas"). \
        find_elements(By.CSS_SELECTOR, ':scope > .blocklyDraggable')
    logger.debug(f"{el_index}:- On Category {cat_name}, blocks {len(blocks)}")
    inv_index = 0
    block_canvas = driver.find_element(By.CLASS_NAME, "blocklyFlyout"). \
        find_element(By.CLASS_NAME, "blocklyBlockCanvas")

    for index, block in enumerate(blocks):
        if cat_name not in ["LITERALS", "VARIABLES", "CONTROL ACTIONS"]:
            selectors = [
                'g[transform = "translate(66,12)"]',
                'g[transform = "translate(66,12.5)"]',

                'g[transform = "translate(12,16)"]',
                'g[transform = "translate(12,16.5)"]',

                'g[transform = "translate(120,12)"]',
                'g[transform = "translate(120,12.5)"]',

                'g[transform = "translate(174,12)"]',
                'g[transform = "translate(174,12.5)"]'
            ]

            name = driver.execute_script(
                "return arguments[0].textContent",
                block.find_element(
                    By.CSS_SELECTOR,
                    ",".join(selectors)
                )
            )

        elif cat_name == "LITERALS":
            if index == 0:
                name = "String"
            elif index == 1:
                name = "Number"
            else:
                name = "Bool"
        elif cat_name == 'VARIABLES':
            if index == 0:
                name = "Variable"
            elif index == 1:
                name = "GetVariable"
            else:
                name = "SetVariable"
        else:
            if index != 3:
                name = driver.execute_script(
                    "return arguments[0].querySelector('[transform]').textContent",
                    block
                )
            else:
                name = "If"

        if index > 8:
            base = 0
            if el_index < 7:
                base = -96
            else:
                base = -61

            transform_string = f'arguments[0].' \
                               f'setAttribute("transform", ' \
                               f'"translate(0, {base * (1 if index == 9 else index - 9)}) scale(1)")'
            driver.execute_script(
                transform_string, block_canvas
            )

        if name == "RULE":
            name = "Rule"
        elif name == "CONDITION":
            name = "Condition"

        logger.debug(f"\tExporting {name}")
        images_dir = Path(__file__).parents[2] / "portal_blocks"
        images_dir.mkdir(exist_ok=True, parents=True)
        file_path = images_dir / name
        block.screenshot(str(f"{file_path}.png"))

