DROP TABLE IF EXISTS daily_db_project_task_file_analysis;
DROP TABLE IF EXISTS daily_db_project_files;
DROP TABLE IF EXISTS daily_db_projects;
DROP TABLE IF EXISTS daily_db_users;
DROP TABLE IF EXISTS daily_db_setting_config;
DROP TABLE IF EXISTS daily_db_messages;

CREATE TABLE IF NOT EXISTS daily_db_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uid VARCHAR(255) NOT NULL UNIQUE,
    pwd VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
INSERT INTO daily_db_users (uid, pwd) VALUES ('test', '$2b$12$zujjjJ3C36ZrWtVu/lpibueErLgjAAvwIkH70819YoAnItG3gaRY6') ON DUPLICATE KEY UPDATE update_date = CURRENT_TIMESTAMP;
INSERT INTO daily_db_users (uid, pwd) VALUES ('test2', 'test') ON DUPLICATE KEY UPDATE update_date = CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS daily_db_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    root_dir VARCHAR(200) NOT NULL, -- root directory of the project
    if_script VARCHAR(10000) NOT NULL, -- initial script to setup the project environment
    state VARCHAR(20) DEFAULT 'new', -- new, init, doing, done, delete
    batch INT DEFAULT 0, -- current batch number
    insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES daily_db_users(id)
);

CREATE TABLE IF NOT EXISTS daily_db_project_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prj_id INT NOT NULL,
    batch INT DEFAULT 1, -- batch number of the analysis
    filepath VARCHAR(2000) NOT NULL, -- file path relative to root_dir
    result VARCHAR(30) DEFAULT 'Queued', -- Completed, Skipped, Failed, Queued
    flaws VARCHAR(10000) DEFAULT '', -- ai will be added vulnerability findings when result is Completed
    insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (prj_id) REFERENCES daily_db_projects(id)
);

CREATE TABLE IF NOT EXISTS daily_db_project_task_file_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id INT NOT NULL,
    flaw_detail TEXT, -- found flaw detail from daily_db_project_files
    patch_msgs TEXT, -- ai generated patch messages from flaws findings from daily_db_project_files
    execute_type VARCHAR(30), -- patch, build, run
    execute_succeed BOOLEAN, -- whether the execute_type succeed or not
    execute_msgs TEXT, -- real result messages after applying patch, build, run..
    insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES daily_db_project_files(id)
);

-- 기존 더미 데이터 삭제 (순서 중요: 외래 키 제약 조건 때문에 자식 테이블부터 삭제)
DELETE FROM daily_db_project_task_file_analysis WHERE file_id IN (SELECT id FROM daily_db_project_files WHERE prj_id IN (SELECT id FROM daily_db_projects WHERE user_id = (SELECT id FROM daily_db_users WHERE uid = 'test2')));
DELETE FROM daily_db_project_files WHERE prj_id IN (SELECT id FROM daily_db_projects WHERE user_id = (SELECT id FROM daily_db_users WHERE uid = 'test2'));
DELETE FROM daily_db_projects WHERE user_id = (SELECT id FROM daily_db_users WHERE uid = 'test2');

