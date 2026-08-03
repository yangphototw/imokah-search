import codecs
content = codecs.open("fix_all_titles_completely.py", "r", "utf-8").read()
new_items = '''    "Is a 100MP Compact Worth Buying? | A Camera Born of Pure Self-Indulgence": "一億像素隨身機值得買嗎？｜一台為任性而生的相機",
    "The Question Editing Beginners Ask Most | How Bright Should Exposure Be? | ft. BenQ": "修圖新手最常問的問題｜曝光到底要多亮？｜ft. BenQ",
'''
content = content.replace('"Flew Halfway Across the World for a Single BirdUBucket-List Dream: The Faroe Islands": "為了看一隻鳥飛了大半個地球 - 人生夢幻清單：法羅群島"', '"Flew Halfway Across the World for a Single BirdUBucket-List Dream: The Faroe Islands": "為了看一隻鳥飛了大半個地球 - 人生夢幻清單：法羅群島",\n' + new_items)
codecs.open("fix_all_titles_completely.py", "w", "utf-8").write(content)
