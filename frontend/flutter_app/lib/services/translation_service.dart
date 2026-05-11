import 'dart:convert';
import '../config/env.dart';
import 'package:http/http.dart' as http;

class TranslationService {
  //final baseUrl = Env.apiBaseUrl;
  static const String baseUrl =
      'https://skewed-despite-foil.ngrok-free.dev/translate/';
  static const String detectUrl = 'https://libretranslate.de/detect';

  final List<String> supportedLanguages = [
    'auto',
    'en', 'vi',
  ];

  final Map<String, String> languageNames = {
    'auto': 'Tự nhận diện',
    'en': 'Tiếng Anh',
    'vi': 'Tiếng Việt',
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

      final response = await http.post(
        Uri.parse(baseUrl),
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'text': text,
          'source_lang': src,
          'target_lang': targetLanguage,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        return data['translated_text'] ?? text;
      } else {
        throw Exception(
          'Server error: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Không thể dịch: $e');
    }
  }

  String getLanguageName(String code) {
    return languageNames[code] ?? code;
  }
}