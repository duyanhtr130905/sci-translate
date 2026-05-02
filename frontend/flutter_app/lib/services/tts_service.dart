import 'package:flutter_tts/flutter_tts.dart';

class TtsService {
  static final TtsService _instance = TtsService._internal();
  factory TtsService() => _instance;
  TtsService._internal();

  final FlutterTts _tts = FlutterTts();
  bool _isPlaying = false;

  bool get isPlaying => _isPlaying;

  Future<void> speak(String text, String languageCode) async {
    if (text.isEmpty) return;

    await _tts.setLanguage(languageCode);
    await _tts.setPitch(1.0);
    await _tts.setSpeechRate(0.5);

    _isPlaying = true;
    await _tts.speak(text);

    _tts.setCompletionHandler(() {
      _isPlaying = false;
    });
  }

  Future<void> stop() async {
    _isPlaying = false;
    await _tts.stop();
  }
}
