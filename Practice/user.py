import os

# 存储账户信息的文件名
ACCOUNTS_FILE = 'accounts.txt'

def load_accounts():
    """从文件加载账户信息，返回字典 {用户名: 密码}"""
    accounts = {}
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(',', 1)   # 只分割一次，防止密码包含逗号
                    if len(parts) == 2:
                        username, password = parts
                        accounts[username] = password
    return accounts

def save_accounts(accounts):
    """将账户字典写入文件"""
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        for username, password in accounts.items():
            f.write(f"{username},{password}\n")

def main():
    while True:
        print("\n===== 用户账户管理 =====")
        print("1. 用户注册")
        print("2. 用户登录")
        print("3. 修改密码")
        print("4. 用户注销")
        print("5. 退出程序")
        choice = input("请选择功能(1-5): ").strip()

        if choice == '1':          # 用户注册
            username = input("请输入用户名: ").strip()
            accounts = load_accounts()
            if username in accounts:
                print("用户已注册")
            else:
                password = input("请输入密码: ").strip()
                accounts[username] = password
                save_accounts(accounts)
                print("注册成功")

        elif choice == '2':        # 用户登录
            username = input("请输入用户名: ").strip()
            password = input("请输入密码: ").strip()
            accounts = load_accounts()
            if username in accounts and accounts[username] == password:
                print("登录成功")
            else:
                print("用户名或密码不正确")

        elif choice == '3':        # 修改密码
            username = input("请输入用户名: ").strip()
            old_password = input("请输入旧密码: ").strip()
            accounts = load_accounts()
            if username in accounts and accounts[username] == old_password:
                new_password = input("请输入新密码: ").strip()
                accounts[username] = new_password
                save_accounts(accounts)
                print("密码修改成功")
            else:
                print("用户名或密码不正确")

        elif choice == '4':        # 用户注销
            username = input("请输入要注销的用户名: ").strip()
            password = input("请输入密码: ").strip()
            accounts = load_accounts()
            if username not in accounts:
                print("用户不存在")
            else:
                if accounts[username] == password:
                    del accounts[username]
                    save_accounts(accounts)
                    print("注销成功")
                else:
                    print("密码不正确")

        elif choice == '5':        # 退出程序
            print("感谢使用，再见！")
            break

        else:
            print("无效的选择，请重新输入。")

if __name__ == '__main__':
    main()