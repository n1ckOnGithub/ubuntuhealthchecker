import shutil

# Calculates free amount of space on the machine
total, used, free = shutil.disk_usage("/")

total, used, free = (round(x / (1024 ** 3), 2) for x in (total, used, free))

usedp = round((used / total) * 100)

print(f"Total space: {total} GB")
print(f"Total used: {used} GB ({usedp}% used)")
print(f"Total free space: {free} GB")