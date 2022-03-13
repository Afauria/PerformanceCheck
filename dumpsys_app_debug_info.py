#! /usr/bin/python
# -*- coding:utf-8 -*-

import os
import sys
import time
import subprocess
from optparse import OptionParser

def getOptions():
    usage="dumpsys_app_debug_infp.py [Options] package"
    parser = OptionParser(usage)
    parser.add_option("-a", "--all", action="store_true", help="enable all debug info")
    parser.add_option("-v", "--visual_bars", action="store_true", help="show gpu visual bar")
    parser.add_option("-o", "--overdraw", action="store_true", help="enable gpu overdraw")
    parser.add_option("-f", "--fps", action="store_true", help="show fps compute")
    parser.add_option("-c", "--cpu", action="store_true", help="show cpu utilization percentage")
    parser.add_option("-m", "--memory", action="store_true", help="show memory used")
    return parser.parse_args()

def getColumnData(line, split=' '):
    return [item for item in line.strip().split(split) if len(item)>0]

def getMemory(package, adbshell='adb shell '):
    cmd = adbshell + ' dumpsys meminfo ' + package
    popen = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = popen.stdout.readlines()
    popen.kill()
    for line in lines:
        if(line.strip().startswith('TOTAL')):
            return getColumnData(line)[1]

def beginTop(package):
    return subprocess.Popen('adb shell top'.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def getPid(package, adbshell='adb shell '):
    cmd = adbshell + ' ps | grep ' + package
    popen = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    line = popen.stdout.readline()
    popen.kill()
    return getColumnData(line)[1]

def getCpuUse(package, topPipe, adbshell='adb shell '):
    def getCpuIndex(line):
        for index,item in enumerate(getColumnData(line)):
            if "CPU" in item:
                return index
    pid = getPid(package, adbshell)
    cpuIndex = 0
    columnData = None
    line = topPipe.stdout.readline()
    empty_count = 0
    while package not in line:
        line = topPipe.stdout.readline()
        if len(line)==0:
            empty_count = empty_count + 1
        else:
            empty_count = 0
        if empty_count > 10:
            return None
        columnData = getColumnData(line)
        if len(columnData)>1 and (columnData[0].startswith('PID') or columnData[1].startswith('PID')):
            cpuIndex = getCpuIndex(line)
        elif len(columnData)>0 and columnData[0]==pid:
            break
    return columnData[cpuIndex]

def getGfxFps(package, adbshell='adb shell '):
    cmd = adbshell + ' dumpsys gfxinfo ' + package
    popen = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = popen.stdout.readlines()
    popen.kill()
    beginCount = -1
    fps = 0
    count = 0
    for line in lines:
        if line.startswith('Profile data in ms:'):
            beginCount = 3
        elif beginCount > 0:
            beginCount -= 1
        elif line=='\r\n' or line=='\n':
            beginCount = -1
        elif beginCount==0:
            fps += 1000 / sum([float(v) for v in getColumnData(line, '\t')])
            count += 1
    if count > 0:
        return str(fps / count)
    return'0'

def getLauncherFps(package):
    cmd = 'adb shell ls /data/data/%s/files/' % package
    popen = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines = popen.stdout.readlines()
    popen.kill()
    for line in lines:
        if 'fps' in getColumnData(line):
            cmd = 'adb shell cat /data/data/%s/files/fps' % package
            popen = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            line = popen.stdout.readline()
            popen.kill()
            return line
    return 'UNKNOW'

def dumpsysDebugInfo(cpu, memory, fpsForGfx, getGfxFps):
    fmt = ''
    arg = []
    if cpu != None:
        fmt += 'CPU=%s    '
        arg.append(cpu)

    if memory != None:
        fmt += 'MEMORY=%s    '
        arg.append(memory)

    if fpsForGfx != None:
        fmt += 'GFX_FPS=%s    '
        arg.append(fpsForGfx)

    if fps != None:
        fmt += 'FPS=%s'
        arg.append(fps)

    print(fmt % tuple(arg))


if __name__ == '__main__':
    option, args = getOptions()

    if option.all:
        option.overdraw = True
        option.visual_bars = True
        option.fps = True
        option.memory = True
        option.cpu = True
    APP_PACKAGE = args[0]

    # 过度绘制
    if option.overdraw:
        os.system('adb shell setprop debug.hwui.overdraw show')

    # gpu柱状图
    if option.visual_bars:
        os.system('adb shell setprop debug.hwui.profile visual_bars')

    # fps计算
    if option.fps:
        os.system('adb shell setprop debug.fps 1')

    if option.cpu:
        topPipe = beginTop(APP_PACKAGE)

    cpu = None
    memory = None
    fpsForGfx = None
    fps = None
    while(True):
        if option.cpu:
            cpu = getCpuUse(APP_PACKAGE, topPipe)
        if option.memory:
            memory = getMemory(APP_PACKAGE)
        if option.visual_bars:
            fpsForGfx = getGfxFps(APP_PACKAGE)
        if option.fps:
            fps = getLauncherFps(APP_PACKAGE)
        dumpsysDebugInfo(cpu, memory, fpsForGfx, fps)

        if not option.cpu:
            time.sleep(2)
