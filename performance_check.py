#! /usr/bin/python
# -*- coding: UTF-8 -*-
import time
import random
import threading
import json
import sys
import os
import subprocess
import dumpsys_app_debug_info
from optparse import OptionParser
import re

class MonkeyThread(threading.Thread):
    def __init__(self, adbshell):
        threading.Thread.__init__(self)
        self.adbshell_ = adbshell

    def run(self):
        self._running = True
 	while self._running:
            # key = random.randint(19, 22)
            # cmd = self.adbshell_ +' input keyevent '
            # for i in range(0, random.randint(1, 10)):
            #     cmd += str(key) + ' '
            yStart = random.randint(300, 2000)
            yEnd = random.randint(300, 2000)
            if abs(yStart - yEnd) > 100: 
            	cmd = self.adbshell_ +' input swipe 100 %d 100 %d '%(yStart, yEnd)
            	os.system(cmd)


def getOptions():
    usage="performance_check.py [Options] package|package/activity"
    parser = OptionParser(usage)
    parser.add_option('-c', '--config', dest='config', help='limit config dir')
    parser.add_option('-s', '--select', dest='select', help='adb devices select')
    parser.add_option('-p', '--path', dest='path', help='output file path')
    return parser.parse_args()

def popenToRunCommand(cmd):
    return subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def computeStartTime(package, activity, adbshell):
    def standardization(cast_time):
        cast_time = cast_time.replace('ms','').replace(')', '')
        return float(cast_time.replace('s','.') if 's' in cast_time else '0.' + cast_time)

    result = ""

    # 使用-W参数输出
    if activity==None:
    	result = os.popen(adbshell + ' am start -W ' + package).read()
    else:
    	result = os.popen(adbshell + ' am start -W -n %s/%s' % (package,activity)).read()
    print(result)
    time = re.search( r'TotalTime: (.*)', result, re.M|re.I)
    print(time.group(1))
    return float(time.group(1))

    # 从log中获取
    # os.system(adbshell + ' logcat -c')
    # os.system(adbshell + ' am force-stop ' + package)

    # if activity==None:
    #     os.system(adbshell + ' am start ' + package)
    # else:
    #     os.system(adbshell + ' am start -n %s/%s' % (package,activity))

    # Android 10启动时间log改为ActivityTaskManager
    # popen = popenToRunCommand(adbshell + ' logcat -s ActivityTaskManager')
    # line = popen.stdout.readline()
    # while 'Displayed' not in line:
    #     line = popen.stdout.readline()
    # popen.kill()
    # print(line)
    # return standardization(line[line.rfind('+')+1:].strip())

def getSystemMemoryInfo(adbshell):
    def getMemoryMb(info):
        end = info.find('kB') if 'kB' in info else info.find('K')
        return float(info[info.find(':')+1 : end].replace(',', '').strip()) / 1024
    popen = popenToRunCommand(adbshell + ' dumpsys meminfo')
    result = [None, None, None]
    for line in popen.stdout.readlines():
        if 'Total RAM:' in line:
            result[0] = getMemoryMb(line)
        elif 'Used RAM:' in line:
            result[1] = getMemoryMb(line)
        elif 'Free RAM:' in line:
            result[2] = getMemoryMb(line)
    popen.kill()
    return result

def getRunningActivity(adbshell):
    cmd = adbshell + ' dumpsys activity'
    popen = popenToRunCommand(cmd)
    line = popen.stdout.readline()
    while 'Run' not in line or 'ActivityRecord' not in line:
        line = popen.stdout.readline()
    popen.kill()
    return line[line.find('ActivityRecord') : line.find('}')+1]

def getBroadName(adbshell):
    # 获取板卡名称，用于查询limits指标
    cmd = adbshell +' getprop xxxx'
    popen = popenToRunCommand(cmd)
    name = popen.stdout.readline().strip()
    popen.kill()
    return name

