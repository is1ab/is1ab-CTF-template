#!/usr/bin/env python3
"""
CTF 管理 Web 服務器
提供 RESTful API 和靜態檔案服務
"""

import os
import sys
import json
import yaml
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Flask 相關套件
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError

# 添加 scripts 目錄到路徑
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))

# 導入我們的腳本模組
try:
    from create_challenge import ChallengeCreator
    from update_readme import ReadmeUpdater
    from validate_challenge import ChallengeValidator
except ImportError as e:
    print(f"警告: 無法導入腳本模組: {e}")
    print("某些功能可能無法正常運作")

app = Flask(__name__)
CORS(app)  # 允許跨域請求

# 配置
app.config['SECRET_KEY'] = 'ctf-manager-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 全域變數
BASE_DIR = Path(__file__).parent.parent
CHALLENGES_DIR = BASE_DIR / 'challenges'
CONFIG_FILE = BASE_DIR / 'config.yml'

class CTFManager:
    """CTF 管理核心類別"""
    
    def __init__(self):
        self.config = self.load_config()
        self.challenge_creator = None
        self.readme_updater = None
        self.validator = None
        
        # 初始化模組
        try:
            self.challenge_creator = ChallengeCreator(str(CONFIG_FILE))
            self.readme_updater = ReadmeUpdater(str(CONFIG_FILE))
            self.validator = ChallengeValidator()
        except Exception as e:
            print(f"警告: 初始化模組失敗: {e}")
    
    def load_config(self) -> Dict:
        """載入配置檔案"""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self.get_default_config()
        except Exception as e:
            print(f"載入配置失敗: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """預設配置"""
        return {
            'project': {
                'name': 'IS1AB CTF',
                'flag_prefix': 'is1abCTF',
                'year': datetime.now().year
            },
            'points': {
                'baby': 50,
                'easy': 100,
                'middle': 200,
                'hard': 300,
                'impossible': 500
            }
        }
    
    def get_challenges(self) -> Dict:
        """取得所有題目"""
        challenges = {}
        
        if not CHALLENGES_DIR.exists():
            return challenges
        
        for category_dir in CHALLENGES_DIR.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            challenges[category] = []
            
            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue
                
                public_yml = challenge_dir / 'public.yml'
                if public_yml.exists():
                    try:
                        with open(public_yml, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                        
                        data['folder_name'] = challenge_dir.name
                        data['path'] = str(challenge_dir)
                        challenges[category].append(data)
                    except Exception as e:
                        print(f"讀取 {public_yml} 失敗: {e}")
        
        return challenges
    
    def calculate_stats(self, challenges: Dict) -> Dict:
        """計算統計資料"""
        total_challenges = 0
        status_counts = {'planning': 0, 'developing': 0, 'testing': 0, 'completed': 0, 'deployed': 0}
        category_counts = {}
        difficulty_counts = {'baby': 0, 'easy': 0, 'middle': 0, 'hard': 0, 'impossible': 0}
        type_counts = {
            'static_attachment': 0,
            'static_container': 0,
            'dynamic_attachment': 0,
            'dynamic_container': 0,
            'nc_challenge': 0
        }
        source_code_counts = {'provided': 0, 'not_provided': 0}
        
        for category, challenge_list in challenges.items():
            category_counts[category] = len(challenge_list)
            total_challenges += len(challenge_list)
            
            for challenge in challenge_list:
                status = challenge.get('status', 'planning')
                difficulty = challenge.get('difficulty', 'easy')
                challenge_type = challenge.get('challenge_type', 'static_attachment')
                source_code_provided = challenge.get('source_code_provided', False)
                
                if status in status_counts:
                    status_counts[status] += 1
                if difficulty in difficulty_counts:
                    difficulty_counts[difficulty] += 1
                if challenge_type in type_counts:
                    type_counts[challenge_type] += 1
                
                if source_code_provided:
                    source_code_counts['provided'] += 1
                else:
                    source_code_counts['not_provided'] += 1
        
        # 計算配額進度
        quota_progress = self.calculate_quota_progress(category_counts, difficulty_counts, type_counts, total_challenges)
        
        return {
            'total_challenges': total_challenges,
            'status_counts': status_counts,
            'category_counts': category_counts,
            'difficulty_counts': difficulty_counts,
            'type_counts': type_counts,
            'source_code_counts': source_code_counts,
            'quota_progress': quota_progress,
            'last_updated': datetime.now().isoformat()
        }
    
    def calculate_quota_progress(self, category_counts: Dict, difficulty_counts: Dict, type_counts: Dict, total_challenges: int) -> Dict:
        """計算配額完成進度"""
        quota_config = self.config.get('challenge_quota', {})
        
        # 驗證配額設定
        validation_result = self.validate_quota_config(quota_config)
        
        progress = {
            'category_progress': {},
            'difficulty_progress': {},
            'total_progress': {},
            'validation': validation_result
        }
        
        # 分類進度
        category_quota = quota_config.get('by_category', {})
        for category, target in category_quota.items():
            current = category_counts.get(category, 0)
            progress['category_progress'][category] = {
                'current': current,
                'target': target,
                'percentage': min(100, (current / target * 100)) if target > 0 else 0,
                'remaining': max(0, target - current),
                'status': 'completed' if current >= target else 'in_progress' if current > 0 else 'not_started'
            }
        
        # 難度進度
        difficulty_quota = quota_config.get('by_difficulty', {})
        for difficulty, target in difficulty_quota.items():
            current = difficulty_counts.get(difficulty, 0)
            progress['difficulty_progress'][difficulty] = {
                'current': current,
                'target': target,
                'percentage': min(100, (current / target * 100)) if target > 0 else 0,
                'remaining': max(0, target - current),
                'status': 'completed' if current >= target else 'in_progress' if current > 0 else 'not_started'
            }
        
        # 總進度
        total_target = quota_config.get('total_target', 0)
        progress['total_progress'] = {
            'current': total_challenges,
            'target': total_target,
            'percentage': min(100, (total_challenges / total_target * 100)) if total_target > 0 else 0,
            'remaining': max(0, total_target - total_challenges),
            'status': 'completed' if total_challenges >= total_target else 'in_progress' if total_challenges > 0 else 'not_started'
        }
        
        return progress
    
    def validate_quota_config(self, quota_config: Dict) -> Dict:
        """驗證配額配置是否合理"""
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'suggestions': []
        }
        
        validation_rules = quota_config.get('validation', {})
        category_quota = quota_config.get('by_category', {})
        difficulty_quota = quota_config.get('by_difficulty', {})
        total_target = quota_config.get('total_target', 0)
        
        # 檢查總目標是否設定
        if total_target <= 0:
            validation_result['errors'].append('總目標題目數必須大於 0')
            validation_result['is_valid'] = False
        
        # 檢查分類配額總和
        category_sum = sum(category_quota.values())
        if validation_rules.get('category_sum_equals_total', True):
            tolerance = validation_rules.get('tolerance_percentage', 5) / 100
            if abs(category_sum - total_target) > total_target * tolerance:
                if category_sum > total_target:
                    validation_result['warnings'].append(
                        f'分類配額總和 ({category_sum}) 超過總目標 ({total_target})，'
                        f'超出 {category_sum - total_target} 題'
                    )
                else:
                    validation_result['warnings'].append(
                        f'分類配額總和 ({category_sum}) 少於總目標 ({total_target})，'
                        f'缺少 {total_target - category_sum} 題'
                    )
        
        # 檢查難度配額總和
        difficulty_sum = sum(difficulty_quota.values())
        if validation_rules.get('difficulty_sum_equals_total', True):
            tolerance = validation_rules.get('tolerance_percentage', 5) / 100
            if abs(difficulty_sum - total_target) > total_target * tolerance:
                if difficulty_sum > total_target:
                    validation_result['warnings'].append(
                        f'難度配額總和 ({difficulty_sum}) 超過總目標 ({total_target})，'
                        f'超出 {difficulty_sum - total_target} 題'
                    )
                else:
                    validation_result['warnings'].append(
                        f'難度配額總和 ({difficulty_sum}) 少於總目標 ({total_target})，'
                        f'缺少 {total_target - difficulty_sum} 題'
                    )
        
        # 檢查最小配額限制
        min_category = validation_rules.get('min_challenges_per_category', 1)
        min_difficulty = validation_rules.get('min_challenges_per_difficulty', 1)
        
        for category, count in category_quota.items():
            if count < min_category:
                validation_result['warnings'].append(
                    f'分類 "{category}" 配額 ({count}) 低於建議最小值 ({min_category})'
                )
        
        for difficulty, count in difficulty_quota.items():
            if count < min_difficulty:
                validation_result['warnings'].append(
                    f'難度 "{difficulty}" 配額 ({count}) 低於建議最小值 ({min_difficulty})'
                )
        
        # 提供建議
        if category_sum != total_target:
            diff = total_target - category_sum
            if diff > 0:
                validation_result['suggestions'].append(
                    f'建議增加 {diff} 題分類配額以達到總目標'
                )
            else:
                validation_result['suggestions'].append(
                    f'建議減少 {-diff} 題分類配額以符合總目標'
                )
        
        if difficulty_sum != total_target:
            diff = total_target - difficulty_sum
            if diff > 0:
                validation_result['suggestions'].append(
                    f'建議增加 {diff} 題難度配額以達到總目標'
                )
            else:
                validation_result['suggestions'].append(
                    f'建議減少 {-diff} 題難度配額以符合總目標'
                )
        
        # 檢查配額分布合理性
        if category_quota:
            max_category = max(category_quota.values())
            min_category_val = min(category_quota.values())
            if max_category > min_category_val * 3:
                validation_result['suggestions'].append(
                    '分類配額分布不均，建議平衡各分類題目數量'
                )
        
        if difficulty_quota:
            # 檢查難度梯度是否合理 (一般來說，簡單題目應該比困難題目多)
            easy_count = difficulty_quota.get('easy', 0) + difficulty_quota.get('baby', 0)
            hard_count = difficulty_quota.get('hard', 0) + difficulty_quota.get('impossible', 0)
            if hard_count > easy_count:
                validation_result['suggestions'].append(
                    '建議增加簡單題目數量，保持適當的難度梯度'
                )
        
        return validation_result
    
    def get_recent_activity(self) -> List[Dict]:
        """取得最近活動 (從 Git 日誌)"""
        try:
            # 取得最近 10 筆 commit
            result = subprocess.run([
                'git', 'log', '--oneline', '--pretty=format:%h|%an|%ar|%s', '-10'
            ], capture_output=True, text=True, cwd=BASE_DIR)
            
            if result.returncode != 0:
                return []
            
            activities = []
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        activities.append({
                            'type': 'commit',
                            'hash': parts[0],
                            'author': parts[1],
                            'time': parts[2],
                            'message': parts[3]
                        })
            
            return activities
        except Exception as e:
            print(f"取得活動失敗: {e}")
            return []
    
    def get_team_assignments(self, challenges: Dict) -> Dict:
        """取得團隊任務分配"""
        assignments = {}
        
        for category, challenge_list in challenges.items():
            for challenge in challenge_list:
                author = challenge.get('author', 'Unknown')
                if author not in assignments:
                    assignments[author] = []
                
                assignments[author].append({
                    'category': category,
                    'title': challenge.get('title', 'Untitled'),
                    'status': challenge.get('status', 'planning'),
                    'difficulty': challenge.get('difficulty', 'easy'),
                    'challenge_type': challenge.get('challenge_type', 'static_attachment'),
                    'source_code_provided': challenge.get('source_code_provided', False)
                })
        
        return assignments
    
    def create_challenge(self, data: Dict) -> Dict:
        """創建新題目"""
        if not self.challenge_creator:
            raise Exception("Challenge creator 未初始化")
        
        try:
            # 驗證必要欄位
            required_fields = ['name', 'category', 'difficulty', 'challenge_type', 'description', 'author']
            for field in required_fields:
                if field not in data or not data[field]:
                    raise ValueError(f"缺少必要欄位: {field}")
            
            # 呼叫創建腳本
            self.challenge_creator.create_challenge(
                category=data['category'],
                name=data['name'],
                difficulty=data['difficulty'],
                author=data['author'],
                challenge_type=data.get('challenge_type')
            )
            
            challenge_path = CHALLENGES_DIR / data['category'] / data['name']
            
            # 更新 public.yml 中的額外資訊
            if challenge_path.exists():
                public_yml = challenge_path / 'public.yml'
                if public_yml.exists():
                    with open(public_yml, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    
                    # 更新額外資訊
                    config['description'] = data['description']
                    config['source_code_provided'] = data.get('source_code_provided', False)
                    
                    if data.get('tags'):
                        config['tags'] = data['tags'] if isinstance(data['tags'], list) else data['tags'].split(',')
                    
                    if data.get('learning_objectives'):
                        config['learning_objectives'] = data['learning_objectives']
                    
                    # NC 題目特殊設定
                    if data.get('challenge_type') == 'nc_challenge':
                        config['deploy_info'].update({
                            'nc_port': int(data.get('nc_port', 9999)),
                            'timeout': int(data.get('nc_timeout', 60))
                        })
                    
                    with open(public_yml, 'w', encoding='utf-8') as f:
                        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            return {
                'success': True,
                'message': f"題目 {data['name']} 創建成功",
                'path': str(challenge_path),
                'branch': f"challenge/{data['category']}/{data['name']}"
            }
        
        except Exception as e:
            raise Exception(f"創建題目失敗: {str(e)}")
    
    def update_readme(self) -> Dict:
        """更新 README"""
        if not self.readme_updater:
            raise Exception("README updater 未初始化")
        
        try:
            self.readme_updater.collect_challenges()
            self.readme_updater.calculate_stats()
            self.readme_updater.update_readme()
            
            return {
                'success': True,
                'message': 'README 更新成功',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"更新 README 失敗: {str(e)}")
    
    def validate_challenges(self) -> Dict:
        """驗證所有題目"""
        if not self.validator:
            raise Exception("Validator 未初始化")
        
        try:
            success = self.validator.validate_all_challenges()
            
            return {
                'success': success,
                'message': '驗證完成',
                'errors': len(self.validator.errors),
                'warnings': len(self.validator.warnings),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"驗證失敗: {str(e)}")

# 初始化管理器
ctf_manager = CTFManager()

# ========== API 路由 ==========

@app.route('/')
def index():
    """主頁面"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """靜態檔案服務"""
    return send_from_directory('.', filename)

@app.route('/api/health')
def health_check():
    """健康檢查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/config')
def get_config():
    """取得系統配置"""
    return jsonify(ctf_manager.config)

@app.route('/api/stats')
def get_stats():
    """取得統計資料"""
    try:
        challenges = ctf_manager.get_challenges()
        stats = ctf_manager.calculate_stats(challenges)
        
        return jsonify({
            'challenges': challenges,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress')
def get_progress():
    """取得進度資料"""
    try:
        challenges = ctf_manager.get_challenges()
        stats = ctf_manager.calculate_stats(challenges)
        
        # 從配置獲取分類順序和配額
        quota_config = ctf_manager.config.get('challenge_quota', {})
        category_quota = quota_config.get('by_category', {})
        
        # 按照配置文件中的順序排列分類
        categories = list(category_quota.keys()) if category_quota else ['general', 'web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc']
        
        # 生成進度表格
        table_rows = []
        max_challenges_per_category = max([len(challenges.get(cat, [])) for cat in categories] + [6])  # 至少顯示6欄
        
        for category in categories:
            challenge_list = challenges.get(category, [])
            target_count = category_quota.get(category, len(challenge_list))
            category_display = f"{category.title()} ({len(challenge_list)}/{target_count})"
            
            row = [category_display]
            
            for i in range(max_challenges_per_category):
                if i < len(challenge_list):
                    challenge = challenge_list[i]
                    title = challenge.get('title', challenge.get('name', '未命名'))
                    author = challenge.get('author', '未知')
                    difficulty = challenge.get('difficulty', 'easy')
                    status = challenge.get('status', 'planning')
                    
                    # 難度顏色映射
                    difficulty_colors = {
                        'baby': 'success',
                        'easy': 'info', 
                        'middle': 'warning',
                        'hard': 'danger',
                        'impossible': 'dark'
                    }
                    
                    # 狀態圖示
                    status_icons = {
                        'planning': '📝',
                        'developing': '🔨',
                        'testing': '🧪',
                        'completed': '✅',
                        'deployed': '🚀'
                    }
                    
                    icon = status_icons.get(status, '❓')
                    color = difficulty_colors.get(difficulty, 'secondary')
                    
                    # 格式化為包含完整資訊的物件
                    cell_data = {
                        'type': 'challenge',
                        'title': title,
                        'author': author,
                        'difficulty': difficulty,
                        'status': status,
                        'icon': icon,
                        'color': color,
                        'display': f"{icon} {title}\\n👤 {author}\\n🎯 {difficulty.title()}"
                    }
                    row.append(cell_data)
                elif i < target_count:
                    # 在目標範圍內但尚未創建的題目
                    row.append({
                        'type': 'empty',
                        'display': '⚪ 待創建',
                        'color': 'light'
                    })
                else:
                    # 超出目標的欄位
                    row.append({
                        'type': 'unused',
                        'display': '⬜ 不需要',
                        'color': 'secondary'
                    })
            
            table_rows.append(row)
        
        # 生成動態表格標題
        headers = ['分類 (現有/目標)']
        for i in range(max_challenges_per_category):
            headers.append(chr(65 + i))  # A, B, C, D...
        
        return jsonify({
            'challenges': challenges,
            'stats': stats,
            'quota_config': category_quota,
            'table_headers': headers,
            'table_rows': table_rows,
            'categories_order': categories
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activity')
def get_activity():
    """取得最近活動"""
    try:
        activities = ctf_manager.get_recent_activity()
        return jsonify(activities)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/assignments')
def get_assignments():
    """取得團隊任務分配"""
    try:
        challenges = ctf_manager.get_challenges()
        assignments = ctf_manager.get_team_assignments(challenges)
        return jsonify(assignments)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/challenges', methods=['GET'])
def get_challenges():
    """取得所有題目"""
    try:
        challenges = ctf_manager.get_challenges()
        return jsonify(challenges)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/challenges', methods=['POST'])
def create_challenge():
    """創建新題目"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("無效的 JSON 資料")
        
        result = ctf_manager.create_challenge(data)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/challenges/<challenge_id>')
def get_challenge(challenge_id):
    """取得特定題目"""
    try:
        # 解析 challenge_id (格式: category/name)
        if '/' not in challenge_id:
            raise BadRequest("無效的題目 ID 格式")
        
        category, name = challenge_id.split('/', 1)
        challenge_path = CHALLENGES_DIR / category / name / 'public.yml'
        
        if not challenge_path.exists():
            raise NotFound("題目不存在")
        
        with open(challenge_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return jsonify(data)
    except (BadRequest, NotFound):
        raise
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-readme', methods=['POST'])
def update_readme():
    """更新 README"""
    try:
        result = ctf_manager.update_readme()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def validate_challenges():
    """驗證題目"""
    try:
        result = ctf_manager.validate_challenges()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export')
def export_data():
    """匯出資料"""
    try:
        challenges = ctf_manager.get_challenges()
        stats = ctf_manager.calculate_stats(challenges)
        
        data = {
            'challenges': challenges,
            'stats': stats,
            'config': ctf_manager.config,
            'exported_at': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search_challenges():
    """搜尋題目"""
    try:
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify([])
        
        challenges = ctf_manager.get_challenges()
        results = []
        
        for category, challenge_list in challenges.items():
            for challenge in challenge_list:
                # 搜尋標題、描述、標籤
                title = challenge.get('title', '').lower()
                description = challenge.get('description', '').lower()
                tags = challenge.get('tags', [])
                tag_str = ' '.join(tags).lower() if isinstance(tags, list) else str(tags).lower()
                
                if (query in title or 
                    query in description or 
                    query in tag_str or 
                    query in category.lower()):
                    
                    results.append({
                        'category': category,
                        'title': challenge.get('title', ''),
                        'description': challenge.get('description', ''),
                        'difficulty': challenge.get('difficulty', ''),
                        'status': challenge.get('status', ''),
                        'path': challenge.get('path', '')
                    })
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """取得系統日誌"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        # 這裡可以實作真正的日誌系統
        # 目前返回一些模擬日誌
        logs = [
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'CTF Manager started successfully',
                'component': 'server'
            }
        ]
        
        return jsonify(logs[:limit])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== 錯誤處理 ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(BadRequest)
def bad_request(error):
    return jsonify({'error': error.description}), 400

# ========== 啟動服務器 ==========

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CTF Manager Web Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"""
    ========================================
    🚀 CTF Manager Web Server
    ========================================
    
    Server starting on: http://{args.host}:{args.port}
    Debug mode: {'ON' if args.debug else 'OFF'}
    Working directory: {BASE_DIR}
    
    API Endpoints:
    - GET  /api/health         健康檢查
    - GET  /api/stats          統計資料  
    - GET  /api/progress       進度資料
    - GET  /api/activity       最近活動
    - GET  /api/challenges     所有題目
    - POST /api/challenges     創建題目
    - POST /api/update-readme  更新 README
    - POST /api/validate       驗證題目
    - GET  /api/export         匯出資料
    
    Web Interface:
    - /                        主控台
    - /create-challenge.html   創建題目
    - /progress.html          進度查看
    
    ========================================
    """)
    
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()