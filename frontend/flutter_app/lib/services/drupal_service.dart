import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/env.dart';
import 'auth_service.dart';

class DrupalService {
  final AuthService _auth = AuthService();

  Future<List<Map<String, dynamic>>> searchTerms(String q) async {
    final token = await _auth.getToken();
    final res = await http.get(
      Uri.parse('${AppConfig.baseUrl}/jsonapi/term/terms?filter[name][value]=$q'),
      headers: {
        if (token != null) 'Authorization': 'Bearer $token',
        'Accept': 'application/vnd.api+json',
      },
    );

    if (res.statusCode != 200) {
      throw Exception('Lỗi Drupal');
    }

    final data = jsonDecode(res.body);
    return (data['data'] as List).cast<Map<String, dynamic>>();
  }

  Future<void> submitReview(Map<String, dynamic> payload) async {
    final token = await _auth.getToken();
    final res = await http.post(
      Uri.parse('${AppConfig.baseUrl}/reviews/submit'),
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      },
      body: jsonEncode(payload),
    );
    if (res.statusCode != 200 && res.statusCode != 201) {
      throw Exception('Gửi review thất bại');
    }
  }
}