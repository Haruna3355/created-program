import sys, os
import time
import traceback
import numpy as np
import math as m
import pandas as pd
import datetime

import socket
from config import HOST_IP, HOST_PORT
import pyrealsense2 as rs
from multiprocessing import Process

from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.config import Config
from kivy.lang import Builder


#ウインドウの幅と高さの設定
Config.set('graphics', 'width', 600)
Config.set('graphics', 'height', 500)
#1でサイズ変更可、0はサイズ変更不可
Config.set('graphics', 'resizable', 1)

# -------------------------- Realsense初期設定 --------------------------
pipe = rs.pipeline()
cfg = rs.config()
cfg.enable_stream(rs.stream.pose)
pipe.start(cfg)

# -------------------------- Socket通信設定 --------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST_IP, HOST_PORT))

max_walk = 5

# -------------------------- 変数定義 --------------------------
csv_dir = "."
dt_now = datetime.datetime.now()
csv_name = "ap_con_"+dt_now.strftime('%m-%d-%H%M')+".csv"


savedata_pose_x = []
savedata_pose_y = []
savedata_pose_z = []
savedata_yaw = []
savedata_command = []

savedata = [
    savedata_pose_x,
    savedata_pose_y,
    savedata_pose_z,
    savedata_yaw,
    savedata_command
]

columns = [
    "pose_x",
    "pose_y",
    "pose_z",
    "yaw",
    "command"
]


class Widget(Widget):
    socket_command = b"none"

class RealsenseWidget(Label):
    text = StringProperty("")

    def __init__(self, **kwargs):
        super(RealsenseWidget, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 0.1)   #保存間隔

    def update(self, dt):
        # -------------------------- Realsenseからデータ取得 --------------------------
        frames = pipe.wait_for_frames()
        pose = frames.get_pose_frame()
        data = pose.get_pose_data()
        walk_distance = data.translation.z
        w = data.rotation.w
        x = -data.rotation.z
        y = data.rotation.x
        z = -data.rotation.y
        yaw   =  m.atan2(2.0 * (w*z + x*y), w*w + x*x - y*y - z*z) * 180.0 / m.pi


        # -------------------------- ソケットコマンドの条件分岐 --------------------------
        if pose:
            self.text = str(walk_distance)
        else:
            self.text = "wait second..."
        
        if Widget.socket_command == b"none":
            command = Widget.socket_command
        elif  Widget.socket_command == b"off":
            command = Widget.socket_command
            s.send(command)
            Widget.socket_command = b"none"

        elif Widget.socket_command == b"finish":
            print("finish")
            command = Widget.socket_command
            s.send(command)
            s.close() 
            Widget.socket_command = b"none"

        elif Widget.socket_command == b"on": 
            # start_distance = walk_distance
            if -walk_distance <= 1.0:
                duty = 0
                print(f"Duty ratio : {duty}")
                command = f"on {duty}".encode()
                s.send(command)
            elif -walk_distance <= 2.0:
                duty = 10
                print(f"Duty ratio : {duty}")
                command = f"on {duty}".encode()
                s.send(command)
            elif 2.0 < -walk_distance <= 2.5:
                duty = 30
                print(f"Duty ratio : {duty}")
                command = f"on {duty}".encode()
                s.send(command)
            elif 2.5 < -walk_distance <= 3.0:
                duty = 50
                print(f"Duty ratio : {duty}")
                command = f"on {duty}".encode()
                s.send(command)
            # elif 3.0 < -walk_distance <= 3.5:
            #     duty = 70
            #     print(f"Duty ratio : {duty}")
            #     command = f"on {duty}".encode()
            #     s.send(command)
            elif 3.0 < -walk_distance:
                duty = 100
                print(f"Duty ratio : {duty}")
                command = f"on {duty}".encode()
                s.send(command)

            """
            duty = abs(walk_distance) // (max_walk / 10) * 10
            duty = duty if duty <= 100 else 100
            duty = int(duty)
            print(f"Duty ratio : {duty}")
            command = f"on {duty}".encode()
            """
            # s.send(command)
        else:
            pass

        # -------------------------- データの格納 --------------------------
        data = [
            data.translation.x,
            data.translation.y,
            data.translation.z,
            yaw,
            command
        ]
        for sav, d in zip(savedata, data): sav.append(d)

class ButtonWidget(Widget):
    def __init__(self, **kwargs):
        super(ButtonWidget, self).__init__(**kwargs)

    def press1(self):
        Widget.socket_command = b"on"
        self.ids.rs_widget.text = "Vibrate turn on"

    def press2(self):
        Widget.socket_command = b"off"
        self.ids.rs_widget.text = "Vibrate turn off"

    def press3(self):
        Widget.socket_command = b"finish"
        self.ids.rs_widget.text = "Connection done"

class SuzukiApp(App):
    def build(self):
        self.title = "window"
        return ButtonWidget()

    def stop(self, *largs):
        pipe.stop()
        return super().stop(*largs)

if __name__ == '__main__':
    try:
        SuzukiApp().run()
    except OSError:
        print("OSError: [WinError 10038] ソケット以外のものに対して操作を実行しようとしました。")
        print("OSEErro: が、無視してプログラムを続行します")
    except:
        t = traceback.format_exc()
        print(t)
    finally:
        data = np.array(savedata)
        df = pd.DataFrame(data.T, columns=columns, )
        df.to_csv(os.path.join(csv_dir, csv_name), index=False)