-- daily_db_projects 더미 데이터 (10개)
INSERT INTO daily_db_projects (name, user_id, root_dir, if_script, state, batch) VALUES
('New Project 1', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/new1', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'new', 0),
('New Project 2', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/new2', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'new', 0),
('Init Project 1', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/init1', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'init', 1),
('Init Project 2', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/init2', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'init', 1),
('Doing Project 1', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/doing1', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'doing', 1),
('Doing Project 2', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/doing2', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'doing', 1),
('Doing Project 3', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/doing3', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'doing', 2),
('Done Project 1', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/done1', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'done', 1),
('Done Project 2', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/done2', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'done', 1),
('Done Project 3', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/done3', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'done', 1),
('Done Project 4', (SELECT id FROM daily_db_users WHERE uid = 'test2'), '/projects/done4', '# 이 파일은 프로젝트 생성 시 로딩 스크립트에서 실행될 샘플 코드입니다.\n# 인터페이스는 항상 소스코드 루트에서 실행됩니다.\nimport os\n\nclass DailyProjectInterface:\n    def __init__(self):\n        self.version = "v1"\n        pass\n\n    def init(self):\n        # You can clone from git like below\n        os.system(f"git clone <repo_url>")\n        # check clone success and return result\n        ret = True\n        return ret\n\n    # build\n    def build(self):\n        print(f"Building project at ...")\n        os.system(f"build commands here")\n        \n        # check build success and return result\n        ret = True\n        return ret\n\n    # run\n    def run(self):\n        print("Running the project...")\n        os.system("adb shell am start -n <package_name>/<activity_name>")\n        # check run success and return result\n        ret = True\n        return ret', 'done', 1);

-- daily_db_project_files 더미 데이터 (init 및 done 상태 프로젝트용)
INSERT INTO daily_db_project_files (prj_id, batch, filepath, result, flaws) VALUES
((SELECT id FROM daily_db_projects WHERE name = 'Init Project 1'), 1, '/projects/init1/file_a.py', 'Queued', ''),
((SELECT id FROM daily_db_projects WHERE name = 'Init Project 2'), 1,'/projects/init2/file_b.js', 'Queued', ''),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 1'), 1,'/projects/doing1/file_c1.java', 'Completed', '1. Array index out of bounds vulnerability found.'),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 1'), 1,'/projects/doing1/file_c2.bin', 'Skipped', 'Binary file is not supported.'),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 1'), 1,'/projects/doing1/file_c3.java', 'Queued', ''),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 2'), 1,'/projects/doing2/file_d.cpp', 'Queued', ''),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 3'), 1,'/projects/doing3/file_d11.java', 'Skipped', ''),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 3'), 2,'/projects/doing3/file_d21.java', 'Completed', ''),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 3'), 2,'/projects/doing3/file_d22.java', 'Queued', ''),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 1'), 1,'/projects/done1/file_e.html', 'Completed', 'No flaws.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 2'), 1,'/projects/done2/file_f.css', 'Completed', 'Minor issues.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 3'), 1,'/projects/done3/file_g.php', 'Completed', 'Security check passed.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 4'), 1,'/projects/done4/file_h.go', 'Completed', 'Performance optimized.');

-- daily_db_project_task_file_analysis 더미 데이터 (done 상태 프로젝트용)
INSERT INTO daily_db_project_task_file_analysis (file_id, flaw_detail, patch_msgs, execute_type, execute_succeed, execute_msgs) VALUES
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing1/file_c1.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_c1.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'patch', FALSE, 'Patch failed due to syntax error.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing1/file_c1.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_c1.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'patch', TRUE, 'Patch applied successfully.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing1/file_c1.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_c1.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'build', TRUE, 'Build successful.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing1/file_c1.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_c1.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'run', TRUE, 'Run successful.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing1/file_c1.java'), 'diff /projects/doing1/file_c1.java...', 'No patch needed.', 'patch', FALSE, 'Patch failed due to syntax error.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing3/file_d11.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_d11.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'patch', FALSE, 'Patch failed due to syntax error.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing3/file_d21.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_d21.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'patch', TRUE, 'Patch applied successfully.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing3/file_d21.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_d21.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'build', TRUE, 'Build successful.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/doing3/file_d21.java'), 'array list_abc is out of bounds.', 'diff /projects/doing1/file_d21.java...\n--- /projects/doing1/file_c1.java\n+++ /projects/doing1/file_c1.java', 'run', TRUE, 'Run successful.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/done1/file_e.html'), 'No critical flaws.', 'No patch needed.', 'patch', TRUE, 'Patch applied successfully.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/done2/file_f.css'), 'Unused CSS rules.', 'Removed dead code.', 'patch', TRUE, 'CSS optimized.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/done3/file_g.php'), 'SQL injection risk.', 'Used prepared statements.', 'build', TRUE, 'Build successful.'),
((SELECT id FROM daily_db_project_files WHERE filepath = '/projects/done4/file_h.go'), 'Concurrency bug.', 'Implemented mutex.', 'run', TRUE, 'Concurrency issue resolved.');

