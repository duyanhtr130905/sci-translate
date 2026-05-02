import 'dart:convert';
import '../config/env.dart';
import 'package:http/http.dart' as http;

class TranslationService {
  //final baseUrl = Env.apiBaseUrl;
  static const String baseUrl = 'https://api.mymemory.translated.net/get';
  static const String detectUrl = 'https://libretranslate.de/detect';

  final List<String> supportedLanguages = [
    'auto',
    'en', 'vi', 'fr', 'de', 'es', 'zh', 'ja', 'ko'
  ];

  final Map<String, String> languageNames = {
    'auto': 'Tự nhận diện',
    'en': 'Tiếng Anh',
    'vi': 'Tiếng Việt',
    'fr': 'Tiếng Pháp',
    'de': 'Tiếng Đức',
    'es': 'Tây Ban Nha',
    'zh': 'Trung Quốc',
    'ja': 'Nhật Bản',
    'ko': 'Hàn Quốc',
  };

  Future<String> detectLanguageOnline(String text) async {
    final t = text.trim();
    if (t.isEmpty) return 'en';

    final res = await http.post(
      Uri.parse(detectUrl),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'q': t},
    );

    if (res.statusCode != 200) {
      throw Exception('Không thể nhận diện ngôn ngữ (${res.statusCode})');
    }

    final data = jsonDecode(res.body);
    // data: [{language: "en", confidence: 0.99}, ...]
    if (data is List && data.isNotEmpty) {
      final lang = (data[0]['language'] ?? '').toString();
      if (supportedLanguages.contains(lang)) return lang;
    }

    return 'en';
  }

  Future<String> translate({
    required String text,
    required String sourceLanguage,
    required String targetLanguage,
  }) async {
    try {
      var src = sourceLanguage;
      if (src == 'auto') {
        src = await detectLanguageOnline(text);
      }

      final url = Uri.parse(
        '$baseUrl?q=${Uri.encodeComponent(text)}&langpair=$src|$targetLanguage',
      );

      final response = await http.get(url);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (data['responseData'] != null) {
          final translatedText = data['responseData']['translatedText'];
          return translatedText ?? text;
        } else {
          throw Exception('Lỗi API: ${data['responseStatus']} - ${data['responseDetails']}');
        }
      } else {
        throw Exception('Lỗi máy chủ (${response.statusCode})');
      }
    } catch (e) {
      throw Exception('Không thể dịch: $e');
    }
  }

  String getLanguageName(String code) {
    return languageNames[code] ?? code;
  }
}