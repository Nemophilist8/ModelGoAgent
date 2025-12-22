import requests

API_URL = "http://127.0.0.1:8012/v1/chat/completions"
CASE_FILE = "original_reports/case2.txt"

def main():
    # 读取 case1_s.txt 文件内容
    with open(CASE_FILE, "r", encoding="utf-8") as f:
        case_content = f.read().strip()

    # 构造请求体（注意：只需要把 case 内容作为 messages[-1].content 即可）
    payload = {
        "messages": [
            {"role": "user", "content": case_content}
        ],
        "stream": False,
        "userId": "test_user",
        "conversationId": "test_conv_1"
    }

    print("====== 输入 case1_s.txt 内容 ======")
    print(case_content)
    print("\n====== 调用 /v1/chat/completions... ======\n")

    # 发送请求
    response = requests.post(API_URL, json=payload)

    print("====== 原始响应 ======")
    print(response.text)

    try:
        data = response.json()
        print("\n====== assistant 输出 ======")
        print(data["choices"][0]["message"]["content"])
    except Exception:
        print("\n(响应不是 JSON，已原样输出)")

if __name__ == "__main__":
    main()
