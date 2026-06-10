
records = {
    "2026-05": [
        {"type": "收入", "amount": 5000, "note": "工资"},
        {"type": "支出", "amount": 300, "note": "买菜"},
    ],
}
print(records)
new_record = {"type": "支出", "amount": 200, "note": "买书"}
month = input("请输入要添加的月份")
if month in records:
    records[month].append(new_record)
else:
    records[month] = [new_record]
print(records)

def get_balance(month):
    total_income = 0
    total_expense = 0
    for record in records[month]:
        if record["type"] == "收入":
            total_income += record["amount"]
        elif record["type"] == "支出":
            total_expense += record["amount"]
        else:
            return "错误没有该月份"
    balance = total_income - total_expense
    return {
        "收入": total_income,
        "支出": total_expense,
        "结余": balance,
    }
def show_monthly_report(month):
    result = get_balance(month)        # 先拿到汇总字典
    if result is None:                 # 如果月份不存在，get_balance 返回 None
        return
    print(f"====== {month} 月收支报告 ======")
    print(f"总收入：{result['收入']} 元")
    print(f"总支出：{result['支出']} 元")
    print(f"结  余：{result['结余']} 元")
    print("================================")
