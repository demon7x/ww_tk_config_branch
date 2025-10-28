# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
App Launch Hook

This hook is executed to launch the applications.
"""

import os
import re
import sys
import subprocess
import platform
import tank
import sgtk

# Qt GUI 사용
try:
    from sgtk.platform.qt import QtGui, QtCore
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

#rez append 
#sys.path.append("/westworld/inhouse/rez/lib/python2.7/site-packages/rez-2.23.1-py2.7.egg")

ENGINES = {
    'tk-houdini':'houdini',
    'tk-maya': 'maya' ,
    'tk-nuke': 'nuke',
    'tk-nukestudio': 'nuke',
    'tk-katana': 'katana',
    'tk-mari' : 'mari',
    'tk-3de4' : '3de',
    'tk-clarisse' : 'clarisse',
    'tk-unreal' : 'unreal'
}


# 사용 가능한 플러그인 리스트
AVAILABLE_PLUGINS = ['Silk', 'boris']

def show_software_selector():
    """
    플러그인 선택 GUI를 표시하고 선택된 플러그인을 반환
    
    :returns: 선택된 플러그인 이름 리스트, 또는 None
    """
    if not GUI_AVAILABLE:
        return None
    
    # 사용 가능한 플러그인 목록
    software_dict = {plugin: plugin for plugin in AVAILABLE_PLUGINS}
    
    if not software_dict:
        return None
    
    # QApplication이 없으면 생성
    app = QtGui.QApplication.instance()
    if app is None:
        app = QtGui.QApplication(sys.argv)
    
    # 다이얼로그 클래스 정의
    class SoftwareSelectorDialog(QtGui.QDialog):
        def __init__(self, software_dict, parent=None):
            super(SoftwareSelectorDialog, self).__init__(parent)
            self.software_dict = software_dict
            self.selected_items = []
            self.init_ui()
        
        def init_ui(self):
            self.setWindowTitle("추가 플러그인 선택")
            self.setMinimumSize(400, 500)
            
            # 메인 레이아웃
            main_layout = QtGui.QVBoxLayout(self)
            
            # 라벨
            label = QtGui.QLabel("추가로 로드할 플러그인을 선택하세요:")
            main_layout.addWidget(label)
            
            # 리스트 위젯 (다중 선택 가능)
            self.list_widget = QtGui.QListWidget()
            self.list_widget.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
            main_layout.addWidget(self.list_widget)
            
            # 소프트웨어 목록 추가
            for code in sorted(self.software_dict.keys()):
                self.list_widget.addItem(code)
            
            # 버튼 레이아웃
            button_layout = QtGui.QHBoxLayout()
            
            # 확인 버튼
            ok_button = QtGui.QPushButton("확인")
            ok_button.clicked.connect(self.accept_selection)
            button_layout.addWidget(ok_button)
            
            # 취소 버튼
            cancel_button = QtGui.QPushButton("취소")
            cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(cancel_button)
            
            main_layout.addLayout(button_layout)
            
            # 다이얼로그를 화면 중앙에 배치
            self.center_dialog()
        
        def center_dialog(self):
            frame_geometry = self.frameGeometry()
            screen_center = QtGui.QDesktopWidget().availableGeometry().center()
            frame_geometry.moveCenter(screen_center)
            self.move(frame_geometry.topLeft())
        
        def accept_selection(self):
            # 선택된 항목 가져오기
            selected_items = [item.text() for item in self.list_widget.selectedItems()]
            self.selected_items = selected_items
            self.accept()
    
    # 다이얼로그 실행
    dialog = SoftwareSelectorDialog(software_dict)
    result = dialog.exec_()
    
    # OK 버튼을 눌렀고 선택된 항목이 있으면
    if result == QtGui.QDialog.Accepted and dialog.selected_items:
        return dialog.selected_items
    
    return None



class AppLaunch(tank.Hook):
    """
    Hook to run an application.
    """
    
    def execute(self, app_path, app_args, version, engine_name, **kwargs):
        """
        The execute functon of the hook will be called to start the required application
        
        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.

        :returns: (dict) The two valid keys are 'command' (str) and 'return_code' (int).
        """
        if engine_name == "tk-photoshopcc":
            cmd =  "start /B \"App\" \"%s\" %s" % (app_path, app_args)
            exit_code = os.system(cmd)
            return {"command": cmd,
                    "return_code": exit_code

                    }


        app_name = ENGINES[engine_name]
        context = self.tank.context_from_path(self.tank.project_path)
        project = context.project
        sg = self.tank.shotgun
        system = sys.platform
        
        adapter = get_adapter(platform.system())
        
        packages = get_rez_packages(sg,app_name,version,system,project)

        # GUI를 통해 추가 플러그인 선택
        additional_plugins = show_software_selector()
        
        # 선택된 추가 플러그인이 있으면 packages에 추가
        if additional_plugins:
            if not packages:
                packages = []
            if isinstance(packages, str):
                packages = [packages]
            if not isinstance(packages, list):
                packages = list(packages) if packages else []
            
            # 추가 플러그인을 packages에 추가
            packages.extend(additional_plugins)
            self.logger.info('추가로 선택된 플러그인: %s' % ', '.join(additional_plugins))
        print("packages--------------------------------")
        print(packages)
        print("packages--------------------------------")
        try:
            import rez as _
        except ImportError:
            rez_path = adapter.get_rez_module_root()
            if not rez_path:
                raise EnvironmentError('rez is not installed and could not be automatically found. Cannot continue.')
            
            if sys.version_info.major == 3:
                rez_path = rez_path.decode('utf-8')

            sys.path.append(rez_path)
        
        from rez import resolved_context
        

        if not packages:
            self.logger.debug('No rez packages were found. The default boot, instead.')
            command = adapter.get_command(app_path, app_args)
            return_code = os.system(command)
            return {'command': command, 'return_code': return_code}
        context = resolved_context.ResolvedContext(packages)
        return adapter.execute(context, app_args,app_name)
        


def get_rez_packages(sg,app_name,version,system,project):
    
    if "linux" in system:
        filter_dict = [['code','is',app_name.title()+" "+version],
                       ['projects','in',project]
                      ]
        packages = sg.find("Software",filter_dict,['sg_rez'])
        if packages : 
            packages =  packages[0]['sg_rez']
        else:
            filter_dict = [['code','is',app_name.title()+" "+version],
                        ['projects','is',None] ]
            packages = sg.find("Software",filter_dict,['sg_rez'])
            if packages:
                packages =  packages[0]['sg_rez']

    else:
        filter_dict = [['code','is',app_name.title()+" "+version],
                       ['projects','in',project]
                      ]
        packages = sg.find("Software",filter_dict,['sg_win_rez'])
        if packages : 
            packages =  packages[0]['sg_win_rez']
        else:
            filter_dict = [['code','is',app_name.title()+" "+version],
                        ['projects','is',None] ]
            packages = sg.find("Software",filter_dict,['sg_win_rez'])
            if packages:
                packages =  packages[0]['sg_win_rez']

    if packages:
        packages = [ x for x in packages.split(",")] 
    else:
        packages = None
    return packages


class BaseAdapter(object):


    shell_type = 'bash'

    @staticmethod
    def get_command(path, args):

        return '"{path}" {args} &'.format(path=path, args=args)

    @staticmethod
    def get_rez_root_command():

        return 'rez-env rez -- printenv REZ_REZ_ROOT'

    @classmethod
    def get_rez_module_root(cls):

        command = cls.get_rez_root_command()
        module_path, stderr = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()

        module_path = module_path.strip()

        if not stderr and module_path:
            return module_path

        return ''

    @classmethod
    def execute(cls, context, args,command):
        
        if command == "unreal":
            command = "UE4Editor"

        os.environ['USE_SHOTGUN'] = "OK"
        if args:
            command += ' {args}'.format(args=args)
        if platform.system()  == "Linux" and command  not in  ["houdini",'UE4Editor']:
            command = "mate-terminal -x bash -c '{}'".format(command)
        
        proc = context.execute_shell(
            command = command,
            #command = "gnome-terminal -x bash -c 'python'",
            stdin = False,
            block = False
        )
        
        return_code = 0
        context.print_info(verbosity=True)

        return {
            'command': command,
            'return_code': return_code,
        }


class LinuxAdapter(BaseAdapter):


    pass


class WindowsAdapter(BaseAdapter):


    shell_type = 'cmd'

    @staticmethod
    def get_command(path, args):
        return 'start /B "App" "{path}" {args}'.format(path=path, args=args)

    @staticmethod
    def get_rez_root_command():

        return 'rez-env rez -- echo %REZ_REZ_ROOT%'






def get_adapter(system=''):
    if not system:
        system = platform.system()
    
    options = {
        'Linux' : LinuxAdapter,
        'Windows' : WindowsAdapter
        }


    try :
        return options[system]

    except KeyError:
        raise NotImplementedError('system "{system}" is currently unsupported. Options were, "{options}"'
                                  ''.format(system=system, options=list(options)))
