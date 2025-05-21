"""
translation.py - Module for translating text between English and Arabic using Argos Translate.
"""
import argostranslate.package
import argostranslate.translate

class Translator:
    """
    Translator class for English <-> Arabic translation using Argos Translate.
    Initializes the required translation models and provides translation methods.
    """
    def __init__(self):
        installed_languages = argostranslate.translate.get_installed_languages()
        self._english_lang = next((lang for lang in installed_languages if lang.code == "en"), None)
        self._arabic_lang = next((lang for lang in installed_languages if lang.code == "ar"), None)
        if not self._english_lang or not self._arabic_lang:
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            for pkg in available_packages:
                if (pkg.from_code == "en" and pkg.to_code == "ar") or (pkg.from_code == "ar" and pkg.to_code == "en"):
                    download_path = pkg.download()
                    argostranslate.package.install_from_path(download_path)
            installed_languages = argostranslate.translate.get_installed_languages()
            self._english_lang = next((lang for lang in installed_languages if lang.code == "en"), None)
            self._arabic_lang = next((lang for lang in installed_languages if lang.code == "ar"), None)
        if not self._english_lang or not self._arabic_lang:
            raise RuntimeError("Required translation languages (English and Arabic) are not available.")
        # Get translation objects for English->Arabic and Arabic->English
        self._en_to_ar_translation = self._english_lang.get_translation(self._arabic_lang)
        self._ar_to_en_translation = self._arabic_lang.get_translation(self._english_lang)
        if not self._en_to_ar_translation or not self._ar_to_en_translation:
            raise RuntimeError("Failed to load translation models for English<->Arabic.")

    def translate_en_to_ar(self, text: str) -> str:
        """
        Translate English text to Arabic.
        :param text: The source text in English.
        :return: Translated text in Arabic.
        """
        return self._en_to_ar_translation.translate(text) if text.strip() != "" else ""

    def translate_ar_to_en(self, text: str) -> str:
        """
        Translate Arabic text to English.
        :param text: The source text in Arabic.
        :return: Translated text in English.
        """
        return self._ar_to_en_translation.translate(text) if text.strip() != "" else ""
