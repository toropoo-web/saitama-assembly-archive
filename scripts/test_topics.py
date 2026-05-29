from topic_keywords import detect_topics

sample_text = """
外国人支援と多文化共生について質問します。
また学校教育と給食費についても議論します。
"""

topics = detect_topics(sample_text)

print(topics)