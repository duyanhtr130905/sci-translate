import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/translation_provider.dart';
import 'package:intl/intl.dart';

class FavoritesScreen extends StatelessWidget {
  const FavoritesScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Yêu thích')),
      body: Consumer<TranslationProvider>(
        builder: (context, provider, _) {
          if (provider.favorites.isEmpty) {
            return const Center(child: Text('Chưa có mục yêu thích'));
          }

          return ListView.separated(
            itemCount: provider.favorites.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final item = provider.favorites[index];
              final dateFormat = DateFormat('dd/MM/yyyy HH:mm');

              return Dismissible(
                key: ValueKey('fav_${item.timestamp.millisecondsSinceEpoch}_${item.sourceText.hashCode}'),
                direction: DismissDirection.endToStart,
                background: Container(
                  color: Colors.red,
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: const Icon(Icons.delete, color: Colors.white),
                ),
                confirmDismiss: (_) async {
                  return (await showDialog<bool>(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: const Text('Xóa yêu thích?'),
                      content: const Text('Bạn có chắc muốn xóa mục yêu thích này không?'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, false),
                          child: const Text('Hủy'),
                        ),
                        TextButton(
                          onPressed: () => Navigator.pop(ctx, true),
                          child: const Text('Xóa'),
                        ),
                      ],
                    ),
                  )) ??
                      false;
                },
                onDismissed: (_) async {
                  await provider.removeFavoriteItem(item);
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Đã xóa khỏi yêu thích')),
                  );
                },
                child: ListTile(
                  title: Text(item.sourceText, maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 4),
                      Text(
                        item.translatedText,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w500),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${item.sourceLanguage.toUpperCase()} → ${item.targetLanguage.toUpperCase()} • ${dateFormat.format(item.timestamp)}',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: Icon(
                          provider.isFavorite(item) ? Icons.star : Icons.star_border,
                          color: provider.isFavorite(item) ? Colors.amber : null,
                        ),
                        onPressed: () => provider.toggleFavorite(item),
                        tooltip: 'Bỏ yêu thích',
                      ),
                      IconButton(
                        icon: const Icon(Icons.copy),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: item.translatedText));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Đã sao chép bản dịch!'),
                              duration: Duration(seconds: 1),
                            ),
                          );
                        },
                        tooltip: 'Sao chép',
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}