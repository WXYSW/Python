# 1. 用字典存水果数量
stock = {"苹果": 10, "香蕉": 5, "橘子": 8}

# 2. 定义一个函数：卖水果，减少库存
def sell_fruit(fruit_name, amount):
    if fruit_name in stock:          # 判断水果是否存在
        if stock[fruit_name] >= amount:  # 库存够不够
            stock[fruit_name] -= amount
            print(f"卖出 {amount} 个{fruit_name}，剩余 {stock[fruit_name]} 个")
        else:
            print(f"库存不足！只剩 {stock[fruit_name]} 个{fruit_name}")
    else:
        print("没有这种水果")

# 3. 循环展示库存
print("当前库存：")
for fruit, count in stock.items():   # items() 返回键值对
    print(f"{fruit}: {count} 个")

# 4. 模拟卖出
sell_fruit("苹果", 3)
sell_fruit("西瓜", 1)   # 没有西瓜，会提示
sell_fruit("香蕉", 10)  # 库存不足