def getMemorySize(adbshell):
    # 获取板卡内存，用于查询limits指标
    cmd = adbshell + ' getprop xxx'
    popen = popenToRunCommand(cmd)
    size = popen.stdout.readline().strip()
    popen.kill()
    if len(size)==0:
        cmd = adbshell + ' getprop xxx'
        popen = popenToRunCommand(cmd)
        name = popen.stdout.readline().strip()
        popen.kill()
        size = '1G' if '_1G_' in name else '512M'

    return size

def getCpuUse(package, adbshell):
    top_popen = popenToRunCommand(adbshell + ' top')
    cpu = dumpsys_app_debug_info.getCpuUse(package, top_popen, adbshell)
    top_popen.kill()
    return None if cpu==None else float(cpu.replace('%', ''))

def getCurrentStatus(package, adbshell):
    print("get cpu...")
    cpu = getCpuUse(package, adbshell)
    while cpu == None:
        print("get cpu...")
        cpu = getCpuUse(package, adbshell)
    print("get app memory...")
    app_memory = float(dumpsys_app_debug_info.getMemory(package, adbshell)) / 1024
    print("get fps...")
    fps = float(dumpsys_app_debug_info.getGfxFps(package, adbshell))
    print("get system memory...")
    sys_memory_info = getSystemMemoryInfo(adbshell)
    print("get running activity...")
    activity = getRunningActivity(adbshell)
    return [activity, cpu, fps, app_memory] + sys_memory_info

def testStartTime(package, activity, adbshell, test_count):
    result = []
    for i in range(0, test_count):
    	os.system(adbshell + ' am force-stop ' + package)
    	time.sleep(3)
        result.append(computeStartTime(package, activity, adbshell))
        time.sleep(3)
    return result

def testHotStartTime(package, activity, adbshell, test_count):
    result = []
    for i in range(0, test_count):
        os.system(adbshell + ' input keyevent 3')
        time.sleep(3)
        result.append(computeStartTime(package, activity, adbshell))
        time.sleep(3)
    return result

def testStatus(package, adbshell, count):
    result = []
    for i in range(0, count):
        status = getCurrentStatus(package, adbshell)
        print(status)
        result.append(status)
        time.sleep(3)
    return result

def getLimits(broad_name, adbshell, config_dir):
    none_config = {
            'startTime': None,
            'hotStartTime': None,
            'static': [None, None, None, None, None, None, None],
            'running': [None, None, None, None, None, None, None],
            'average': [None, None, None, None, None, None, None]
    }

    if config_dir == None:
        return none_config

    path = os.path.join(config_dir, broad_name+'_'+getMemorySize(adbshell)+'.json')
    print(path)
    if not os.path.exists(path):
        return none_config

    with open(path) as f:
        config = json.loads(''.join(f.readlines()))
        return {
            'startTime': config['startTime'],
            'hotStartTime': config['hotStartTime'],
            'static': [None, config['static'].get('cpu'), None, config['static'].get('appMomery'), None, None, None],
            'running': [None, config['running'].get('cpu'), None, config['running'].get('appMomery'), None, None, None],
            'average': [None, config['average'].get('cpu'), None, config['average'].get('appMomery'), None, None, None]
        }

