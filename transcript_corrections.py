"""High-confidence, auditable corrections for recurring ASR mistakes."""

from __future__ import annotations

import re

NAME_VARIANTS = r"(?:道子|到此|刀子|到齊)"


def apply_corrections(text: str) -> tuple[str, list[str]]:
    corrected = text
    reasons: list[str] = []

    def replace(pattern: str, replacement: str, reason: str) -> None:
        nonlocal corrected
        corrected, count = re.subn(pattern, replacement, corrected)
        if count:
            reasons.append(f"{reason} × {count}")

    # Only correct name variants when the surrounding wording is an introduction
    # or a direct honorific.  This deliberately leaves ordinary phrases such as
    # 「人都到齊了」 untouched.
    replace(rf"((?:大家好|哈囉|嗨|OK|各位).{{0,20}}?)(?:我是|我)\s*{NAME_VARIANTS}(?=[，,。！!\s]|$)", r"\1我是道慈", "name in greeting")
    replace(rf"(?:(?<=我是)|(?<=我叫))\s*{NAME_VARIANTS}(?=[，,。！!\s]|$)", "道慈", "name in self-introduction")
    replace(rf"{NAME_VARIANTS}老師", "道慈老師", "channel host honorific")

    focal_context = r"(?:\d{2,3}\s*(?:mm|毫米)|鏡頭|視角|廣角|望遠|景深)"
    if "焦燈" in corrected and re.search(focal_context, corrected, re.IGNORECASE):
        corrected = corrected.replace("焦燈", "焦段")
        reasons.append("photography term: 焦燈 → 焦段")
    if "交代" in corrected and re.search(rf"{focal_context}.{{0,18}}交代|交代.{{0,18}}(?:廣|窄|望遠)", corrected, re.IGNORECASE):
        corrected = corrected.replace("交代", "焦段")
        reasons.append("photography term: 交代 → 焦段")
    if "四角" in corrected and re.search(r"(?:焦段|28|35|視野|畫面)", corrected):
        corrected = corrected.replace("四角", "視角")
        reasons.append("photography term: 四角 → 視角")
    if "接拍" in corrected and re.search(r"(?:在|去|做|喜歡|練習)接拍|接拍(?:的時候|時)", corrected):
        corrected = corrected.replace("接拍", "街拍")
        reasons.append("photography term: 接拍 → 街拍")

    return corrected, reasons
