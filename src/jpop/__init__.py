# -*- coding: utf-8 -*-
import urllib
import re
import datetime
import gdata.youtube
import gdata.youtube.service
from BeautifulSoup import BeautifulSoup
from contextlib import closing
import sqlite3
from flask import Flask
from flask import render_template
from flask import g

# configuration
DATABASE   = 'jpop.db'
DEBUG      = True
NUM_SONGS  = 10
UTAMAP_URL = 'http://access.utamap.com/ranking/index-new-lyrics.php'
LYRIC_URL  = 'http://www.utamap.com/phpflash/flashfalsephp.php?unum='

# create our application
app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.after_request
def after_request(response):
    g.db.close()
    return response

@app.route('/')
def show_ranking():
    songs = get_ranking(NUM_SONGS)
    return render_template('main.html', songs=songs)

def get_ranking(num_songs=10):
    today = datetime.date.today()
    ranking = get_ranking_fr_db(num_songs, today)
    if ranking == None:
        ranking = get_ranking_fr_web(num_songs, today)
    return ranking

def get_ranking_fr_db(num_songs, date):
    sql  = "SELECT ranking.utamap_id, title, artist, lyric, youtube, rank FROM ranking "
    sql += "LEFT OUTER JOIN songs ON (ranking.utamap_id = songs.utamap_id) "
    sql += "WHERE ranking.crawl_date = '%s' " % str(date)
    cur = g.db.execute(sql)
    rows = cur.fetchall()
    if rows != [] and len(rows) >= num_songs:
        songs = [dict(utamap_id=row[0], title=row[1], artist=row[2], lyric=row[3], youtube=row[4], rank=row[5], lines=row[3].split("\n")) for row in rows]
        return songs
    else:
        return None
    
def get_ranking_fr_web(num_songs, date):
    src = urllib.urlopen(UTAMAP_URL).read()
    soup = BeautifulSoup(src)
    songs = list()
    for data in soup('tr', bgcolor='#ffffff')[0:num_songs]:
        utamap_id = data.find('td', {'class':'td2'}).contents[0]['href'].split('?surl=')[1]
        song = get_song_fr_db(utamap_id)        
        if song == None:
            song = dict()
            song['utamap_id'] = utamap_id
            song['title']   = data.find('td', {'class':'td2'}).contents[0].string
            song['artist']  = data.find('td', {'class':'td3'}).contents[0].strip()
            song['lyric']   = get_lyric(utamap_id)
            search_terms = song['title'] + u" " + song['artist']
            youtube_url = get_youtube(search_terms.encode('utf-8'))
            song['youtube'] = youtube_url.encode('utf-8')        
            save_song(song)
        song['lines'] = song['lyric'].split("\n")
        song['rank'] = int(data.find('td', {'class':'td1'}).contents[0])
        songs.append(song)
        save_rank(song)
    return songs
    
def get_song_fr_db(utamap_id):
    cur = g.db.execute("SELECT title, artist, lyric, youtube, utamap_id FROM songs WHERE utamap_id = '%s'" % utamap_id)
    rows = cur.fetchall()
    if rows == []:
        return None
    else:
        row = rows[0]
        song = dict(title=row[0], artist=row[1], lyric=row[2], youtube=row[3], utamap_id=row[4])
        return song

def save_song(song):
    g.db.execute('INSERT INTO songs (utamap_id, title, lyric, artist, youtube) values (?, ?, ?, ?, ?)',
                 [song['utamap_id'], song['title'], song['lyric'], song['artist'], song['youtube']])
    g.db.commit()

def save_rank(song):
    today = datetime.date.today()
    g.db.execute('INSERT INTO ranking (crawl_date, rank, utamap_id) values (?, ?, ?)',
                 [str(today), song['rank'], song['utamap_id']])
    g.db.commit()

def get_lyric(song_id):
    src = urllib.urlopen(LYRIC_URL+song_id).read()
    lyric = re.split('(test2=)', src)[2]
    return lyric.decode('utf-8')
    
def get_youtube(search_terms):
    yt_service = gdata.youtube.service.YouTubeService()
    query = gdata.youtube.service.YouTubeVideoQuery()
    query.vq = search_terms
    query.max_results = 1
    query.format = '5'
    query.lr = 'ja'
    feed = yt_service.YouTubeQuery(query)
    for entry in feed.entry:
        youtube_url = entry.GetSwfUrl()
        return youtube_url.encode('utf-8')

def main():
    if DEBUG:
        app.debug = True
    app.run()
    show_ranking()

if __name__ == '__main__':
    main()
