import config  # 설정파일
import pymysql  # MYSQL
from datetime import datetime  # 현재시간
import emoji  # 이모티콘 제거용
from selenium import webdriver  # 셀레니움
from bs4 import BeautifulSoup  # HTML 태그 가져오기
import time
import sys
import dateutil.parser
from dateutil import tz  # Time Zone

# Set Tag
tag = config.TAG

# 시간 변환 함수
def Get_Time(time):
    date = str(dateutil.parser.parse(time)).split("+")[0]
    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    date = date.replace(tzinfo=tz.tzutc())
    date = date.astimezone(tz.tzlocal())
    date = str(date).split("+")[0]
    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    return date


# 이모티콘 제거 함수
def remove_emoji(text):
    return emoji.get_emoji_regexp().sub(r'', text)


# Miss list 로그 생성
def data_log(text):
    f = open("No_input_list({0}).txt".format(datetime.today().strftime("%Y-%m-%d")), 'a')
    f.write("[{0}] {1}\n".format(tag, text))
    f.close()


# 상태 로그 생성
def Log(text):
    f = open("log.txt", 'a')
    cur_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    f.write("[{0}] > {1} :: {2}\n".format(cur_time, tag, text))
    f.close()
    print(text)


# 웹드라이버 실행 경로 chromedriver는 폴더가 아니라 파일명입니다.
driver = webdriver.Chrome(config.DRIVIER)

# Instagram 이동
driver.get('https://www.instagram.com/')
time.sleep(1)

# 로그인 Form 입력
login_id = driver.find_element_by_name('username')
login_id.send_keys(config.ID)  # id 입력
time.sleep(1)

login_pw = driver.find_element_by_name('password')
login_pw.send_keys(config.PW)  # pw 입력

# 로그인 시도
login_pw.submit()
time.sleep(5)

# 태그 이동
driver.get('https://www.instagram.com/explore/tags/' + tag)
time.sleep(5)

page_source = driver.page_source
html = BeautifulSoup(page_source, 'html.parser')
html = html.select('article > div:nth-of-type(2)')[0]

driver.find_element_by_xpath('/html/body/div/section/main/article/div[2]/div/div[1]/div[1]').click()

while True:
    try:
        do = False

        # Check Page Loading..
        try_count = 0

        while True:
            time.sleep(3)
            data_page = BeautifulSoup(driver.page_source, 'html.parser')

            # Page Loading Complete..
            try:
                # Get shortcode
                shortcode = data_page.select(".k_Q0X.NnvRN > a")[0].attrs['href']
                shortcode = shortcode.split('/')[2]

                # Get post_time
                post_time = data_page.select(".k_Q0X.NnvRN time")[0].attrs['datetime']
                post_time = Get_Time(post_time)

                temp_time = str(post_time)

                # ---------- Check Date ----------
                year = int(temp_time.split("-")[0])
                month = int(temp_time.split("-")[1])

                do = True
                if (year < 2020):
                    break
                if (year < 2019):
                    do = "close"
                    break

                if (year == 2020 and month < 4):
                    break
                # ---------- Check Date Finish ----------

                # Get text
                text = data_page.select(".gElp9.rUo9f.PpGvg .C4VMK > span")[0].get_text()

                # Get image link or video link
                # case : video
                try:
                    img = data_page.select("._97aPb video")[0].attrs['src']

                # case : image
                except:
                    img = data_page.select("._97aPb img")[0].attrs['src']

                # Get like
                try:
                    check = data_page.select(".Nm9Fw button")[0].get_text()
                    like = "0"
                    if (check != "좋아요"):
                        try:
                            like = data_page.select(".Nm9Fw span")[0].get_text()
                        except:
                            like = data_page.select(".Nm9Fw button")[0].get_text()
                            like = like.split(" ")[1]
                            like = like.split("개")[0]

                # 비디오 게시물일 경우
                except:
                    driver.find_element_by_class_name('vcOH2').click()
                    time.sleep(1)

                    # 조회 클릭 후 좋아요 받아오기
                    temp = BeautifulSoup(driver.page_source, 'html.parser')
                    try:
                        like = temp.select(".vJRqr span")[0].get_text()
                    except:
                        like = temp.select(".vJRqr")[0].get_text()
                        like = like.split(" ")[1]
                        like = like.split("개")[0]

                    # 조회 끄기
                    driver.find_element_by_tag_name('body').click()
                like = like.replace(",", "")

                # Get comment
                try:
                    comment = 0
                    for link in data_page.find_all(class_="Mr508"):
                        comment += 1

                        # 답글 더하기
                        try:
                            count = link.select(".EizgU")[0].get_text()
                            count = count.split("(")[1]
                            count = count.split("개")[0]
                            comment += int(count)

                        # 답글이 없을 경우
                        except:
                            comment += 0
                except:
                    comment = 0

                # Get Post url
                url = "https://www.instagram.com/p/{0}".format(shortcode)

                # MySQL Connection 연결
                conn = pymysql.connect(
                    host=config.DATABASE['host'],
                    port=config.DATABASE['port'],
                    user=config.DATABASE['user'],
                    password=config.DATABASE['password'],
                    db=config.DATABASE['dbname'],
                    charset='utf8mb4')

                # Connection 으로부터 Dictoionary Cursor 생성
                db = conn.cursor(pymysql.cursors.DictCursor)

                # SQL문 실행
                sql = "SELECT * from TB_INSTAGRAM WHERE shortcode = %s"
                db.execute(sql, (shortcode))

                # 데이터 가져오기
                data = db.fetchone()

                # Case : No data
                if (data == None):
                    sql = "INSERT INTO TB_INSTAGRAM (`shortcode`, `tag`, `text`, `like_cnt`, `image_url`, `comment_cnt`, `url`, `post_time`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"

                    try:
                        db.execute(sql, (shortcode, tag, text, like, img, comment, url, post_time))
                    except:
                        try:
                            db.execute(sql, (shortcode, tag, remove_emoji(text), like, img, comment, url, post_time))
                        except:
                            db.execute(sql, (shortcode, tag, '', like, img, comment, url, post_time))

                    conn.commit()

                else:
                    now = datetime.now()
                    sql = "UPDATE TB_INSTAGRAM SET like_cnt = %s, comment_cnt = %s, updated_at = %s WHERE shortcode = %s"
                    db.execute(sql, (like, comment, now, shortcode))
                    conn.commit()

                # Connection 닫기
                conn.close()

                break

            except:
                if (try_count <= 5):
                    try_count += 1

                    # 뒤로이동
                    driver.find_element_by_css_selector('.ITLxV.coreSpriteLeftPaginationArrow').click()
                    time.sleep(5)

                    # 다음으로 이동
                    driver.find_element_by_css_selector('._65Bje.coreSpriteRightPaginationArrow').click()

                    time.sleep(15)
                    continue
                else:
                    # 현재 게시물 URL
                    data = driver.execute_script('return window.location.pathname')
                    data = data.split('/')[2]

                    Log("Page Load Error.. Shortcode is {0}".format(data))
                    data_log(data)
                    break

        # Check Finish..
        try:
            driver.find_element_by_css_selector('._65Bje.coreSpriteRightPaginationArrow').click()
        except:
            do = "close"

        # System Close
        if (do == "close"):
            Log("Finish !")
            break

    except Exception as e:
        Log("Error.. mesage: {0}".format(e))

driver.quit()
sys.exit()
