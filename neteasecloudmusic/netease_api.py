#!/usr/bin/env python
#encoding: UTF-8

#CopyRight (c) 2014 vellow  &lt;<a
#href="mailto:i@vellow.net">i@vellow.net</a>&gt;

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.


'''
网易云音乐 Api
'''

import re
import os
import json
import requests
import hashlib
import utils
from xdg_support import get_cache_file
from config import config

# list去重
def uniq(arr):
    arr2 = list(set(arr))
    arr2.sort(key=arr.index)
    return arr2

default_timeout = 10


class NetEase(object):
    def __init__(self):
        self.header = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'music.163.com',
            'Referer': 'http://music.163.com/search/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'
        }
        self.cookie_db_file = get_cache_file("neteasecloudmusic/cookie.db")
        self.cookies = self.load_cookie()

    def login_and_get_cookie(self, username, password):
        pattern = re.compile(r'^0\d{2,3}\d{7,8}$|^1[34578]\d{9}$')
        if (pattern.match(username)):
            print 'cellphone login'
            action = 'https://music.163.com/api/login/cellphone'
            data = {
                'phone': username,
                'password': hashlib.md5(str(password)).hexdigest(),
                'rememberLogin': 'true'
            }
        else:
            action = 'http://music.163.com/api/login/'
            data = {
                'username': username,
                'password': hashlib.md5(str(password)).hexdigest(),
                'rememberLogin': 'true'
            }
        s = requests.Session()
        try:
            connection = s.post(
                action,
                data=data,
                headers=self.header,
                timeout=default_timeout
            )
            connection.encoding = "UTF-8"
            connection = json.loads(connection.text)
            self.uid = connection['account']['id']
            self.save_cookie(s.cookies)
            self.cookies = s.cookies
            return s.cookies
        except:
            print 'login failed'
            return None

    def get_uid(self):
        try:
            self.uid = re.match('\d+',
                    dict(self.cookies)['NETEASE_WDA_UID']).group()
            return self.uid
        except:
            print 'get uid failed'
            return None

    def save_cookie(self, cookie=None):
        utils.save_db(cookie, self.cookie_db_file)

    def load_cookie(self):
        try:
            return utils.load_db(self.cookie_db_file)
        except:
            print 'load cookie failed'
            return None

    def httpRequest(self, method, action, query=None, urlencoded=None, callback=None, timeout=None):
        if(method == 'GET'):
            url = action if (query == None) else (action + '?' + query)
            connection = requests.get(url, headers=self.header,
                    timeout=default_timeout, cookies=self.cookies)

        elif(method == 'POST'):
            connection = requests.post(
                action,
                data=query,
                headers=self.header,
                timeout=default_timeout,
                cookies=self.cookies
            )

        connection.encoding = "UTF-8"
        connection = json.loads(connection.text)
        return connection

    # 登录
    def login(self, username, password):
        action = 'http://music.163.com/api/login/'
        data = {
            'username': username,
            'password': hashlib.md5( password ).hexdigest(),
            'rememberLogin': 'true'
        }
        try:
            return self.httpRequest('POST', action, data)
        except:
            print 'login failed'
            return {'code': 501}

    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=100):
        if uid:
            action = 'http://music.163.com/api/user/playlist/?offset=' + str(offset) + '&limit=' + str(limit) + '&uid=' + str(uid)
            try:
                data = self.httpRequest('GET', action)
                return data['playlist']
            except:
                print "get user's playlist failed"
                return []
        else:
            return []

    def get_lyric(self, sid):
        if sid:
            action = 'http://music.163.com/api/song/lyric?os=pc&id=' + str(sid) + '&lv=-1&tv=-1&kv=-1&cp=true'
            try:
                data = self.httpRequest('GET', action)
                return data
            except:
                print 'get lyric failed'
                return []
        else:
            return None

    def handle_songs_info(self, tracks):
        save_path = os.path.expanduser(config.get("lyrics", "save_lrc_path"))
        for item in tracks:
            item['sid'] = item['id']
            item['title'] = item['name']
            item['uri'] = item['mp3Url']
            item['artist'] = ','.join([artist['name'] for artist in
                item['artists']])
            item['#duration'] = item['duration']
            item['location_lrc'] = os.path.join(save_path, str(item['id'])+'.lrc')
            item['album_cover_url'] = item['album']['blurPicUrl']
        return tracks

    def personal_fm(self):
        action = 'http://music.163.com/api/radio/get'
        try:
            tracks = self.httpRequest('GET', action)['data']
            return self.handle_songs_info(tracks)
        except:
            print 'get personal_fm failed'
            return []

    def fm_like(self, sid, like=True, time=25, alg='itembased'):
        if like:
            action = 'http://music.163.com/api/radio/like?alg='+alg+'&trackId='+str(sid)+'&like=true&time='+str(time)
        else:
            action = 'http://music.163.com/api/radio/like?alg='+alg+'&trackId='+str(sid)+'&like=false&time='+str(time)
        try:
            data = self.httpRequest('GET', action)
            if data['code'] == 200:
                return data
            elif data['code'] == 502:
                print 'This song may have already liked/unliked'
                return data
        except:
            print 'fm like/unlike failed'
            return None

    def fm_trash(self, sid, time=25, alg='RT'):
        action = 'http://music.163.com/api/radio/trash/add?alg='+alg+'&songId='+str(sid)+'&time='+str(time)
        try:
            data = self.httpRequest('GET', action)
            return data
            if data['code'] == 200:
                return data
            elif data['code'] == 502:
                print 'fm trash falied'
                return data
        except:
            print 'fm trash failed'
            return None

    def add_to_onlinelist(self, sids, playlist_id):
        trackIds = '['+','.join(['"'+str(sid)+'"' for sid in sids])+']'
        data = {'trackIds': trackIds,
                'pid': playlist_id,
                'op': 'add',
                'imme': 'true'}
        action = 'http://music.163.com/api/v1/playlist/manipulate/tracks'
        try:
            data = self.httpRequest('POST', action, data)
            return data
        except:
            print 'add to onlinelist failed'
            return None

    def delete_from_onlinelist(self, sids, playlist_id):
        trackIds = '['+','.join(['"'+str(sid)+'"' for sid in sids])+']'
        data = {'trackIds': trackIds,
                'pid': playlist_id,
                'op': 'del'}
        action = 'http://music.163.com/api/v1/playlist/manipulate/tracks'
        try:
            data = self.httpRequest('POST', action, data)
            return data
        except:
            print 'delete from onlinelist failed'
            return None

    # 搜索单曲(1)，歌手(100)，专辑(10)，歌单(1000)，用户(1002) *(type)*
    def search(self, s, stype=1, offset=0, total='true', limit=60):
        action = 'http://music.163.com/api/search/get/web'
        data = {
            's': s,
            'type': stype,
            'offset': offset,
            'total': total,
            'limit': limit
        }
        try:
            result = self.httpRequest('POST', action, data)
            if stype == 1 or stype == '1':
                songs = result['result']['songs']
                return songs
            # 搜索歌单
            # 歌单名称      playlist['name']
            # 歌单id        playlist['id']
            # 歌曲数量      playlist['trackCount']
            # 创建者        playlist['creator']['nickname']
            elif stype == 1000 or stype == '1000':
                playlists = result['result']['playlists']
                return playlists
        except:
            print 'search failed'
            return []

    def subscribe_playlist(self, playlist_id):
        action = 'http://music.163.com/api/playlist/subscribe/?id=' + str(playlist_id) + '&csrf_token=' + self.cookies['__csrf']
        try:
            data = self.httpRequest('GET', action)
            return data
        except:
            print 'subscribed playlist failed'
            return None

    def unsubscribe_playlist(self, playlist_id):
        action = 'http://music.163.com/api/playlist/unsubscribe/?id=' + str(playlist_id) + '&csrf_token=' + self.cookies['__csrf']
        try:
            data = self.httpRequest('GET', action)
            return data
        except:
            print 'unsubscribed playlist failed'
            return None

    # 新碟上架 http://music.163.com/#/discover/album/
    def new_albums(self, offset=0, limit=50):
        action = 'http://music.163.com/api/album/new?area=ALL&offset=' + str(offset) + '&total=true&limit=' + str(limit)
        try:
            data = self.httpRequest('GET', action)
            return data['albums']
        except:
            return []

    # 歌单（网友精选碟） hot||new http://music.163.com/#/discover/playlist/
    def top_playlists(self, category='全部', order='hot', offset=0, limit=50):
        action = 'http://music.163.com/api/playlist/list?cat=' + category + '&order=' + order + '&offset=' + str(offset) + '&total=' + ('true' if offset else 'false') + '&limit=' + str(limit)
        try:
            data = self.httpRequest('GET', action)
            return data['playlists']
        except:
            return []

    # 歌单详情
    def playlist_detail(self, playlist_id):
        action = 'http://music.163.com/api/playlist/detail?id=' + str(playlist_id)
        try:
            data = self.httpRequest('GET', action)
            tracks = data['result']['tracks']
            return self.handle_songs_info(tracks)
        except:
            print 'get playlist_detail failed, playlist_id:', playlist_id
            return []

    # 热门歌手 http://music.163.com/#/discover/artist/
    def top_artists(self, offset=0, limit=100):
        action = 'http://music.163.com/api/artist/top?offset=' + str(offset) + '&total=false&limit=' + str(limit)
        try:
            data = self.httpRequest('GET', action)
            return data['artists']
        except:
            return []

    # 热门单曲 http://music.163.com/#/discover/toplist 50
    def top_songlist(self, offset=0, limit=100):
        action = 'http://music.163.com/discover/toplist'
        try:
            connection = requests.get(action, headers=self.header, timeout=default_timeout)
            connection.encoding = 'UTF-8'
            songids = re.findall(r'/song\?id=(\d+)', connection.text)
            if songids == []:
                return []
            # 去重
            songids = uniq(songids)
            return self.songs_detail(songids)
        except:
            return []

    # 歌手单曲
    def artists(self, artist_id):
        action = 'http://music.163.com/api/artist/' + str(artist_id)
        try:
            data = self.httpRequest('GET', action)
            return data['hotSongs']
        except:
            return []

    # album id --> song id set
    def album(self, album_id):
        action = 'http://music.163.com/api/album/' + str(album_id)
        try:
            data = self.httpRequest('GET', action)
            return data['album']['songs']
        except:
            return []

    # song ids --> song urls ( details )
    def songs_detail(self, ids, offset=0):
        tmpids = ids[offset:]
        tmpids = tmpids[0:100]
        tmpids = map(str, tmpids)
        action = 'http://music.163.com/api/song/detail?ids=[' + (',').join(tmpids) + ']'
        try:
            data = self.httpRequest('GET', action)
            songs_info =  data['songs']
            return self.handle_songs_info(songs_info)
        except:
            print 'get songs_detail failed, ids:', ids
            return []

    # 今日最热（0）, 本周最热（10），历史最热（20），最新节目（30）
    def djchannels(self, stype=0, offset=0, limit=50):
        action = 'http://music.163.com/discover/djchannel?type=' + str(stype) + '&offset=' + str(offset) + '&limit=' + str(limit)
        try:
            connection = requests.get(action, headers=self.header, timeout=default_timeout)
            connection.encoding = 'UTF-8'
            channelids = re.findall(r'/dj\?id=(\d+)', connection.text)
            channelids = uniq(channelids)
            return self.channel_detail(channelids)
        except:
            return []

    # DJchannel ( id, channel_name ) ids --> song urls ( details )
    # 将 channels 整理为 songs 类型
    def channel_detail(self, channelids, offset=0):
        channels = []
        for i in range(0, len(channelids)):
            action = 'http://music.163.com/api/dj/program/detail?id=' + str(channelids[i])
            try:
                data = self.httpRequest('GET', action)
                channel = self.dig_info( data['program']['mainSong'], 'channels' )
                channels.append(channel)
            except:
                continue

        return channels

    def dig_info(self, data ,dig_type):
        temp = []
        if dig_type == 'songs':
            for i in range(0, len(data) ):
                song_info = {
                    'song_id': data[i]['id'],
                    'artist': [],
                    'song_name': data[i]['name'],
                    'album_name': data[i]['album']['name'],
                    'mp3_url': data[i]['mp3Url']
                }
                if 'artist' in data[i]:
                    song_info['artist'] = data[i]['artist']
                elif 'artists' in data[i]:
                    for j in range(0, len(data[i]['artists']) ):
                        song_info['artist'].append( data[i]['artists'][j]['name'] )
                    song_info['artist'] = ', '.join( song_info['artist'] )
                else:
                    song_info['artist'] = '未知艺术家'

                temp.append(song_info)

        elif dig_type == 'artists':
            temp = []
            for i in range(0, len(data) ):
                artists_info = {
                    'artist_id': data[i]['id'],
                    'artists_name': data[i]['name'],
                    'alias': ''.join(data[i]['alias'])
                }
                temp.append(artists_info)

            return temp

        elif dig_type == 'albums':
            for i in range(0, len(data) ):
                albums_info = {
                    'album_id': data[i]['id'],
                    'albums_name': data[i]['name'],
                    'artists_name': data[i]['artist']['name']
                }
                temp.append(albums_info)

        elif dig_type == 'playlists':
            for i in range(0, len(data) ):
                playlists_info = {
                    'playlist_id': data[i]['id'],
                    'playlists_name': data[i]['name'],
                    'creator_name': data[i]['creator']['nickname']
                }
                temp.append(playlists_info)


        elif dig_type == 'channels':
            channel_info = {
                'song_id': data['id'],
                'song_name': data['name'],
                'artist': data['artists'][0]['name'],
                'album_name': 'DJ节目',
                'mp3_url': data['mp3Url']
                }
            temp = channel_info

        return temp
