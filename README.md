# 介绍

PerformanceCheck是一个性能检测脚本。通过adb发送指令，模拟事件，统计应用启动时长、内存占用、FPS等，并打开过度绘制和FPS柱状图。

执行脚本之后会输出Markdown报表。

做了一些修改隐藏了一些信息，可能会有一点小问题，主要用于参考。有空再调试下。

# 参数

performance_check.py脚本的参数如下:

```shell
Usage: performance_check.py [Options] <package>|<package/activity>

Options:
  -h, --help            show this help message and exit
  -c CONFIG, --config=CONFIG
                        limit config dir # 用于指定配置文件的目录，目录下是针对某个板卡的性能指标
  -s SELECT, --select=SELECT # 用于指定adb设备，当同时连接多个adb设备的时候可以使用
                        adb devices select
```

示例:

> ./performance_check.py -c ./limits/ com.afauria.performance.android_app/com.afauria.performance.android_app.MainActivity -s 172.19.134.23:5555


# 性能指标配置

不同板卡的整体性能和统计方式可能不一样，不同应用指标的限制可能也不一样。为了检测是否超标，可以通过c/config参数指定性能指标目录，配置文件名称格式为：`板卡名_内存大小.json`，如果脚本检测出来的值超标，就会标红。

性能指标配置如下:

```json
{
	"startTime" : 2.0, //启动时间
	"static": {
		"cpu": 0, //静止状态下CPU占用
		"appMomery": 55 //静止状态下的内存占用
	},
	"running": {
		"appMomery": 75 //运行状态下的内存占用
	},
	"average": {
		"appMomery": 40 //平均内存占用
	}
}
```
