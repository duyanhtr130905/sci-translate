class offlinetranslationservice {
static String _normalize(String s) => s.trim().toLowerCase();

static String _k(String text, String sourceLanguage, String targetLanguage) {
return '${_normalize(text)}|${sourceLanguage.toLowerCase()}|${targetLanguage.toLowerCase()}';
}

final Map<String, String> _dictionary = {
_k('hello', 'en', 'vi'): 'xin chào',
_k('thank you', 'en', 'vi'): 'cảm ơn',
_k('goodbye', 'en', 'vi'): 'tạm biệt',
};

String? translateOffline({
required String text,
required String sourceLanguage,
required String targetLanguage,
}) {
return _dictionary[_k(text, sourceLanguage, targetLanguage)];
}
}
