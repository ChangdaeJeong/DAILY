# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.
# 인터페이스는 항상 소스코드 루트에서 실행됩니다.
import os

class Daily_Project_Interface:
    def __init__(self):
        self.version = "v1"
        pass

    def init(self):
        # You can clone from git like below
        os.system(f"git clone <repo_url>")
        # check clone success and return result
        ret = True
        return ret

    # build
    def build(self):
        print(f"Building project at ...")
        os.system(f"build commands here")
        
        # check build success and return result
        ret = True
        return ret

    # run
    def run(self):
        print("Running the project...")
        os.system("adb shell am start -n <package_name>/<activity_name>")
        # check run success and return result
        ret = True
        return ret
