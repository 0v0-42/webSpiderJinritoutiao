import os
import multiprocessing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import mysql.connector
import time

# 配置MySQL连接参数
config = {
    'user': 'root',
    'password': '1234',
    'host': 'localhost',
    'database': 'pachong',
}

driver = webdriver.Chrome()


def get_content_from_database(process_id, num_processes):
    try:
        # Connect to the database in each process
        conn = mysql.connector.connect(**config)

        # Select source_url from rows where id > 680 and distribute articles among processes
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_url FROM crawler_article")
        rows = cursor.fetchall()

        # Calculate the range of articles for this process
        start_index = process_id * len(rows) // num_processes
        end_index = (process_id + 1) * len(rows) // num_processes

        # Filter rows based on the range
        process_rows = rows[start_index:end_index]

        # Iterate over the rows and get content for each URL
        for row in process_rows:
            article_id, article_url = row
            new_content_found = True  # Flag to check if new content is found

            # Open a new tab and switch to it
            driver.execute_script("window.open('', '_blank');")
            driver.switch_to.window(driver.window_handles[-1])

            for paragraph_number in range(1, 100):
                if not get_content_and_save(driver, article_id, article_url, paragraph_number):
                    new_content_found = False
                    break  # Break out of the loop if no new content is found

            # Close the current tab and switch back to the first tab
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            if new_content_found:
                print(f"Content for article {article_id} saved successfully by process {process_id}.")

        # Close the cursor and connection
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"An error occurred: {e}")


def get_content_and_save(driver, article_id, url, paragraph_number):
    try:
        # Concatenate URL and XPath dynamically
        xpath = f"/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div/div/article/p[{paragraph_number}]"
        xpath_title = "/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div/div/h1"
        xpath_author = "/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div/div/div/span[3]/a"
        xpath_publish_date = "/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div/div/div/span[1]"
        full_url = f"{url}#{xpath}"

        # Visit the concatenated URL
        driver.get(full_url)

        # Check if the article content exists
        if EC.presence_of_element_located((By.XPATH, xpath)):
            # Wait for the article content to load
            element = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, xpath)))
            element_title = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, xpath_title)))
            element_author = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, xpath_author)))
            element_publish_date = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, xpath_publish_date)))

            # Get the content of the specified paragraph
            paragraph_content = driver.find_element(By.XPATH, xpath).text
            title = driver.find_element(By.XPATH, xpath_title).text
            author = driver.find_element(By.XPATH, xpath_author).text
            publish_date = driver.find_element(By.XPATH, xpath_publish_date).text
            save_to_database(article_id, title, author, publish_date)
            # Save content to a txt file
            save_to_txt(article_id, paragraph_content)

            return True  # New content found

    except Exception as e:
        print(f"An error occurred: {e}")

    return False  # No new content found


def save_to_database(article_id, title, author, publish_date):
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE crawler_article
            SET processed = True, title = %s, author = %s, publish_date = %s
            WHERE id = %s
        """, (title, author, publish_date, article_id))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"An error occurred while saving to the database: {e}")


def save_to_txt(article_id, content):
    # Create an "文章" folder if it doesn't exist
    if not os.path.exists("文章"):
        os.makedirs("文章")

    # Generate the file name using article_id
    file_name = f"文章/{article_id}.txt"

    # Write content to the txt file
    with open(file_name, "a", encoding="utf-8") as file:
        file.write(content + "\n\n")  # Add newline between paragraphs


def main():
    num_processes = 4
    poll_interval = 60  # 60 seconds, you can adjust this based on your needs

    while True:
        # Connect to the database and check for new URLs
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_url FROM crawler_article WHERE processed = False")
        rows = cursor.fetchall()
        conn.close()

        if rows:
            # If there are new URLs, distribute tasks among processes
            processes = []
            for process_id in range(num_processes):
                process = multiprocessing.Process(target=get_content_from_database, args=(process_id, num_processes))
                processes.append(process)
                process.start()

            for process in processes:
                process.join()

        # Sleep for a while before checking again
        time.sleep(poll_interval)


if __name__ == '__main__':
    # 创建并启动主进程
    main()