CREATE TABLE IF NOT EXISTS daily_db_setting_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    operation_days VARCHAR(255) NOT NULL DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat,Sun', -- 요일 선택 (예: Mon,Tue,Wed)
    operation_time_start TIME NOT NULL DEFAULT '09:00:00', -- 동작 시간 시작 (예: 09:00:00)
    operation_time_end TIME NOT NULL DEFAULT '18:00:00', -- 동작 시간 종료 (예: 18:00:00)
    ai_request_per_hour INT NOT NULL DEFAULT 20, -- 시간당 AI 요청 처리 횟수 (5~30, 5단위)
    max_retry_attempts INT NOT NULL DEFAULT 5, -- 최대 수정 시도 횟수 (1~5, 1단위)
    report_daily BOOLEAN DEFAULT FALSE,
    report_weekly BOOLEAN DEFAULT TRUE,
    report_monthly BOOLEAN DEFAULT FALSE,
    report_send_time TIME NOT NULL DEFAULT '09:00:00', -- 리포트 발송 시간 (예: 17:00:00)
    report_recipients TEXT DEFAULT '', -- 리포트 수신인 리스트 (콤마로 구분된 이메일 주소), 추가 수신인 (본인은 자동 포함)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES daily_db_users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_db_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES daily_db_projects(id) ON DELETE CASCADE
);

-- daily_db_messages 더미 데이터 (20개)
INSERT INTO daily_db_messages (project_id, title, message) VALUES
((SELECT id FROM daily_db_projects WHERE name = 'New Project 1'), '프로젝트 생성', '프로젝트 "New Project 1"이 새로 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Init Project 1'), '프로젝트 초기화 완료', '프로젝트 "Init Project 1"이 초기화 단계를 완료했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Init Project 1'), 'AI 호출 한도 도달', '프로젝트 "Doing Project 1"의 일일 AI 호출 한도에 도달했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 1'), '보고서 생성', '프로젝트 "Done Project 1"에 대한 보고서가 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'New Project 2'), '프로젝트 생성', '프로젝트 "New Project 2"이 새로 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Init Project 2'), '프로젝트 초기화 완료', '프로젝트 "Init Project 2"이 초기화 단계를 완료했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 2'), 'AI 호출 한도 도달', '프로젝트 "Doing Project 2"의 일일 AI 호출 한도에 도달했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 2'), '보고서 생성', '프로젝트 "Done Project 2"에 대한 보고서가 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 3'), '프로젝트 생성', '프로젝트 "Doing Project 3"이 새로 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 3'), '프로젝트 초기화 완료', '프로젝트 "Done Project 3"이 초기화 단계를 완료했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 4'), 'AI 호출 한도 도달', '프로젝트 "Done Project 4"의 일일 AI 호출 한도에 도달했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'New Project 1'), '보고서 생성', '프로젝트 "New Project 1"에 대한 보고서가 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Init Project 1'), '프로젝트 생성', '프로젝트 "Init Project 1"이 새로 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 1'), '프로젝트 초기화 완료', '프로젝트 "Doing Project 1"이 초기화 단계를 완료했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 1'), 'AI 호출 한도 도달', '프로젝트 "Done Project 1"의 일일 AI 호출 한도에 도달했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'New Project 2'), '보고서 생성', '프로젝트 "New Project 2"에 대한 보고서가 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Init Project 2'), '프로젝트 생성', '프로젝트 "Init Project 2"이 새로 생성되었습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 2'), '프로젝트 초기화 완료', '프로젝트 "Doing Project 2"이 초기화 단계를 완료했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Done Project 2'), 'AI 호출 한도 도달', '프로젝트 "Done Project 2"의 일일 AI 호출 한도에 도달했습니다.'),
((SELECT id FROM daily_db_projects WHERE name = 'Doing Project 3'), '보고서 생성', '프로젝트 "Doing Project 3"에 대한 보고서가 생성되었습니다.');
