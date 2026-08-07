import unittest

from transcript_corrections import apply_corrections


class TranscriptCorrectionTests(unittest.TestCase):
    def test_corrects_host_in_introduction(self):
        corrected, reasons = apply_corrections("大家好我是到此，今天聊鏡頭")
        self.assertEqual(corrected, "大家好我是道慈，今天聊鏡頭")
        self.assertTrue(reasons)

    def test_normalizes_short_greeting_to_full_introduction(self):
        corrected, _ = apply_corrections("嗨大家好我到此")
        self.assertEqual(corrected, "嗨大家好我是道慈")

    def test_does_not_change_normal_arrival_phrase(self):
        corrected, reasons = apply_corrections("大家還沒有到齊的時候先等等")
        self.assertEqual(corrected, "大家還沒有到齊的時候先等等")
        self.assertFalse(reasons)

    def test_corrects_contextual_photography_terms(self):
        corrected, _ = apply_corrections("28mm和35mm兩個焦燈的視野差異，街上接拍的時候很好比較")
        self.assertEqual(corrected, "28mm和35mm兩個焦段的視野差異，街上街拍的時候很好比較")

    def test_does_not_change_unrelated_word(self):
        corrected, reasons = apply_corrections("請先把事情交代清楚")
        self.assertEqual(corrected, "請先把事情交代清楚")
        self.assertFalse(reasons)


if __name__ == "__main__":
    unittest.main()
