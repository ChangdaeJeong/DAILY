import os
import sys
import shutil
import importlib.util

# 이 파일은 router/project/__init__.py에서 호출되어 각 스텝별 동작을 수행합니다.
# 초기에는 비어있으며, 필요에 따라 로직이 추가될 예정입니다.

def _execute_interface_function(function_name, project_root_dir):
    """
    DailyProjectInterface.py 파일을 동적으로 임포트하고 지정된 클래스 메서드를 수행합니다.
    """
    full_project_path = os.path.join('workspace', project_root_dir)
    interface_file_name = 'DailyProjectInterface.py' # 파일 이름만 지정
    
    original_cwd = os.getcwd() # 현재 작업 디렉토리 저장
    try:
        # 프로젝트 디렉토리로 이동
        os.chdir(full_project_path)

        # 변경된 작업 디렉토리를 기준으로 파일 경로 지정
        spec = importlib.util.spec_from_file_location("DailyProjectInterface", interface_file_name)
        interface_module = importlib.util.module_from_spec(spec)
        sys.modules["DailyProjectInterface"] = interface_module
        spec.loader.exec_module(interface_module)

        if hasattr(interface_module, 'DailyProjectInterface') and callable(interface_module.DailyProjectInterface):
            interface_instance = interface_module.DailyProjectInterface() # 클래스 인스턴스화
            if hasattr(interface_instance, function_name) and callable(getattr(interface_instance, function_name)):
                result = getattr(interface_instance, function_name)() # 인자 없이 메서드 호출
                return {'success': result, 'msg': f"인터페이스 함수 '{function_name}' 실행 완료."} # DailyProjectInterface의 메서드가 True/False를 반환한다고 가정
            else:
                return {'success': False, 'msg': f"DailyProjectInterface 클래스에 '{function_name}' 메서드가 없습니다."}
        else:
            return {'success': False, 'msg': "DailyProjectInterface.py에 'DailyProjectInterface' 클래스가 없습니다."}
    except Exception as e:
        return {'success': False, 'msg': f"인터페이스 함수 '{function_name}' 실행 중 오류 발생: {e}"}
    finally:
        os.chdir(original_cwd) # 원래 작업 디렉토리로 복원

def execute_interface_init(project_root_dir):
    return _execute_interface_function('init', project_root_dir)

def execute_interface_build(project_root_dir):
    return _execute_interface_function('build', project_root_dir)

def execute_interface_run(project_root_dir):
    return _execute_interface_function('run', project_root_dir)
