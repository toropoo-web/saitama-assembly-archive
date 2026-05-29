TOPIC_KEYWORDS = {
    "foreigner": [
        "外国人",
        "移民",
        "多文化",
        "技能実習",
        "留学生"
    ],

    "education": [
        "教育",
        "学校",
        "教員",
        "教師",
        "給食",
        "児童",
        "生徒"
    ],

    "disaster": [
        "防災",
        "災害",
        "避難",
        "地震",
        "洪水"
    ],

    "welfare": [
        "福祉",
        "介護",
        "高齢者",
        "障害者"
    ],

    "childcare": [
        "子育て",
        "保育",
        "少子化",
        "こども"
    ],

    "budget": [
        "予算",
        "税金",
        "財政",
        "事業費"
    ]
}
def detect_topics(text):
    found_topics = []

    text = text.lower()

    for slug, keywords in TOPIC_KEYWORDS.items():

        for keyword in keywords:

            if keyword.lower() in text:
                found_topics.append(slug)
                break

    return found_topics