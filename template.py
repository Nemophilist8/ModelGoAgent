from e2b import Template

template = (
    Template()
    .from_template("code-interpreter-v1")
    .set_workdir("/home/user")
    .run_cmd("pip install tabulate")
    .run_cmd("mkdir -p /home/user/workspace /home/user/data /home/user/output /home/user/scripts")
    # 使用 template.copy() 逐个复制文件
    .copy("scripts/licenses_description.yml", "/home/user/scripts/licenses_description.yml")
    .copy("scripts/license_parser.py", "/home/user/scripts/license_parser.py")
    .copy("scripts/main_case.py", "/home/user/scripts/main_case.py")
    .copy("scripts/reuse_methods.py", "/home/user/scripts/reuse_methods.py")
    .copy("scripts/test.py", "/home/user/scripts/test.py")
    .copy("scripts/works.py", "/home/user/scripts/works.py")
)
