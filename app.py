from flask import Flask, render_template, request
from db_conn import open_db, close_db

app = Flask(__name__)

MOVIES_PER_PAGE = 10
PAGES_PER_BLOCK = 10

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'm.Movie_ID')
    title = request.args.get('title', '')
    director = request.args.get('director', '')
    start_year = request.args.get('start_year', '')
    end_year = request.args.get('end_year', '')

    conn, cur = open_db()

    # 영화 목록의 총 개수를 가져오기
    query_count = '''
    SELECT COUNT(*) as count 
    FROM Movie m
    LEFT JOIN Casting cs ON m.Movie_ID = cs.Movie_ID
    LEFT JOIN Casting_Director cd ON cs.Casting_ID = cd.Casting_ID
    LEFT JOIN Director d ON cd.Director_ID = d.Director_ID
    WHERE (m.Title LIKE %s OR %s = '')
      AND (d.Name LIKE %s OR %s = '')
      AND (m.Released_Year >= %s OR %s = '')
      AND (m.Released_Year <= %s OR %s = '')
    '''
    cur.execute(query_count, ('%' + title + '%', title, '%' + director + '%', director, start_year, start_year, end_year, end_year))
    total_movies = cur.fetchone()['count']

    # 정렬 옵션에 따른 정렬 SQL 구문
    if sort_by == 'released_year':
        order_by = 'm.Released_Year DESC'
    elif sort_by == 'title':
        order_by = 'm.Title'
    elif sort_by == 'director':
        order_by = 'd.Name'
    else:
        order_by = 'm.Movie_ID'

    # 페이지네이션을 위한 영화 목록 가져오기
    offset = (page - 1) * MOVIES_PER_PAGE
    query = f'''
    SELECT m.Movie_ID AS movie_id, m.Title AS title, m.Title_Eng AS title_eng, m.Released_Year AS released_year, 
           m.Category AS category, m.Status AS status,
           IFNULL(GROUP_CONCAT(DISTINCT d.Name SEPARATOR ', '), '') AS director, 
           IFNULL(GROUP_CONCAT(DISTINCT c.Country SEPARATOR ', '), '') AS country, 
           IFNULL(GROUP_CONCAT(DISTINCT cc.Company SEPARATOR ', '), '') AS company,
           IFNULL(GROUP_CONCAT(DISTINCT g.Genre SEPARATOR ', '), '') AS genre
    FROM Movie m
    LEFT JOIN Casting cs ON m.Movie_ID = cs.Movie_ID
    LEFT JOIN Casting_Director cd ON cs.Casting_ID = cd.Casting_ID
    LEFT JOIN Director d ON cd.Director_ID = d.Director_ID
    LEFT JOIN Casting_Country c ON cs.Casting_ID = c.Casting_ID
    LEFT JOIN Casting_Company cc ON cs.Casting_ID = cc.Casting_ID
    LEFT JOIN Genre g ON m.Movie_ID = g.Movie_ID
    WHERE (m.Title LIKE %s OR %s = '')
      AND (d.Name LIKE %s OR %s = '')
      AND (m.Released_Year >= %s OR %s = '')
      AND (m.Released_Year <= %s OR %s = '')
    GROUP BY m.Movie_ID, m.Title, m.Title_Eng, m.Released_Year, m.Category, m.Status, d.Name
    ORDER BY {order_by}
    LIMIT %s OFFSET %s
    '''
    cur.execute(query, ('%' + title + '%', title, '%' + director + '%', director, start_year, start_year, end_year, end_year, MOVIES_PER_PAGE, offset))
    movies = cur.fetchall()

    close_db(conn, cur)

    # 총 페이지 수 계산
    total_pages = total_movies // MOVIES_PER_PAGE
    if total_movies % MOVIES_PER_PAGE > 0:
        total_pages += 1

    # 현재 페이지가 전체 페이지 수를 넘지 않도록 조정
    if total_pages < page:
        page = total_pages

    # 현재 페이지 블록 계산
    start_page = ((page - 1) // PAGES_PER_BLOCK) * PAGES_PER_BLOCK + 1
    end_page = start_page + PAGES_PER_BLOCK - 1

    if end_page > total_pages:
        end_page = total_pages

    return render_template('index.html', movies=movies, page=page, total_pages=total_pages,
                           start_page=start_page, end_page=end_page, sort_by=sort_by,
                           title=title, director=director, start_year=start_year, end_year=end_year,
                           total_movies=total_movies)

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    conn, cur = open_db()
    query = '''
    SELECT m.Movie_ID AS movie_id, m.Title AS title, m.Title_Eng AS title_eng, m.Released_Year AS released_year, 
           m.Category AS category, m.Status AS status,
           IFNULL(GROUP_CONCAT(DISTINCT d.Name SEPARATOR ', '), '') AS director, 
           IFNULL(GROUP_CONCAT(DISTINCT c.Country SEPARATOR ', '), '') AS country, 
           IFNULL(GROUP_CONCAT(DISTINCT cc.Company SEPARATOR ', '), '') AS company,
           IFNULL(GROUP_CONCAT(DISTINCT g.Genre SEPARATOR ', '), '') AS genre
    FROM Movie m
    LEFT JOIN Casting cs ON m.Movie_ID = cs.Movie_ID
    LEFT JOIN Casting_Director cd ON cs.Casting_ID = cd.Casting_ID
    LEFT JOIN Director d ON cd.Director_ID = d.Director_ID
    LEFT JOIN Casting_Country c ON cs.Casting_ID = c.Casting_ID
    LEFT JOIN Casting_Company cc ON cs.Casting_ID = cc.Casting_ID
    LEFT JOIN Genre g ON m.Movie_ID = g.Movie_ID
    WHERE m.Movie_ID = %s
    GROUP BY m.Movie_ID, m.Title, m.Title_Eng, m.Released_Year, m.Category, m.Status, d.Name
    '''
    cur.execute(query, (movie_id,))
    movie = cur.fetchone()
    close_db(conn, cur)
    return render_template('movie_detail.html', movie=movie)

if __name__ == '__main__':
    app.run(debug=True)
