import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:jwt_decode/jwt_decode.dart';
import '../config/env.dart';

class AuthService {
  static const String tokenKey = 'auth_token';
  final _storage = const FlutterSecureStorage();
  Future<String> login(String username, String password) async {
    final res = await http.post(
      Uri.parse('${AppConfig.baseUrl}/user/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': username, 'pass': password}),
    );

    if (res.statusCode != 200) {
      throw Exception('Đăng nhập thất bại');
    }

    final data = jsonDecode(res.body);
    final token = data['access_token'] as String;
    await _storage.write(key: tokenKey, value: token);
    return token;
  }

  Future<void> logout() async {
    await _storage.delete(key: tokenKey);
  }

  Future<String?> getToken() async {
    return _storage.read(key: tokenKey);
  }

  Future<String?> getRole() async {
    final token = await getToken();
    if (token == null) return null;
    final decoded = Jwt.parseJwt(token);
    return decoded['role']?.toString();
  }

  Future<bool> isLoggedIn() async {
    final token = await getToken();
    if (token == null) return false;
    return !Jwt.isExpired(token);
  }
}