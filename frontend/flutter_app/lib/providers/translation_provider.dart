import 'package:flutter/material.dart';
import '../services/translation_service.dart';
import '../models/translation_history.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../services/tts_service.dart';

class TranslationProvider extends ChangeNotifier {
  final TranslationService _service = TranslationService();

  String _sourceLanguage = 'en';
  String _targetLanguage = 'vi';
  String _inputText = '';
  String _outputText = '';
  bool _isLoading = false;
  String? _error;
  List<TranslationHistory> _history = [];

  String get sourceLanguage => _sourceLanguage;
  String get targetLanguage => _targetLanguage;
  String get inputText => _inputText;
  String get outputText => _outputText;
  bool get isLoading => _isLoading;
  String? get error => _error;
  List<TranslationHistory> get history => _history;

  TranslationProvider() {
    _loadHistory();
    _loadFavorites();
  }

  void setSourceLanguage(String lang) {
    _sourceLanguage = lang;
    notifyListeners();
  }

  void setTargetLanguage(String lang) {
    _targetLanguage = lang;
    notifyListeners();
  }

  void setInputText(String text) {
    _inputText = text;
    _error = null;
    notifyListeners();
  }

  void swapLanguages() {
    final temp = _sourceLanguage;
    _sourceLanguage = _targetLanguage;
    _targetLanguage = temp;

    final tempText = _inputText;
    _inputText = _outputText;
    _outputText = tempText;

    notifyListeners();
  }
  Future<void> translate() async {
    if (_inputText.trim().isEmpty) {
      _error = 'Vui lòng nhập văn bản';
      notifyListeners();
      return;
    }

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final result = await _service.translate(
        text: _inputText,
        sourceLanguage: _sourceLanguage,
        targetLanguage: _targetLanguage,
      );

      _outputText = result;

      final historyItem = TranslationHistory(
        sourceText: _inputText,
        translatedText: result,
        sourceLanguage: _sourceLanguage,
        targetLanguage: _targetLanguage,
        timestamp: DateTime.now(),
      );

      _history.insert(0, historyItem);
      if (_history.length > 50) {
        _history = _history.sublist(0, 50);
      }

      await _saveHistory();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      _outputText = '';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }



  void clearInput() {
    _inputText = '';
    _outputText = '';
    _error = null;
    notifyListeners();
  }

  void clearHistory() async {
    _history.clear();
    await _saveHistory();
    notifyListeners();
  }

  Future<void> _saveHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonList = _history.map((h) => h.toJson()).toList();
    await prefs.setString('translation_history', jsonEncode(jsonList));
  }

  Future<void> _loadHistory() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString('translation_history');

      if (jsonString != null) {
        final List<dynamic> decodedList = jsonDecode(jsonString);
        _history = decodedList
            .map((json) => TranslationHistory.fromJson(json))
            .toList();
        notifyListeners();
      }
    } catch (e) {
      print('Error loading history: $e');
    }
  }
  List<TranslationHistory> _favorites = [];
  List<TranslationHistory> get favorites => _favorites;

  String _favKey(TranslationHistory item) {
    return '${item.sourceLanguage}|${item.targetLanguage}|${item.sourceText}|${item.translatedText}';
  }

  bool isFavorite(TranslationHistory item) {
    final k = _favKey(item);
    return _favorites.any((f) => _favKey(f) == k);
  }

  Future<void> toggleFavorite(TranslationHistory item) async {
    final k = _favKey(item);
    final idx = _favorites.indexWhere((f) => _favKey(f) == k);

    if (idx >= 0) {
      _favorites.removeAt(idx);
    } else {
      _favorites.insert(0, item);
    }

    await _saveFavorites();
    notifyListeners();
  }

  Future<void> _saveFavorites() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonList = _favorites.map((h) => h.toJson()).toList();
    await prefs.setString('translation_favorites', jsonEncode(jsonList));
  }

  Future<void> _loadFavorites() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString('translation_favorites');
      if (jsonString == null) return;

      final List<dynamic> decodedList = jsonDecode(jsonString);
      _favorites = decodedList.map((j) => TranslationHistory.fromJson(j)).toList();
      notifyListeners();
    } catch (_) {}
  }
  final TtsService _tts = TtsService();
  bool get isSpeaking => _tts.isPlaying;

  Future<void> speakInput() async {
    if (_inputText.isEmpty) return;
    await _tts.speak(_inputText, _sourceLanguage);
    notifyListeners();
  }

  Future<void> speakOutput() async {
    if (_outputText.isEmpty) return;
    await _tts.speak(_outputText, _targetLanguage);
    notifyListeners();
  }

  Future<void> stopSpeaking() async {
    await _tts.stop();
    notifyListeners();
  }
  // them chuc nang xoa khi quet ngang man hinh
  Future<void> removeHistoryItem(TranslationHistory item) async {
    _history.removeWhere((h) =>
    h.sourceText == item.sourceText &&
        h.translatedText == item.translatedText &&
        h.sourceLanguage == item.sourceLanguage &&
        h.targetLanguage == item.targetLanguage &&
        h.timestamp == item.timestamp);

    await _saveHistory();
    notifyListeners();
  }

  Future<void> removeFavoriteItem(TranslationHistory item) async {
    final k = _favKey(item);
    _favorites.removeWhere((f) => _favKey(f) == k);

    await _saveFavorites();
    notifyListeners();
  }
}