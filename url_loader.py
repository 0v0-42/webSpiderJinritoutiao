from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import mysql.connector
import threading

# 配置MySQL连接参数
config = {
    'user': 'root',
    'password': '1234',
    'host': 'localhost',
    'database': 'pachong',
}

# 创建一个Chrome浏览器实例
driver = webdriver.Chrome()

# 互斥锁，防止多线程访问冲突
lock = threading.Lock()


def store_url_to_database(url, conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO crawler_article (source_url)
            VALUES (%s)
        ''', (url,))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"存储链接时发生异常：{e}")


def crawl_and_store_new_urls():
    i = 1
    scroll_count = 0
    try:
        # 创建数据库连接
        with mysql.connector.connect(**config) as conn:
            driver.get(
                "https://www.toutiao.com/c/user/token/MS4wLjABAAAAP09LrX61xFpIWrgGdBDqkp-5om9Lans_kuIZ_ipAGRE/?source"
                "=tuwen_detail")

            num = 0
            while num >= 0:
                # 设置 i 的值
                i = i + 1  # 你可以根据需要修改 i 的计算方式

                # 构建 XPath
                xpath = f"/html/body/div[1]/div/div[3]/div[1]/div/div[2]/div/div/div[{i}]/div/div/div/a"

                try:
                    # 使用 presence_of_element_located 直接获取单个元素
                    element = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, xpath)))

                    # 获取单个元素的 href 属性
                    link = element.get_attribute("href")

                    if 'article' in link:
                        with lock:
                            store_url_to_database(link, conn)
                    num += 1
                    if num % 10 == 0:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        scroll_count += 1
                        print(f"已经向下滚动了 {scroll_count} 次")
                except Exception as e:
                    print(f"在这里发生了异常：{e}")
                # 在抓取完10条链接后向下滚动，每次下滚更新会刷出来12条但是不知道为什么只能抓到11条


    except Exception as e:
        print(f"滚动的时候发生了异常：{e}")

    finally:
        # 关闭浏览器窗口
        driver.close()


# 启动存储线程
store_thread = threading.Thread(target=crawl_and_store_new_urls)
store_thread.start()

# 主线程等待存储线程结束
store_thread.join()
