#!/usr/bin/env python3
"""
題目提示管理腳本
用於管理 CTF 題目的多階段提示系統
"""

import argparse
import yaml
import sys
from pathlib import Path

class HintManager:
    def __init__(self):
        self.challenges_dir = Path("challenges")
    
    def find_challenge(self, category, name):
        """尋找題目路徑"""
        challenge_path = self.challenges_dir / category / name
        if not challenge_path.exists():
            print(f"❌ 題目不存在: {challenge_path}")
            return None
        
        public_yml = challenge_path / "public.yml"
        if not public_yml.exists():
            print(f"❌ 找不到 public.yml: {public_yml}")
            return None
        
        return challenge_path
    
    def load_config(self, challenge_path):
        """載入題目配置"""
        config_file = challenge_path / "public.yml"
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 載入配置失敗: {e}")
            return None
    
    def save_config(self, challenge_path, config):
        """儲存題目配置"""
        config_file = challenge_path / "public.yml"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return True
        except Exception as e:
            print(f"❌ 儲存配置失敗: {e}")
            return False
    
    def list_hints(self, category, name):
        """列出所有提示"""
        challenge_path = self.find_challenge(category, name)
        if not challenge_path:
            return
        
        config = self.load_config(challenge_path)
        if not config:
            return
        
        hints = config.get('hints', [])
        if not hints:
            print(f"📝 {config['title']} 目前沒有設定提示")
            return
        
        print(f"💡 {config['title']} - 題目提示列表")
        print("=" * 50)
        
        for hint in hints:
            level = hint.get('level', '?')
            cost = hint.get('cost', 0)
            content = hint.get('content', '無內容')
            
            print(f"🔸 提示 {level}")
            print(f"   消耗分數: {cost}")
            print(f"   內容: {content}")
            print()
    
    def add_hint(self, category, name, level, cost, content):
        """新增提示"""
        challenge_path = self.find_challenge(category, name)
        if not challenge_path:
            return
        
        config = self.load_config(challenge_path)
        if not config:
            return
        
        # 確保 hints 陣列存在
        if 'hints' not in config:
            config['hints'] = []
        
        # 檢查是否已存在相同 level 的提示
        for hint in config['hints']:
            if hint.get('level') == level:
                print(f"❌ 提示等級 {level} 已存在，請使用 update 命令更新")
                return
        
        # 新增提示
        new_hint = {
            'level': level,
            'cost': cost,
            'content': content
        }
        
        config['hints'].append(new_hint)
        
        # 按 level 排序
        config['hints'].sort(key=lambda x: x.get('level', 0))
        
        if self.save_config(challenge_path, config):
            print(f"✅ 成功新增提示 {level}")
            self.list_hints(category, name)
    
    def update_hint(self, category, name, level, cost=None, content=None):
        """更新提示"""
        challenge_path = self.find_challenge(category, name)
        if not challenge_path:
            return
        
        config = self.load_config(challenge_path)
        if not config:
            return
        
        hints = config.get('hints', [])
        hint_found = False
        
        for hint in hints:
            if hint.get('level') == level:
                hint_found = True
                if cost is not None:
                    hint['cost'] = cost
                if content is not None:
                    hint['content'] = content
                break
        
        if not hint_found:
            print(f"❌ 找不到提示等級 {level}")
            return
        
        if self.save_config(challenge_path, config):
            print(f"✅ 成功更新提示 {level}")
            self.list_hints(category, name)
    
    def remove_hint(self, category, name, level):
        """移除提示"""
        challenge_path = self.find_challenge(category, name)
        if not challenge_path:
            return
        
        config = self.load_config(challenge_path)
        if not config:
            return
        
        hints = config.get('hints', [])
        original_count = len(hints)
        
        config['hints'] = [h for h in hints if h.get('level') != level]
        
        if len(config['hints']) == original_count:
            print(f"❌ 找不到提示等級 {level}")
            return
        
        if self.save_config(challenge_path, config):
            print(f"✅ 成功移除提示 {level}")
            self.list_hints(category, name)
    
    def init_default_hints(self, category, name, difficulty):
        """初始化預設提示"""
        challenge_path = self.find_challenge(category, name)
        if not challenge_path:
            return
        
        config = self.load_config(challenge_path)
        if not config:
            return
        
        # 根據難度設定預設提示
        if difficulty == 'baby':
            default_hints = [
                {'level': 1, 'cost': 0, 'content': '這是一個適合新手的題目，從檢查原始碼開始吧！'},
                {'level': 2, 'cost': 5, 'content': '試著查看網頁的原始碼或檢查開發者工具'},
                {'level': 3, 'cost': 10, 'content': 'Flag 可能隱藏在 HTML 註解或 JavaScript 中'}
            ]
        elif difficulty == 'easy':
            default_hints = [
                {'level': 1, 'cost': 0, 'content': '仔細觀察題目的功能和輸入點'},
                {'level': 2, 'cost': 10, 'content': '試著測試不同的輸入，看看有什麼異常回應'},
                {'level': 3, 'cost': 20, 'content': '考慮常見的 Web 安全漏洞，如 SQL 注入或 XSS'}
            ]
        elif difficulty == 'middle':
            default_hints = [
                {'level': 1, 'cost': 0, 'content': '這題需要對安全概念有基本理解'},
                {'level': 2, 'cost': 15, 'content': '分析應用程式的邏輯，找出可能的攻擊點'},
                {'level': 3, 'cost': 30, 'content': '可能需要組合多種技術或繞過某些防護機制'}
            ]
        elif difficulty == 'hard':
            default_hints = [
                {'level': 1, 'cost': 0, 'content': '這是一個挑戰性題目，需要深入的技術知識'},
                {'level': 2, 'cost': 25, 'content': '考慮進階的攻擊技術或複雜的利用鏈'},
                {'level': 3, 'cost': 50, 'content': '可能需要編寫自定義工具或腳本來解決'}
            ]
        else:  # impossible
            default_hints = [
                {'level': 1, 'cost': 0, 'content': '極限挑戰題目，需要專家級的知識和技能'},
                {'level': 2, 'cost': 50, 'content': '這可能涉及最新的研究成果或未公開的技術'},
                {'level': 3, 'cost': 100, 'content': '建議查閱最新的學術論文和安全研究'}
            ]
        
        config['hints'] = default_hints
        
        if self.save_config(challenge_path, config):
            print(f"✅ 成功初始化 {difficulty} 難度的預設提示")
            self.list_hints(category, name)
    
    def validate_hints(self, category, name):
        """驗證提示設定"""
        challenge_path = self.find_challenge(category, name)
        if not challenge_path:
            return
        
        config = self.load_config(challenge_path)
        if not config:
            return
        
        hints = config.get('hints', [])
        issues = []
        
        if not hints:
            issues.append("⚠️  沒有設定任何提示")
            return
        
        # 檢查必要欄位
        for i, hint in enumerate(hints):
            if 'level' not in hint:
                issues.append(f"❌ 提示 {i+1} 缺少 level 欄位")
            if 'cost' not in hint:
                issues.append(f"❌ 提示 {i+1} 缺少 cost 欄位")
            if 'content' not in hint:
                issues.append(f"❌ 提示 {i+1} 缺少 content 欄位")
            elif not hint['content'] or hint['content'].startswith('TODO'):
                issues.append(f"⚠️  提示 {i+1} 內容需要完善")
        
        # 檢查 level 唯一性
        levels = [h.get('level') for h in hints]
        if len(levels) != len(set(levels)):
            issues.append("❌ 存在重複的提示等級")
        
        # 檢查成本遞增
        costs = [h.get('cost', 0) for h in sorted(hints, key=lambda x: x.get('level', 0))]
        for i in range(1, len(costs)):
            if costs[i] < costs[i-1]:
                issues.append("⚠️  提示成本應該遞增")
                break
        
        # 檢查第一個提示是否免費
        first_hint = min(hints, key=lambda x: x.get('level', 0), default={})
        if first_hint.get('cost', 0) != 0:
            issues.append("⚠️  建議第一個提示設為免費 (cost: 0)")
        
        # 輸出結果
        print(f"🔍 {config['title']} - 提示驗證結果")
        print("=" * 50)
        
        if not issues:
            print("✅ 所有提示設定正確！")
        else:
            for issue in issues:
                print(issue)

