from RuntimeConfigsModule import LLM_MODEL_FOR_WEB_SEARCH, LLM_ENGINE, LLM_MODEL_PROVIDER
from FileUtilitiesModule import calculateUsageCost
from seleniumwire2 import webdriver
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service
from selenium.common import TimeoutException

"""Setting Path to Chrome Driver Binary"""
# service = Service("/usr/bin/chromedriver")

def SeleniumHTMLRetrieval(browserHeader: dict, url: str) -> tuple[int, bytes]:
    """
    Description: Opening Headless Selenium browser to fetch url response content with customized browser header
    :param browserHeader: Customized browser header
    :param url: URL to retrieve the response content in bytes
    :return: Status code of the request and the response bytes content
    """
    print("Opening Selenium Webdriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--no-sandbox')  # Enable the spider to run web scrape in real life browser.
    chrome_options.add_argument('--disable-dev-shm-usage')  # Disable shared memory feature that could cause the Selenium Chromium session to crash.
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # IMPORTANT: Remove the navigator.webdriver flag that websites use to detect Selenium. Selenium default set this to true.
    chrome_options.add_experimental_option("excludeSwitches",["enable-automation"])  # IMPORTANT: Removes the "Chrome is being controlled by automated test software" banner and prevent Chrome form adding automation-related command -line switches.
    chrome_options.add_experimental_option('useAutomationExtension',False)  # IMPORTANT: Disables Chrome's automation extension that Selenium normally loads. This limit the bot detection surface.
    userAgent = browserHeader.get('user-agent')
    if userAgent:
        chrome_options.add_argument(f'user-agent={userAgent}')
        print(f"Using ScrapeOps fake user agent: {userAgent}")
    # browser = webdriver.Chrome(options=chrome_options, service=service)
    browser = webdriver.Chrome(options=chrome_options)
    if browserHeader and hasattr(browser, 'execute_cdp_cmd'):
        headers_to_set = {}
        for key, value in browserHeader.items():
            if key not in ['user-agent']:
                headers_to_set[key] = value

        if headers_to_set:
            browser.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': headers_to_set})
            print(f"Set {len(headers_to_set)} additional headers via CDP")
            print(f"Using ScrapeOps browser header: {browserHeader}")
    print(f"Making request to URL: {url}")
    browser.set_page_load_timeout(10)
    try:
        browser.get(url)
    except TimeoutException:
        print(f"Page load timed out at 10s for {url}, attempting to proceed...")
    EncodedResponseBody = browser.page_source.encode('utf-8')
    currentUrl = browser.current_url
    statusCode = 200
    for request in reversed(browser.requests):
        if request.response:
            if request.url == currentUrl or (request.url.rstrip('/') == currentUrl.rstrip('/')):
                statusCode = request.response.status_code
                print(f"Final page status for {currentUrl}: {statusCode}")
                break
    print("Closing and Quitting Selenium Webdriver...")
    browser.close()
    browser.quit()
    return statusCode, EncodedResponseBody


async def scanWebContentUsingWebSearchWithLLM(url: str) -> str:
    """
    Description: Scanning web content with web search tool
    :param url: The URL to be scanned
    :return: The scan result
    """
    # https://developers.openai.com/api/docs/pricing#built-in-tools
    print(f"Starting LLM web search analysis with {LLM_MODEL_FOR_WEB_SEARCH}")
    systemPrompt = "You are a web content moderator"
    prompt = (f"# ACTION\n"
              f"Perform a search on a website url and determine if the website contains NSFW content\n "
              f"# URL\n"
              f"{url}\n"
              f"# RESPONSE FORMAT\n"
              f"1. If the website can not be access, just reply CAN NOT ACCESS WEBSITE.\n"
              f"2. If the website is detected with NSFW content, ALWAYS START your reply with a Yes, then EXPLAIN the reason NO MORE THAN 30 WORDS!\n"
              f"3. If the website does not have any NSFW content, just reply No.")
    if LLM_MODEL_PROVIDER == "openai":
        response = await LLM_ENGINE.responses.create(
            model=LLM_MODEL_FOR_WEB_SEARCH,
            tools=[{"type": "web_search"}],
            instructions=systemPrompt,
            input=prompt,
            max_output_tokens=2000,
            store=False
        )
    else:
        response = await LLM_ENGINE.aio.interactions.create(
            model=LLM_MODEL_FOR_WEB_SEARCH,
            tools=[{"type": "url_context"}],
            system_instruction=systemPrompt,
            input=prompt,
            generation_config={"max_output_tokens": 2000},
            store=True
        )
    totalCost = await calculateUsageCost(LLM_MODEL_FOR_WEB_SEARCH, response, True)
    print(f"Total Cost: ${totalCost}")
    print(f"Web Search Result: {response.output_text}")
    return response.output_text