def genResultMarkdown(package, adbshell, config_dir, path, broad_name, start_times, hot_start_times, status_start, status_running, status_calm_down):
    def addStartTime(start_times, out, limit):
        out.write('# 冷启动时间:\n||时间|\n|:-:|:-:|\n')
        all_time = 0
        for index, cast_time in enumerate(start_times):
            all_time += cast_time
            if limit != None and cast_time > limit: out.write('|第 %d 次| <font color=red>%fms</font>|\n' % (index+1, cast_time))
            else: out.write('|第 %d 次| %fms|\n' % (index+1, cast_time))

        average = all_time / len(start_times)
        if limit != None and average > limit: out.write('|平均时间|<font color=red>%fs</font>|\n\n' % (all_time / len(start_times)))
        else: out.write('|平均时间|%fms|\n\n' % (all_time / len(start_times)))

    def addHotStartTime(start_times, out, limit):
        out.write('# 热启动时间:\n||时间|\n|:-:|:-:|\n')
        all_time = 0
        for index, cast_time in enumerate(start_times):
            all_time += cast_time
            if limit != None and cast_time > limit: out.write('|第 %d 次| <font color=red>%fms</font>|\n' % (index+1, cast_time))
            else: out.write('|第 %d 次| %fms|\n' % (index+1, cast_time))

        average = all_time / len(start_times)
        if limit != None and average > limit: out.write('|平均时间|<font color=red>%.3fs</font>|\n\n' % (all_time / len(start_times)))
        else: out.write('|平均时间|%fms|\n\n' % (all_time / len(start_times)))

    def highlightWhenAbove(desc, info, limit):
        return desc if limit == None or info <= limit else '<font color=red>%s</font>' % desc

    def getStatusDescription(index, info, limits):
        if index == 0: return info
        elif index == 1: return highlightWhenAbove('%.3f%%' % info, info, limits[index])
        elif index == 2: return highlightWhenAbove('%.3f' % info, info, limits[index])
        else: return highlightWhenAbove('%.3fM' % info, info, limits[index])

    def addStatusInfo(totals, title, status,limits, out):
        for s in status:
            for i in range(1, len(s)):
                totals[i-1] += s[i]
            out.write('|%s|' % title)
            out.write('|'.join([getStatusDescription(index, info, limits) for index,info in enumerate(s)]))
            out.write('|\n')
        return len(status)

    path = path if path != None else '%s_in_%s.md' % (package.replace('.','_'), broad_name)
    out = open(path, 'w')

    out.write('# 板卡:\n%s\n\n' % broad_name.replace('_','\\_'))
    out.write('# 包名:\n%s\n\n' % package)

    limits = getLimits(broad_name, adbshell, config_dir)

    addStartTime(start_times, out, limits['startTime'])
    addHotStartTime(hot_start_times, out, limits['hotStartTime'])

    out.write('# 系统状态:\n')
    out.write('||前台activity|cpu|fps|应用内存|系统总内存|系统使用内存|系统剩余内存|\n')
    out.write('|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n')

    totals = [0,0,0,0,0,0]
    count = 0
    count += addStatusInfo(totals, '静止状态', status_start, limits['static'], out)
    count += addStatusInfo(totals, '运行状态', status_running, limits['running'], out)
    count += addStatusInfo(totals, '静止状态', status_calm_down, limits['static'], out)

    averages = tuple([getStatusDescription(index+1, total/count, limits['average']) for index,total in enumerate(totals)])
    out.write('|平均值||%s|%s|%s|%s|%s|%s|\n' % averages)
    out.close()

if __name__ == '__main__':
    option, args = getOptions()
    if '/' in args[0]:
        component = args[0].split('/')
        package = component[0]
        activity = component[1]
    else:
        package = args[0]
        activity = None

    adbshell = 'adb shell ' if option.select==None else 'adb -s %s shell ' %  option.select
    os.system(adbshell + ' setprop debug.hwui.profile visual_bars')

    print('wait to reset 5 times...')
    start_times = testStartTime(package, activity, adbshell, 5)
    print(start_times)

    print('wait to reset 5 times for hot...')
    hot_start_times = testHotStartTime(package, activity, adbshell, 5)
    print(hot_start_times)

    print('wait to get static status 5 times...')
    status_start = testStatus(package, adbshell, 5)

    print('wait to get running status 10 times...')
    thread = MonkeyThread(adbshell)
    thread.start()
    status_running = testStatus(package, adbshell, 10)
    thread._running = False

    print('wait to get static status 5 times...')
    status_calm_down = testStatus(package, adbshell, 5)

    genResultMarkdown(package, adbshell, option.config, option.path, getBroadName(adbshell), start_times, hot_start_times, status_start, status_running, status_calm_down)
    print('finish')
