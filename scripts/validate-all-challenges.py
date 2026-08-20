#!/usr/bin/env python3
# scripts/validate-all-challenges.py

import sys
import yaml
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import challenge_schema as cs

class AllChallengesValidator:
    def __init__(self, config_path='config.yml'):
        self.load_config(config_path)
        self.challenges_dir = Path('challenges')
        self.stats = defaultdict(int)
        self.errors = []
        self.warnings = []
        
    def load_config(self, config_path):
        """載入專案配置"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️  配置文件 {config_path} 不存在，使用預設配置")
            self.config = {}

    def find_all_challenges(self):
        """找出所有題目"""
        challenges = []
        if not self.challenges_dir.exists():
            print(f"❌ 找不到題目目錄：{self.challenges_dir}")
            return challenges

        for category_dir in self.challenges_dir.iterdir():
            if not category_dir.is_dir():
                continue

            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue
                public_yml = challenge_dir / 'public.yml'
                if public_yml.exists():
                    challenges.append({
                        'path': challenge_dir,
                        'category': category_dir.name,
                        'name': challenge_dir.name,
                        'public_yml': public_yml
                    })
                    
        return challenges
    
    def validate_single_challenge(self, challenge):
        """驗證單個題目"""
        try:
            result = subprocess.run([
                sys.executable, 'scripts/validate-challenge.py', 
                str(challenge['path'])
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
    
    def analyze_challenge_config(self, challenge):
        """分析題目配置"""
        try:
            with open(challenge['public_yml'], 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            return {
                'difficulty': config.get('difficulty', 'unknown'),
                'points': config.get('points', 0),
                'status': config.get('status', 'unknown'),
                'author': config.get('author', 'unknown'),
                'challenge_type': cs.kind(config)
            }
        except Exception as e:
            return {
                'difficulty': 'error',
                'points': 0,
                'status': 'error',
                'author': 'error',
                'challenge_type': 'error',
                'error': str(e)
            }
    
    def validate_all(self):
        """驗證所有題目"""
        print("🔍 開始驗證所有題目...")
        print()
        
        challenges = self.find_all_challenges()
        if not challenges:
            print("⚠️  未找到任何題目")
            return False
            
        print(f"📊 找到 {len(challenges)} 個題目")
        print()
        
        results = []
        for i, challenge in enumerate(challenges, 1):
            print(f"[{i}/{len(challenges)}] 驗證 {challenge['category']}/{challenge['name']}...")
            
            validation_result = self.validate_single_challenge(challenge)
            config_analysis = self.analyze_challenge_config(challenge)
            
            result = {
                "challenge": challenge,
                "validation": validation_result,
                "config": config_analysis,
            }
            results.append(result)

            self.stats["total"] += 1
            self.stats[f"category_{challenge['category']}"] += 1
            self.stats[f"difficulty_{config_analysis['difficulty']}"] += 1
            self.stats[f"status_{config_analysis['status']}"] += 1

            if validation_result["success"]:
                self.stats["valid"] += 1
                print("   ✅ 驗證通過")
            else:
                self.stats["invalid"] += 1
                print("   ❌ 驗證失敗")

        print()
        return self.generate_report(results)

    def generate_report(self, results):
        """生成驗證報告"""
        print("📋 驗證報告")
        print("=" * 50)

        print(f"📊 總計：{self.stats['total']} 個題目")
        print(f"✅ 通過：{self.stats['valid']} 個")
        print(f"❌ 失敗：{self.stats['invalid']} 個")
        print()

        return self.stats["invalid"] == 0


def main():
    parser = argparse.ArgumentParser(description="Validate all CTF challenges")
    parser.add_argument("--config", default="config.yml", help="Config file path")
    args = parser.parse_args()

    validator = AllChallengesValidator(args.config)
    success = validator.validate_all()

    if success:
        print("\n🎉 所有題目驗證通過！")
        sys.exit(0)
    else:
        print(f"\n⚠️  {validator.stats['invalid']} 個題目驗證失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()