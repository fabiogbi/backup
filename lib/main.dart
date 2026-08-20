import 'dart:io';
import 'package:flutter/material.dart';
import 'package:photo_manager/photo_manager.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:path/path.dart' as p;

// ===== CONFIGURAÇÃO =====
// IP fixo do Tailscale do NAS (funciona de qualquer rede, inclusive empresa)
const String NAS_BASE_URL = 'http://100.66.10.4:9120';
const String USER = 'fabio';
const String PASS = '@Azul98verde';
// ===== FIM CONFIG =====

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'NAS Backup',
        theme: ThemeData(primarySwatch: Colors.teal),
        home: const BackupHome(),
      );
}

class BackupHome extends StatefulWidget {
  const BackupHome({super.key});
  @override
  State<BackupHome> createState() => _BackupHomeState();
}

class _BackupHomeState extends State<BackupHome> {
  String _status = 'ocioso';
  int _pending = 0;
  int _done = 0;

  @override
  void initState() {
    super.initState();
    _initPhotos();
  }

  Future<void> _initPhotos() async {
    final perm = await PhotoManager.requestPermissionExtend();
    setState(() => _status = perm.isAuth ? 'pronto' : 'sem permissão de fotos');
  }

  Future<List<AssetEntity>> _newAssets() async {
    final pref = await SharedPreferences.getInstance();
    final lastId = pref.getString('lastAssetId') ?? '';
    final list = await PhotoManager.getAssetListPaged(
        page: 0, pageCount: 100, type: RequestType.image | RequestType.video);
    final assets = <AssetEntity>[];
    for (final a in list) {
      if (a.id == lastId) break;
      assets.add(a);
    }
    return assets.reversed.toList(); // mais antigo -> mais novo
  }

  Future<void> _backupNow() async {
    setState(() => _status = 'lendo fotos...');
    final assets = await _newAssets();
    setState(() {
      _pending = assets.length;
      _status = '${assets.length} novo(s)';
    });
    if (assets.isEmpty) {
      setState(() => _status = 'nada novo');
      return;
    }
    final pref = await SharedPreferences.getInstance();
    String? lastId;
    for (final a in assets) {
      setState(() => _status = 'enviando ${a.title}');
      final ok = await _upload(a);
      if (ok) {
        lastId = a.id;
        setState(() => _done++);
      }
    }
    if (lastId != null) await pref.setString('lastAssetId', lastId);
    setState(() => _status = 'concluído: $_done enviado(s)');
    _done = 0;
  }

  Future<bool> _upload(AssetEntity asset) async {
    try {
      final file = await asset.file;
      if (file == null) return false;
      final bytes = await file.readAsBytes();
      final uri = Uri.parse('$NAS_BASE_URL/upload');
      final req = http.MultipartRequest('POST', uri)
        ..fields['device'] = 'iPhoneFabio'
        ..files.add(http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: asset.title ?? p.basename(file.path),
        ));
      req.headers['Authorization'] =
          'Basic ${base64Encode(utf8.encode('$USER:$PASS'))}';
      final resp = await req.send().timeout(const Duration(minutes: 2));
      return resp.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('NAS Backup')),
        body: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Servidor: $NAS_BASE_URL', style: const TextStyle(fontSize: 12)),
              const SizedBox(height: 16),
              Text('Status: $_status', style: const TextStyle(fontSize: 16)),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _backupNow,
                child: const Text('Fazer backup agora'),
              ),
              const SizedBox(height: 12),
              const Text('Dica: use o Atalho "NAS Backup 2h" para '
                  'disparar automaticamente ao ficar 2h no mesmo local.'),
            ],
          ),
        ),
      );
}