def main():
    parser = argparse.ArgumentParser(description='管理 CTF 題目提示')
    parser.add_argument('action', choices=['list', 'add', 'update', 'remove', 'init', 'validate'],
                       help='要執行的操作')
    parser.add_argument('category', help='題目分類')
    parser.add_argument('name', help='題目名稱')
    
    # 提示相關參數
    parser.add_argument('--level', type=int, help='提示等級')
    parser.add_argument('--cost', type=int, help='提示成本 (消耗分數)')
    parser.add_argument('--content', help='提示內容')
    parser.add_argument('--difficulty', help='題目難度 (用於初始化預設提示)')
    
    args = parser.parse_args()
    
    manager = HintManager()
    
    if args.action == 'list':
        manager.list_hints(args.category, args.name)
    
    elif args.action == 'add':
        if not all([args.level, args.cost is not None, args.content]):
            print("❌ 新增提示需要 --level, --cost, --content 參數")
            sys.exit(1)
        manager.add_hint(args.category, args.name, args.level, args.cost, args.content)
    
    elif args.action == 'update':
        if not args.level:
            print("❌ 更新提示需要 --level 參數")
            sys.exit(1)
        manager.update_hint(args.category, args.name, args.level, args.cost, args.content)
    
    elif args.action == 'remove':
        if not args.level:
            print("❌ 移除提示需要 --level 參數")
            sys.exit(1)
        manager.remove_hint(args.category, args.name, args.level)
    
    elif args.action == 'init':
        if not args.difficulty:
            print("❌ 初始化預設提示需要 --difficulty 參數")
            sys.exit(1)
        manager.init_default_hints(args.category, args.name, args.difficulty)
    
    elif args.action == 'validate':
        manager.validate_hints(args.category, args.name)

if __name__ == "__main__":
    main()