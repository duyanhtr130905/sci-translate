import 'dart:convert';
import 'package:http/http.dart' as http;
import 'auth_service.dart';

class ApiClient {
  final AuthService _auth = AuthService();

  Future<http.Response> get(String url) async {
    final token = await _auth.getToken();
    return http.get(
      Uri.parse(url),
      headers: token == null ? {} : {'Authorization': 'Bearer $token'},
    );
  }

  Future<http.Response> post(String url, Map<String, dynamic> body) async {
    final token = await _auth.getToken();
    return http.post(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      },
      body: jsonEncode(body),
    );
  }
}