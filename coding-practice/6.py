def compare_numbers(a,b):
    if a > b:
        print(a)
        return a
    if a < b:
        print(b)
        return b
    else:
        print("两个数一样大")
        return 0

compare_numbers(1,2)
compare_numbers(6,5)
compare_numbers(2,2)