from __future__ import unicode_literals

import json
import os
import sys
from argparse import ArgumentParser
import pandas as pd
from base_content import *
from cf import *
import random
from data_acquire_store.recommender.sql2df import *
from data_acquire_store.netease.user_data import *


import requests
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage, VideoMessage, FileMessage, StickerMessage,
    StickerSendMessage, TemplateSendMessage, PostbackEvent, PostbackAction, ButtonsTemplate,
    CarouselTemplate, CarouselColumn, URIAction
)

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = 'ca32938ed12b316917179536814633f5'
channel_access_token = 'leBxqANNw4mlbcYnXBsg7fvAHRZmfHkIazjnCvskr4tLFzlgndR1Hw/QT1AAvnHogl6VGmYD477lk8UUKH0WWecD33eeyKKe9qMsd1v5jst6wHJW2bAN1vrdPWp5TB0BchjrWLDl7AgTI9iF9DlDMgdB04t89/1O/w1cDnyilFU='

# obtain the port that heroku assigned to this app.
heroku_port = os.getenv('PORT', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if isinstance(event, PostbackEvent):
            handle_PostbackEvent(event)
            continue
        if isinstance(event.message, TextMessage):
            handle_TextMessage(event)
            continue
        if not isinstance(event, MessageEvent):
            continue
        if isinstance(event.message, ImageMessage):
            handle_ImageMessage(event)
        if isinstance(event.message, VideoMessage):
            handle_VideoMessage(event)
        if isinstance(event.message, FileMessage):
            handle_FileMessage(event)
        if isinstance(event.message, StickerMessage):
            handle_StickerMessage(event)
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

    return 'OK'


def handle_PostbackEvent(event):
    msg = ''
    if event.postback.data == "input":
        msg = TextSendMessage('Please input the user id:')
    elif event.postback.data == "OK":
        msg = TextSendMessage(text='The format is as follows. \n张学友,周杰伦,林俊杰,陈奕迅,Michael Jackson')
    elif event.postback.data == 'new':
        msg = TemplateSendMessage(
            alt_text='Buttons template',
            template=ButtonsTemplate(
                thumbnail_image_url='https://store-images.s-microsoft.com/image/apps.36553.9007199266243310.0768217f-be29-4e43-8b75-082f6578f21a.50f2f2dc-1363-4189-80b6-314bcecda675?mode=scale&q=90&h=300&w=300',
                text='Please enter your five preferred singers.',
                actions=[
                    PostbackAction(
                        label='OK',
                        display_text='OK',
                        data='OK'
                    )
                ]
            )
        )
    elif event.postback.data == "old":
        line_bot_api.push_message(event.source.user_id,
                                  TextSendMessage(text='Recommending...'))
        songs = list()
        for i in range(10):
            url = 'https://musicapi.leanapp.cn/song/detail?ids=1436709403'
            html = requests.get(url).text
            song = json.loads(html)
            song_img = song['songs'][0]['al']['picUrl']
            song_img = song_img.replace('http', 'https')
            songs.append(CarouselColumn(
                thumbnail_image_url=song_img,
                title='夏天的风',
                text='温岚',
                actions=[
                    URIAction(
                        label='Listen',
                        uri='https://music.163.com/#/song?id=1436709403'
                    )
                ]
            ))
        msg = TemplateSendMessage(
            alt_text='Carousel template',
            template=CarouselTemplate(
                columns=songs
            )
        )
    else:
        msg = TextSendMessage('error')
    line_bot_api.reply_message(event.reply_token, msg)


# Handler function for Text Message
def handle_TextMessage(event):
    if event.message.text.isdigit():
        line_bot_api.push_message(event.source.user_id,
                                  TextSendMessage(text='Recommending...'))
        user_id = int(event.message.text)
        # print('----------------------------')
        # print(type(user_id))

        # xb
        records_list = music_records_list()
        if str(userid) in records_list:
            user_favourite_list=code_favourite_list(userid)
            user_ranklist = code_ranklist(userid)
            user_music_record=code_music_records(userid)

        else:
            u = user_data()
            u.get_user_target(user_id)

            user_favourite_list=code_favourite_list(user_id)
            user_ranklist = code_ranklist(user_id)
            user_music_record=code_music_records(user_id)

        rs_songs_cf = recommend('music_record.csv', user_id, dataframe = user_music_record)
        songs = pd.read_csv('song_detail.csv')
        artists, tags = user_feature(user_favourite_list, user_ranklist)
        rs_songs_cont = rs_content(songs, artists, tags)
        output_songs = []
        if len(rs_songs_cf) > 5:
            output_songs.extend(random.sample(list(rs_songs_cf), 5))
            output_songs.extend(random.sample(list(rs_songs_cont), 5))
        else:
            output_songs.extend(list(rs_songs_cf))
            output_songs.extend(random.sample(list(rs_songs_cont), 10 -len(rs_songs_cf)))

        result = output_songs

        songs = list()
        for item in result:
            url = 'https://musicapi.leanapp.cn/song/detail?ids=' + str(item[0])
            html = requests.get(url).text
            song = json.loads(html)
            song_img = song['songs'][0]['al']['picUrl']
            song_img = song_img.replace('http', 'https')
            songs.append(CarouselColumn(
                thumbnail_image_url=song_img,
                title=item[1],
                text=item[2],
                actions=[
                    URIAction(
                        label='Listen',
                        uri='https://music.163.com/#/song?id='+ str(item[0])
                    )
                ]
            ))
        message = TemplateSendMessage(
            alt_text='Carousel template',
            template=CarouselTemplate(
                columns=songs
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            message
        )
    elif event.message.text.count(',') == 4:
        line_bot_api.push_message(event.source.user_id,
                                  TextSendMessage(text='Recommending...'))
        data = event.message.text
        singers = list()
        data = data.split(',')
        for name in data:
            singers.append(name)
        
        # xb
        songs = pd.read_csv('song_detail.csv')
        rs_songs_cold = rs_content_cold(songs, singers, n = 5)
        result = random.sample(list(rs_songs_cold), 10)

        songs = list()
        for item in result:
            url = 'https://musicapi.leanapp.cn/song/detail?ids=' + str(item[0])
            html = requests.get(url).text
            song = json.loads(html)
            song_img = song['songs'][0]['al']['picUrl']
            song_img = song_img.replace('http', 'https')
            songs.append(CarouselColumn(
                thumbnail_image_url=song_img,
                title=item[1],
                text=item[2],
                actions=[
                    URIAction(
                        label='Listen',
                        uri='https://music.163.com/#/song?id='+ str(item[0])
                    )
                ]
            ))
        message = TemplateSendMessage(
            alt_text='Carousel template',
            template=CarouselTemplate(
                columns=songs
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            message
        )
    else:
        line_bot_api.push_message(event.source.user_id,
                                  TextSendMessage(text='Welcome to NetEase Cloud Music Recommendation Chatbot!'))
        msg = TemplateSendMessage(
            alt_text='Buttons template',
            template=ButtonsTemplate(
                thumbnail_image_url='https://store-images.s-microsoft.com/image/apps.36553.9007199266243310.0768217f-be29-4e43-8b75-082f6578f21a.50f2f2dc-1363-4189-80b6-314bcecda675?mode=scale&q=90&h=300&w=300',
                title='Menu',
                text='Please select the user type',
                actions=[
                    PostbackAction(
                        label='New subscriber',
                        display_text='New subscriber',
                        data='new'
                    ),
                    PostbackAction(
                        label='User',
                        display_text='User',
                        data='input'
                    )
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            msg
        )


# Handler function for Sticker Message
def handle_StickerMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id=event.message.package_id,
            sticker_id=event.message.sticker_id)
    )


# Handler function for Image Message
def handle_ImageMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice image!")
    )


# Handler function for Video Message
def handle_VideoMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice video!")
    )


# Handler function for File Message
def handle_FileMessage(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="Nice file!")
    )


if __name__ == "__main__":
    userid = 0
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(host='0.0.0.0', debug=options.debug, port=heroku_port)
