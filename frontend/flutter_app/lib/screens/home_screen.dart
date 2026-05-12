import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/translation_provider.dart';
import '../services/translation_service.dart';
//import 'history_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Translator App'),
        elevation: 2,
      ),
      body: SafeArea(
        child: Column(
          children: [
            const LanguageSelector(),
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  children: const [
                    InputTextArea(),
                    SizedBox(height: 16),
                    OutputTextArea(),
                  ],
                ),
              ),
            ),
            const TranslateButton(),
          ],
        ),
      ),
    );
  }
}

class LanguageSelector extends StatelessWidget {
  const LanguageSelector({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final service = TranslationService();
    final supportedLangs = service.supportedLanguages;

    return Consumer<TranslationProvider>(
      builder: (context, provider, _) {
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
          color: Colors.grey.withOpacity(0.1),
          child: Row(
            children: [
              // --- Nút chọn ngôn ngữ nguồn ---
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Từ:', style: TextStyle(fontSize: 12, color: Colors.black45)),
                    DropdownButtonFormField<String>(
                      value: provider.sourceLanguage,
                      isExpanded: true, // ✅ Quan trọng: Cho phép text tự co giãn
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 0),
                      ),
                      items: supportedLangs.map((langCode) {
                        return DropdownMenuItem(
                          value: langCode,
                          child: Text(
                            service.getLanguageName(langCode),
                            overflow: TextOverflow.ellipsis, // ✅ Cắt bớt text nếu quá dài
                            style: const TextStyle(fontSize: 14),
                          ),
                        );
                      }).toList(),
                      onChanged: (val) => provider.setSourceLanguage(val!),
                    ),
                  ],
                ),
              ),

              // --- Nút hoán đổi ---
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4.0),
                child: IconButton(
                  icon: const Icon(Icons.swap_horiz, color: Colors.blue),
                  onPressed: provider.swapLanguages,
                  tooltip: "Đổi ngôn ngữ",
                ),
              ),

              // --- Nút chọn ngôn ngữ đích ---
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Sang:', style: TextStyle(fontSize: 12, color: Colors.black45)),
                    DropdownButtonFormField<String>(
                      value: provider.targetLanguage,
                      isExpanded: true, // ✅ Quan trọng
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 0),
                      ),
                      items: supportedLangs.map((langCode) {
                        return DropdownMenuItem(
                          value: langCode,
                          child: Text(
                            service.getLanguageName(langCode),
                            overflow: TextOverflow.ellipsis, // ✅ Cắt bớt text
                            style: const TextStyle(fontSize: 14),
                          ),
                        );
                      }).toList(),
                      onChanged: (val) => provider.setTargetLanguage(val!),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class InputTextArea extends StatelessWidget {
  const InputTextArea({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Consumer<TranslationProvider>(
      builder: (context, provider, _) {
        return Container(
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade400),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            children: [
              TextField(
                controller: TextEditingController(text: provider.inputText)
                  ..selection = TextSelection.collapsed(offset: provider.inputText.length),
                maxLines: 5,
                decoration: const InputDecoration(
                  hintText: 'Nhập văn bản cần dịch...',
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.all(12),
                ),
                onChanged: provider.setInputText,
              ),
              if (provider.inputText.isNotEmpty)
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                IconButton(
                icon: Icon(provider.isSpeaking ? Icons.stop : Icons.volume_up),
                onPressed: provider.isSpeaking
                ? provider.stopSpeaking
                    : provider.speakInput,
                ),
                IconButton(
                icon: const Icon(Icons.clear),
                onPressed: provider.clearInput,
                ),
        ]
              ),
            ],
          ),
        );
      },
    );
  }
}

class OutputTextArea extends StatelessWidget {
  const OutputTextArea({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Consumer<TranslationProvider>(
      builder: (context, provider, _) {
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 16),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.blue.withOpacity(0.05),
            border: Border.all(color: Colors.blue.withOpacity(0.3)),
            borderRadius: BorderRadius.circular(8),
          ),
          constraints: const BoxConstraints(minHeight: 120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Kết quả dịch:', style: TextStyle(color: Colors.blue.shade800, fontWeight: FontWeight.bold)),
                  if (provider.outputText.isNotEmpty)
                    Row(
                      children: [
                        IconButton(
                          icon: Icon(provider.isSpeaking ? Icons.stop : Icons.volume_up, size: 20),
                          onPressed: provider.isSpeaking
                              ? provider.stopSpeaking
                              : provider.speakOutput,
                        ),
                        IconButton(
                          icon: const Icon(Icons.copy, size: 20),
                          onPressed: () {
                            Clipboard.setData(ClipboardData(text: provider.outputText));
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Đã sao chép!'), duration: Duration(seconds: 1)),
                            );
                          },
                        ),
                      ],
                    ),
                ],
              ),
              const SizedBox(height: 8),
              if (provider.isLoading)
                const Center(child: CircularProgressIndicator())
              else if (provider.error != null)
                Text(provider.error!, style: const TextStyle(color: Colors.red))
              else
                Text(
                  provider.outputText.isEmpty ? '...' : provider.outputText,
                  style: const TextStyle(fontSize: 16),
                ),
            ],
          ),
        );
      },
    );
  }
}

class TranslateButton extends StatelessWidget {
  const TranslateButton({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Consumer<TranslationProvider>(
      builder: (context, provider, _) {
        return Container(
          padding: const EdgeInsets.all(16),
          width: double.infinity,
          child: ElevatedButton(
            onPressed: provider.isLoading ? null : provider.translate,
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              backgroundColor: Colors.lightBlue,
              foregroundColor: Colors.white,
            ),
            child: const Text('DỊCH', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ),
        );
      },
    );
  }
}