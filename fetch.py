#!/usr/bin/python
# coding:utf-8
#spider

import urllib2
import re
import os
import pprint
import time
from random import randint

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36'}

#data source
base_url = "http://www.umei.cc/tags/BeautyLeg.htm"
down_dir = './down_pic/'

#在down_status.data中记录总进度，如果当前list中所有角色都下载完毕，则删除listData，并在down_status中记录此次下载的序号（NO值），这样网站更新数据后，就从这个序号开始开始最新的数据。而不用担心将整个list重新下载一遍。
status_file = './bleg_status.data'
#如果没有状态也只下载1000以后的数据
default_order = 1000

#列表数据(当前url中每个角色的相册地址),只是用来寻找单张地址集合而已，实际的数据和进度都是在each_star_file中存储。
star_list_file = './bleg_list.data'
#单张图地址集合(存储每个相册中所有图片地址，会动态更新，是断点续传的保证)
each_star_file = './bleg_single.data'


import pickle
def save_data(data_path , data):
    f = open(data_path, 'wb' )
    pickle.dump(data, f)
    f.close()

def load_data(data_path):
    try:
        f = open(data_path, 'rb' )
        result = pickle.load(f)
        return result
    except(IOError, EOFError):
        print data_path, ' does not exist.'
        return False


#basic module
def wget(url, proxy=None):
    req = urllib2.Request(url, headers= headers)
    f = urllib2.urlopen(req)
    return f.read()

def wfile(f, content=''):
    '''
    A simple module for writting file
    '''
    rf = open(f, 'w')
    rf.write(content)
    rf.close()

def formatNum(num, digit = 4):
    '''
    format number to string with specify digit
    i.e format 1 to '0001'
    '''
    num2str = str(num)
    if len(num2str) >= digit:
        return str(num)
    else:
        return '0'*(digit - len(num2str)) + num2str

def alexDown(url, path):
    req = urllib2.Request(url, headers= headers)

    try:
        u = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        print e.code, e.msg
        return 

    f = open(path , 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (path, file_size)

    file_size_dl = 0
    block_sz = 1024
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,
    f.close()

#test
#print formatNum(0)

#get all star
def getAllStar(url):
    '''
    return {list} i.e ['urlx', 'urly']
    '''
    star_urls = load_data(star_list_file)
    if  star_urls:
        print 'Got list From Local '
        return star_urls 
    else:
        print 'Getting List From Remote'

        url_content = wget(url)
        #i.e <DIV class=title><A href=http://www.80517185.htm >xx</A></DIV>

        result = re.findall(r'<DIV class=title>.*href=(.*.htm).*', url_content)

        #save data
        save_data(star_list_file, result )
        print 'Got list, Saved in: ', star_list_file
        return result

#find img rule for all star
def findImgRule(urls):
    '''
    return {list} of {dict}
    e.g. [{img: img_url, total: number, current: number}]
    '''

    #get last order
    status_data = load_data(status_file)
    if status_data:
        last_order = status_data['last_order']
    else:
        last_order = default_order 

    print 'Getting Rule From Remote'
    result = []
    for url in urls:
        url_content = wget(url)
        #e.g. <img class=IMG_show border=0 src=http://i8.umei.cc//img2012/2013/04/15/017BT813/0000.jpg alt='[b] x 2013.04.26 No.813 Vicni [93P]'>

        img_info = re.search(r'IMG_show.*?src=([^\s]*\.jpg)\s+alt=\'[^>]*?No\.(\d+)[^>]*?\[(\d+)P\]\'', url_content)
        if img_info :
            img_order = img_info.group(2)
            if img_order > last_order :
                result.append({'img':img_info.group(1), 'dir': img_order,'total': img_info.group(3), 'current':0})
                print 'Get One Rule: ', img_order
            else:
                print 'Discard Unavailable Rule: ', img_order
        
    save_data(each_star_file, result )
    print 'Got Rule saved in: ', each_star_file
    return result

#try to load img rule of each star 
star_rule = load_data(each_star_file)
if  star_rule:
    print 'Got Rule From Local '
else:
    star_urls = getAllStar(base_url)
    #pprint.pprint(star_urls, width=10, indent=2)
    #exit()

    star_rule = findImgRule(star_urls)
    #pprint.pprint(star_rule, width=10)
    #exit()

    os.remove(star_list_file)
    print 'Removed List Data'

import sys
rp_count = 0
def rp_fn(blocknum, blocksize, totalsize):
    global rp_count
    percent = 20.0 * blocknum * blocksize / totalsize
    percent = 20 if int(percent)>20 else int(percent)
    for i in range(percent - rp_count):
        print '>',
    rp_count = percent

def fetchImg(star_data, target):
    if not os.path.exists(target):
        os.mkdir(target, 0744)

    max_order = default_order 
    for index, single in enumerate(star_data):
        if max_order < single['dir']:
            max_order = single['dir']

        img_prefix = os.path.dirname(single['img']) + '/'
        #python is a strong type language
        start = int(single['current'])
        end = int(single['total']) + 1

        for order in range(start, end):

            sub_dir = target + single['dir'] + '/'
            if not os.path.exists(sub_dir):
                os.mkdir(sub_dir, 0744)

            fname = formatNum(order) + '.jpg'
            url = img_prefix + fname
            print '\n';
            print '{0:-^39}'.format('Fetch ' + single['dir'] + '/' + fname );
            if not os.path.exists(sub_dir+fname):
                alexDown(url, sub_dir + fname)
                randomSleep = randint(1, 5)
                time.sleep(randomSleep)

            if  os.path.exists(sub_dir+fname):
                each_size = os.path.getsize(sub_dir + fname)/1000
                if  each_size < 100:
                    os.remove(sub_dir + fname)
                    print fname, ' has been deleted.'

            #record status
            #modify true arguments will change the passed arguments
            star_data[index]['current'] = order + 1
            save_data(each_star_file, star_data )

            if  order == end - 1:
                #del star_data[index]
                print '\nGot this group, Now fetch next group \n';

    print 'All Downloaded'
    os.remove(each_star_file)
    print 'Removed Rule Data'
    status = {'last_order': max_order}
    save_data(status_file, status )
    print 'Record Last order: ', max_order


fetchImg(star_rule, down_dir)
