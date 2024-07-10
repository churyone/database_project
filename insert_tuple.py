import pandas as pd
import numpy as np
from db_conn import *

import sys

def replace_to_none(df):
    # 데이터프레임의 비어있는 값을 None으로 채움
    df = df.where(pd.notnull(df), None)
    return df

def print_nan_values(df):
    # NaN 값을 가진 셀만 출력
    nan_positions = df.isna()
    for col in df.columns:
        nan_indices = nan_positions[nan_positions[col]].index
        for idx in nan_indices:
            print(f"NaN value found at column: {col}, row index: {idx}, value: {df.at[idx, col]}")

def convert_none_to_null(data):
    # None 값을 명시적으로 NULL로 변환
    return [[v if v is not None else 'NULL' for v in row] for row in data]

def read_excel_into_mysql(sheet_name, skiprows, batch_size):
    # 엑셀 파일 경로
    excel_file = "movie_list.xls"

    # 데이터베이스 연결 열기
    conn, cur = open_db()

    # 엑셀 파일을 읽어 DataFrame으로 변환
    df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=skiprows)
    # 컬럼 이름을 영어로 변경
    df.columns = ['Title', 'Title_Eng', 'Released_Year', 'Country', 'Category', 'Genre', 'Status', 'Director', 'Company']
    filtered_df = replace_to_none(df)
    print(filtered_df.head())

    # NaN 값을 가진 셀 출력
    print("Cells with NaN values:")
    print_nan_values(filtered_df)

    # 테이블 이름 배정
    movie_table = "Movie"
    genre_table = "Genre"
    director_table = "Director"
    casting_table = "Casting"
    casting_director_table = "Casting_Director"
    casting_country_table = "Casting_Country"
    casting_company_table = "Casting_Company"

     # 외래 키 제약 조건을 먼저 삭제하는 SQL문
    drop_constraints_sql = f"""
        SET FOREIGN_KEY_CHECKS = 0;
        DROP TABLE IF EXISTS {genre_table};
        DROP TABLE IF EXISTS {casting_director_table};
        DROP TABLE IF EXISTS {casting_country_table};
        DROP TABLE IF EXISTS {casting_company_table};
        DROP TABLE IF EXISTS {casting_table};
        DROP TABLE IF EXISTS {director_table};
        DROP TABLE IF EXISTS {movie_table};
        SET FOREIGN_KEY_CHECKS = 1;
    """

    # 영화 테이블 생성 SQL문
    create_movie_sql = f"""
        CREATE TABLE {movie_table} (
            Movie_ID INT AUTO_INCREMENT PRIMARY KEY,
            Title VARCHAR(500),
            Title_Eng VARCHAR(500),
            Released_Year INT,
            Country VARCHAR(100),
            Category VARCHAR(100),
            Status VARCHAR(30)
        ); """

    # 장르 테이블 생성 SQL문
    create_genre_sql = f"""
        CREATE TABLE {genre_table} (
            Movie_ID INT,
            Genre VARCHAR(100),
            PRIMARY KEY (Movie_ID, Genre),
            FOREIGN KEY (Movie_ID) REFERENCES {movie_table}(Movie_ID)
        ); """

    # 감독 테이블 생성 SQL문
    create_director_sql = f"""
        CREATE TABLE {director_table} (
            Director_ID INT AUTO_INCREMENT PRIMARY KEY,
            Name VARCHAR(100)
        ); """

    # 캐스팅 테이블 생성 SQL문
    create_casting_sql = f"""
        CREATE TABLE {casting_table} (
            Casting_ID INT AUTO_INCREMENT PRIMARY KEY,
            Movie_ID INT,
            FOREIGN KEY (Movie_ID) REFERENCES {movie_table}(Movie_ID)
        ); """

    # 캐스팅_디렉터 테이블 생성 SQL문
    create_casting_director_sql = f"""
        CREATE TABLE {casting_director_table} (
            Casting_ID INT,
            Director_ID INT,
            PRIMARY KEY (Casting_ID, Director_ID),
            FOREIGN KEY (Casting_ID) REFERENCES {casting_table}(Casting_ID),
            FOREIGN KEY (Director_ID) REFERENCES {director_table}(Director_ID)
        ); """

    # 캐스팅_컨트리 테이블 생성 SQL문
    create_casting_country_sql = f"""
        CREATE TABLE {casting_country_table} (
            Casting_ID INT,
            Country VARCHAR(100),
            PRIMARY KEY (Casting_ID, Country),
            FOREIGN KEY (Casting_ID) REFERENCES {casting_table}(Casting_ID)
        ); """

    # 캐스팅_컴퍼니 테이블 생성 SQL문
    create_casting_company_sql = f"""
        CREATE TABLE {casting_company_table} (
            Casting_ID INT,
            Company VARCHAR(100),
            PRIMARY KEY (Casting_ID, Company),
            FOREIGN KEY (Casting_ID) REFERENCES {casting_table}(Casting_ID)
        ); """

    # 테이블 생성 쿼리문 실행
    try:
        cur.execute(drop_constraints_sql)
    except Exception as e:
        print("Warning: ", e)
    cur.execute(create_movie_sql)
    cur.execute(create_genre_sql)
    cur.execute(create_director_sql)
    cur.execute(create_casting_sql)
    cur.execute(create_casting_director_sql)
    cur.execute(create_casting_country_sql)
    cur.execute(create_casting_company_sql)
    conn.commit()

    # 데이터 삽입 SQL문
    insert_movie_sql = f"""INSERT INTO {movie_table} (Title, Title_Eng, Released_Year, Country, Category, Status)
                           VALUES (%s, %s, %s, %s, %s, %s);"""

    insert_genre_sql = f"""INSERT INTO {genre_table} (Movie_ID, Genre)
                           VALUES (%s, %s);"""

    insert_director_sql = f"""INSERT INTO {director_table} (Name)
                              VALUES (%s);"""

    insert_casting_sql = f"""INSERT INTO {casting_table} (Movie_ID)
                             VALUES (%s);"""

    insert_casting_director_sql = f"""INSERT INTO {casting_director_table} (Casting_ID, Director_ID)
                                      VALUES (%s, %s);"""

    insert_casting_country_sql = f"""INSERT INTO {casting_country_table} (Casting_ID, Country)
                                     VALUES (%s, %s);"""

    insert_casting_company_sql = f"""INSERT INTO {casting_company_table} (Casting_ID, Company)
                                     VALUES (%s, %s);"""

    # 배치 사이즈마다 나눠서 삽입
    def batch_insert(data, insert_sql, batch_size):
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                # None 값을 명시적으로 NULL로 변환
                batch = convert_none_to_null(batch)
                cur.executemany(insert_sql, batch)
                conn.commit()
                print(f"{len(batch)} rows inserted")

   # 데이터를 삽입하기 위한 리스트 생성
    movie_data = []
    genre_data = []
    director_data = []
    casting_data = []
    casting_director_data = []
    casting_country_data = []
    casting_company_data = []

    for i, row in filtered_df.iterrows():
        movie_data.append((row['Title'], row['Title_Eng'], row['Released_Year'], row['Country'], row['Category'], row['Status']))

   # 데이터를 테이블에 배치로 삽입
    try:
        batch_insert(movie_data, insert_movie_sql, batch_size)

        # 삽입된 Movie_ID를 사용하여 나머지 데이터를 삽입
        for i, movie_id in enumerate(range(cur.lastrowid - len(movie_data) + 1, cur.lastrowid + 1)):
            genre_data.append((movie_id, filtered_df.iloc[i]['Genre']))
            casting_data.append((movie_id,))

        batch_insert(genre_data, insert_genre_sql, batch_size)
        batch_insert(casting_data, insert_casting_sql, batch_size)

        for i, casting_id in enumerate(range(cur.lastrowid - len(casting_data) + 1, cur.lastrowid + 1)):
            director_name = filtered_df.iloc[i]['Director']
            # Check if the director exists
            cur.execute(f"SELECT Director_ID FROM {director_table} WHERE Name = %s", (director_name,))
            result = cur.fetchone()
            if result:
                director_id = result[0]
            else:
                # Insert new director
                cur.execute(insert_director_sql, (director_name,))
                conn.commit()
                director_id = cur.lastrowid
            
            casting_director_data.append((casting_id, director_id))
            casting_country_data.append((casting_id, filtered_df.iloc[i]['Country']))
            casting_company_data.append((casting_id, filtered_df.iloc[i]['Company']))

        batch_insert(casting_director_data, insert_casting_director_sql, batch_size)
        batch_insert(casting_country_data, insert_casting_country_sql, batch_size)
        batch_insert(casting_company_data, insert_casting_company_sql, batch_size)

    except Exception as e:
        print(e)

    # 데이터베이스 연결 닫기
    close_db(conn, cur)

if __name__ == '__main__':
    # 첫 번째 시트: 4번째 줄부터 시작
    sheet_name_1 = '영화정보 리스트'
    read_excel_into_mysql(sheet_name_1, skiprows=4, batch_size= 1000)

    # 두 번째 시트: 첫 번째 줄부터 시작
    sheet_name_2 = '영화정보 리스트_2'
    read_excel_into_mysql(sheet_name_2, skiprows=0, batch_size= 1000)
