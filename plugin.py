# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import logging
import json

# third-party
import requests
from flask import Blueprint, request, Response, send_file, render_template, redirect, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_socketio import SocketIO, emit, send

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, socketio, check_api
from framework.util import Util, AlchemyEncoder
from system.model import ModelSetting as SystemModelSetting

# 로그
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

# 패키지
from .model import ModelSetting
from .logic import Logic
from .logic_hdhomerun import LogicHDHomerun

blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))

def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()

plugin_info = {
    'version' : '0.1.0.0',
    'name' : 'HDHomerun',
    'category_name' : 'tv',
    'icon' : '',
    'developer' : 'soju6jan',
    'description' : 'TVH 없이 HDHomerun을 이용할 수 있는 플러그인',
    'home' : 'https://github.com/soju6jan/hdhomerun',
    'more' : '',
}
#########################################################

menu = {
    'main' : [package_name, 'HDHomerun'],
    'sub' : [
        ['setting', '설정'], ['channel', '채널'], ['log', '로그']
    ],
    'category' : 'tv',
}


#########################################################
# WEB Menu                                    
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/channel' % package_name)


@blueprint.route('/<sub>')
@login_required
def first_menu(sub):
    if sub == 'setting':
        try:
            arg = ModelSetting.to_dict()
            ddns = SystemModelSetting.get('ddns')
            arg['m3u'] = '%s/%s/api/m3u' % (ddns, package_name)
            arg['xmltv'] = '%s/epg/api/%s' % (ddns, package_name)
            arg['proxy'] = '%s/%s/proxy' % (ddns, package_name)
            if SystemModelSetting.get_bool('auth_use_apikey'):
                apikey = SystemModelSetting.get('auth_apikey')
                arg['m3u'] += '?apikey={apikey}'.format(apikey=apikey)
                arg['xmltv'] += '?apikey={apikey}'.format(apikey=apikey)
            return render_template('%s_%s.html' % (package_name, sub), arg=arg)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'channel':
        try:
            arg = {}
            return render_template('%s_%s.html' % (package_name, sub), arg=arg)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    elif sub == 'proxy':
        return redirect('/%s/proxy/discover.json' % package_name) 
    return render_template('sample.html', title='%s - %s' % (package_name, sub))


#########################################################
# For UI                                                            
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
@login_required
def ajax(sub):
    logger.debug('%s AJAX sub:%s', package_name, sub)
    try:     
        if sub == 'setting_save':
            try:
                ret = ModelSetting.setting_save(request)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
                return jsonify('fail')
        elif sub == 'read_data':
            try:
                data_filename = request.form['data_filename']
                import framework.common.util as CommonUtil
                ret = CommonUtil.read_file(data_filename)
                return jsonify(ret.split('\n'))
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'load_data':
            try:
                ret = LogicHDHomerun.load_data()
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())

        elif sub == 'load_db':
            try:
                ret = {}
                ret['setting'] = ModelSetting.to_dict()
                tmp = LogicHDHomerun.channel_list()
                ret['data'] = [x.as_dict() for x in tmp]
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'group_sort':
            try:
                
                ret = {}
                ret['setting'] = ModelSetting.to_dict()
                ret['data'] = LogicHDHomerun.group_sort()
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'save':
            try:
                LogicHDHomerun.save(request)
                ret = {}
                ret['setting'] = ModelSetting.to_dict()
                tmp = LogicHDHomerun.channel_list()
                ret['data'] = [x.as_dict() for x in tmp]
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'match_for_epg_name':
            try:
                for_epg_name = request.form['for_epg_name']
                channel_id = request.form['id']
                ret = LogicHDHomerun.match_for_epg_name(channel_id, for_epg_name)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'delete':
            try:
                channel_id = request.form['id']
                ret = {}
                ret['ret'] = LogicHDHomerun.delete(channel_id)
                ret['setting'] = ModelSetting.to_dict()
                tmp = LogicHDHomerun.channel_list()
                ret['data'] = [x.as_dict() for x in tmp]
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'ip_fix':
            try:
                deviceid = request.form['deviceid']
                tmp = deviceid.find('192')
                if tmp != -1:
                    deviceid = deviceid[tmp:]
                else:
                    deviceid = deviceid.lower().replace('https://', '').replace('http://', '')
                ModelSetting.set('deviceid', deviceid)
                ret = LogicHDHomerun.ip_fix(deviceid)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())


    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())

#########################################################
# API
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
@check_api
def api(sub):
    if sub == 'm3u':
        try:
            return LogicHDHomerun.get_m3u()
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

#########################################################
# Proxy
#########################################################
@blueprint.route('/proxy/<sub>', methods=['GET', 'POST'])
def proxy(sub):
    logger.debug('proxy %s %s', package_name, sub)
    # 설정 저장
    if sub == 'discover.json':
        try:
            ddns = SystemModelSetting.get('ddns')
            data = {"FriendlyName":"HDHomeRun CONNECT","ModelNumber":"HDHR4-2US","FirmwareName":"hdhomerun4_atsc","FirmwareVersion":"20190621","DeviceID":"104E8010","DeviceAuth":"UF4CFfWQh05c3jROcArmAZaf","BaseURL":"%s/hdhomerun/proxy" % ddns,"LineupURL":"%s/hdhomerun/proxy/lineup.json" % ddns,"TunerCount":20}
            return jsonify(data)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'lineup_status.json':
        try:
            data = {"ScanInProgress":0,"ScanPossible":1,"Source":"Cable","SourceList":["Antenna","Cable"]}
            return jsonify(data)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    elif sub == 'lineup.json':
        try:
            lineup = []
            channel_list = LogicHDHomerun.channel_list(only_use=True)
            ddns = SystemModelSetting.get('ddns')
            for c in channel_list:
                lineup.append({'GuideNumber': str(c.ch_number), 'GuideName': c.scan_name, 'URL': c.url})
            return jsonify(lineup)
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())