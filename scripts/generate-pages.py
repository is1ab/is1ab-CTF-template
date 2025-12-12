#!/usr/bin/env python3
"""
CTF GitHub Pages Generator - 題目展示網站生成器

功能：
1. 生成靜態 HTML 題目展示網站
2. 自動產生題目索引
3. 支援分類和搜尋
4. 響應式設計

用法：
    python generate-pages.py --input ./public-release --output ./_site
    python generate-pages.py --input ./challenges --output ./docs --theme dark
"""

import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict
import html
import re


@dataclass
class Challenge:
    """題目資料結構"""
    name: str
    title: str
    category: str
    difficulty: str
    points: int
    description: str
    author: str
    tags: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    hints: List[Dict] = field(default_factory=list)
    path: str = ""
    has_writeup: bool = False
    created_at: str = ""
    
    @property
    def difficulty_color(self) -> str:
        """根據難度返回顏色"""
        colors = {
            'baby': '#4caf50',      # 綠色
            'easy': '#8bc34a',      # 淺綠
            'middle': '#ffc107',    # 黃色
            'hard': '#ff9800',      # 橙色
            'impossible': '#f44336'  # 紅色
        }
        return colors.get(self.difficulty.lower(), '#9e9e9e')
    
    @property
    def difficulty_badge(self) -> str:
        """難度徽章 HTML"""
        emoji = {
            'baby': '🍼',
            'easy': '⭐',
            'middle': '⭐⭐',
            'hard': '⭐⭐⭐',
            'impossible': '💀'
        }.get(self.difficulty.lower(), '❓')
        return f'<span class="difficulty-badge" style="background-color: {self.difficulty_color}">{emoji} {self.difficulty.title()}</span>'


class PagesGenerator:
    """GitHub Pages 生成器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化生成器"""
        self.config = self._load_config(config_path)
        self.challenges: List[Challenge] = []
        self.categories: Dict[str, List[Challenge]] = defaultdict(list)
        
        # 預設設定
        self.site_title = self.config.get('project', {}).get('name', 'CTF Challenges')
        self.organization = self.config.get('project', {}).get('organization', 'CTF Team')
        self.flag_prefix = self.config.get('project', {}).get('flag_prefix', 'CTF')
        self.year = self.config.get('project', {}).get('year', datetime.now().year)
    
    def _load_config(self, config_path: Optional[str]) -> dict:
        """載入配置檔案"""
        paths_to_try = [
            config_path,
            'config.yml',
            '../config.yml',
            '../../config.yml'
        ]
        
        for path in paths_to_try:
            if path and os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    continue
        
        return {}
    
    def scan_challenges(self, input_dir: str) -> List[Challenge]:
        """掃描題目目錄"""
        input_path = Path(input_dir)
        challenges_dir = input_path / 'challenges'
        
        if not challenges_dir.exists():
            challenges_dir = input_path
        
        self.challenges = []
        self.categories = defaultdict(list)
        
        for category_dir in challenges_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            
            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue
                
                public_yml = challenge_dir / 'public.yml'
                if not public_yml.exists():
                    continue
                
                try:
                    with open(public_yml, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    
                    challenge = Challenge(
                        name=challenge_dir.name,
                        title=data.get('title', challenge_dir.name),
                        category=data.get('category', category),
                        difficulty=data.get('difficulty', 'unknown'),
                        points=data.get('points', 0),
                        description=data.get('description', ''),
                        author=data.get('author', 'Unknown'),
                        tags=data.get('tags', []),
                        files=data.get('files', []),
                        hints=data.get('hints', []),
                        path=f"challenges/{category}/{challenge_dir.name}",
                        has_writeup=(challenge_dir / 'writeup').exists(),
                        created_at=data.get('created_at', '')
                    )
                    
                    self.challenges.append(challenge)
                    self.categories[category].append(challenge)
                    
                except Exception as e:
                    print(f"⚠️ 無法載入 {public_yml}: {e}")
        
        # 排序
        self.challenges.sort(key=lambda c: (c.category, c.points, c.name))
        for category in self.categories:
            self.categories[category].sort(key=lambda c: (c.points, c.name))
        
        return self.challenges
    
    def generate(self, input_dir: str, output_dir: str, theme: str = 'light'):
        """生成網站"""
        print(f"🌐 生成 GitHub Pages...")
        print(f"   輸入: {input_dir}")
        print(f"   輸出: {output_dir}")
        print(f"   主題: {theme}")
        
        # 掃描題目
        self.scan_challenges(input_dir)
        print(f"   發現 {len(self.challenges)} 個題目")
        
        # 建立輸出目錄
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成 CSS
        self._generate_css(output_path, theme)
        
        # 生成首頁
        self._generate_index(output_path)
        
        # 生成分類頁面
        self._generate_category_pages(output_path)
        
        # 生成題目詳情頁面
        self._generate_challenge_pages(output_path, input_dir)
        
        # 生成搜尋頁面
        self._generate_search_page(output_path)
        
        # 生成 JSON 資料
        self._generate_json_data(output_path)
        
        # 複製附件
        self._copy_attachments(input_dir, output_path)
        
        print(f"✅ 網站生成完成！")
    
    def _generate_css(self, output_path: Path, theme: str):
        """生成 CSS 樣式"""
        is_dark = theme.lower() == 'dark'
        
        css = f"""
/* CTF Challenge Archive - Styles */
:root {{
    --bg-color: {'#1a1a2e' if is_dark else '#f5f7fa'};
    --card-bg: {'#16213e' if is_dark else '#ffffff'};
    --text-color: {'#eee' if is_dark else '#333'};
    --text-muted: {'#aaa' if is_dark else '#666'};
    --border-color: {'#0f3460' if is_dark else '#e1e4e8'};
    --accent-color: #e94560;
    --accent-hover: #ff6b6b;
    --shadow: {'0 4px 20px rgba(0,0,0,0.3)' if is_dark else '0 4px 20px rgba(0,0,0,0.1)'};
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Segoe UI', 'Noto Sans TC', system-ui, -apple-system, sans-serif;
    background: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
    min-height: 100vh;
}}

/* Header */
.header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: white;
    padding: 3rem 2rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}}

.header::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23e94560' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}}

.header h1 {{
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    position: relative;
}}

.header p {{
    font-size: 1.2rem;
    opacity: 0.9;
    position: relative;
}}

/* Navigation */
.nav {{
    background: var(--card-bg);
    padding: 1rem 2rem;
    border-bottom: 1px solid var(--border-color);
    position: sticky;
    top: 0;
    z-index: 100;
}}

.nav-container {{
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}}

.nav-links {{
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
}}

.nav-links a {{
    color: var(--text-color);
    text-decoration: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    transition: all 0.3s;
}}

.nav-links a:hover, .nav-links a.active {{
    background: var(--accent-color);
    color: white;
}}

/* Search Box */
.search-box {{
    display: flex;
    gap: 0.5rem;
}}

.search-box input {{
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background: var(--bg-color);
    color: var(--text-color);
    width: 200px;
}}

/* Container */
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}}

/* Stats */
.stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}}

.stat-card {{
    background: var(--card-bg);
    padding: 1.5rem;
    border-radius: 8px;
    text-align: center;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
}}

.stat-card .number {{
    font-size: 2rem;
    font-weight: bold;
    color: var(--accent-color);
}}

.stat-card .label {{
    color: var(--text-muted);
    font-size: 0.9rem;
}}

/* Challenge Grid */
.challenge-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
}}

/* Challenge Card */
.challenge-card {{
    background: var(--card-bg);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
    transition: transform 0.3s, box-shadow 0.3s;
}}

.challenge-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 8px 30px rgba(233, 69, 96, 0.2);
}}

.challenge-card .card-header {{
    padding: 1rem;
    background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
    color: white;
}}

.challenge-card .card-header h3 {{
    margin-bottom: 0.5rem;
}}

.challenge-card .card-header .category {{
    opacity: 0.9;
    font-size: 0.9rem;
}}

.challenge-card .card-body {{
    padding: 1rem;
}}

.challenge-card .meta {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: var(--text-muted);
}}

.challenge-card .description {{
    color: var(--text-muted);
    font-size: 0.95rem;
    margin-bottom: 1rem;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}}

.challenge-card .tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}}

.tag {{
    background: var(--bg-color);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    color: var(--text-muted);
}}

/* Difficulty Badge */
.difficulty-badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    color: white;
    font-weight: 500;
}}

/* Points */
.points {{
    color: var(--accent-color);
    font-weight: bold;
}}

/* Button */
.btn {{
    display: inline-block;
    padding: 0.75rem 1.5rem;
    background: var(--accent-color);
    color: white;
    text-decoration: none;
    border-radius: 6px;
    transition: all 0.3s;
    border: none;
    cursor: pointer;
    font-size: 1rem;
}}

.btn:hover {{
    background: var(--accent-hover);
    transform: translateY(-2px);
}}

/* Challenge Detail */
.challenge-detail {{
    background: var(--card-bg);
    border-radius: 12px;
    padding: 2rem;
    box-shadow: var(--shadow);
}}

.challenge-detail h1 {{
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}}

.challenge-detail .meta-info {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
    padding: 1rem;
    background: var(--bg-color);
    border-radius: 8px;
}}

.challenge-detail .description {{
    margin-bottom: 2rem;
    white-space: pre-wrap;
}}

.challenge-detail .hints {{
    margin-bottom: 2rem;
}}

.hint {{
    background: var(--bg-color);
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 0.5rem;
    border-left: 3px solid var(--accent-color);
}}

.hint .hint-header {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
}}

.hint .cost {{
    color: var(--accent-color);
}}

/* Files */
.files {{
    margin-bottom: 2rem;
}}

.file-item {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--bg-color);
    border-radius: 6px;
    margin-bottom: 0.5rem;
}}

.file-item a {{
    color: var(--accent-color);
    text-decoration: none;
}}

.file-item a:hover {{
    text-decoration: underline;
}}

/* Category Section */
.category-section {{
    margin-bottom: 3rem;
}}

.category-section h2 {{
    margin-bottom: 1.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--accent-color);
}}

/* Footer */
.footer {{
    background: var(--card-bg);
    padding: 2rem;
    text-align: center;
    margin-top: 3rem;
    border-top: 1px solid var(--border-color);
    color: var(--text-muted);
}}

/* Responsive */
@media (max-width: 768px) {{
    .header h1 {{
        font-size: 1.8rem;
    }}
    
    .nav-container {{
        flex-direction: column;
    }}
    
    .search-box input {{
        width: 100%;
    }}
    
    .challenge-grid {{
        grid-template-columns: 1fr;
    }}
}}
"""
        
        css_path = output_path / 'style.css'
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css)
    
    def _generate_html_header(self, title: str, extra_head: str = "") -> str:
        """生成 HTML 頭部"""
        return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} | {html.escape(self.site_title)}</title>
    <link rel="stylesheet" href="style.css">
    {extra_head}
</head>
<body>
"""
    
    def _generate_nav(self, active: str = "") -> str:
        """生成導航列"""
        categories = sorted(self.categories.keys())
        
        nav_links = f'<a href="index.html" class="{"active" if active == "home" else ""}">🏠 首頁</a>'
        
        for category in categories:
            is_active = "active" if active == category else ""
            emoji = self._get_category_emoji(category)
            nav_links += f'<a href="{category}.html" class="{is_active}">{emoji} {category.title()}</a>'
        
        nav_links += f'<a href="search.html" class="{"active" if active == "search" else ""}">🔍 搜尋</a>'
        
        return f"""
<nav class="nav">
    <div class="nav-container">
        <div class="nav-links">
            {nav_links}
        </div>
        <div class="search-box">
            <input type="text" id="quick-search" placeholder="快速搜尋..." onkeyup="quickSearch(this.value)">
        </div>
    </div>
</nav>
"""
    
    def _get_category_emoji(self, category: str) -> str:
        """取得分類的 emoji"""
        emojis = {
            'web': '🌐',
            'pwn': '💥',
            'reverse': '🔄',
            'crypto': '🔐',
            'forensic': '🔍',
            'forensics': '🔍',
            'misc': '🎲',
            'general': '📝'
        }
        return emojis.get(category.lower(), '📁')
    
    def _generate_footer(self) -> str:
        """生成頁腳"""
        return f"""
<footer class="footer">
    <p>🚩 {html.escape(self.site_title)} - {html.escape(self.organization)} {self.year}</p>
    <p>Flag 格式: <code>{html.escape(self.flag_prefix)}{{...}}</code></p>
    <p>📅 最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</footer>

<script>
function quickSearch(query) {{
    if (query.length > 2) {{
        window.location.href = 'search.html?q=' + encodeURIComponent(query);
    }}
}}

document.getElementById('quick-search').addEventListener('keypress', function(e) {{
    if (e.key === 'Enter') {{
        quickSearch(this.value);
    }}
}});
</script>
</body>
</html>
"""
    
    def _generate_index(self, output_path: Path):
        """生成首頁"""
        # 統計資料
        total_challenges = len(self.challenges)
        total_points = sum(c.points for c in self.challenges)
        categories_count = len(self.categories)
        
        difficulty_counts = defaultdict(int)
        for c in self.challenges:
            difficulty_counts[c.difficulty] += 1
        
        # 統計卡片
        stats_html = f"""
<div class="stats">
    <div class="stat-card">
        <div class="number">{total_challenges}</div>
        <div class="label">總題目數</div>
    </div>
    <div class="stat-card">
        <div class="number">{total_points}</div>
        <div class="label">總分數</div>
    </div>
    <div class="stat-card">
        <div class="number">{categories_count}</div>
        <div class="label">分類數</div>
    </div>
</div>
"""
        
        # 最新題目
        recent_challenges = sorted(self.challenges, key=lambda c: c.created_at or '', reverse=True)[:6]
        recent_html = self._generate_challenge_cards(recent_challenges)
        
        # 按分類顯示
        categories_html = ""
        for category in sorted(self.categories.keys()):
            challenges = self.categories[category]
            emoji = self._get_category_emoji(category)
            categories_html += f"""
<div class="category-section">
    <h2>{emoji} {category.title()} ({len(challenges)} 題)</h2>
    <div class="challenge-grid">
        {self._generate_challenge_cards(challenges[:4])}
    </div>
    <p style="margin-top: 1rem;"><a href="{category}.html" class="btn">查看全部 →</a></p>
</div>
"""
        
        content = f"""
{self._generate_html_header('首頁')}
<header class="header">
    <h1>🚩 {html.escape(self.site_title)}</h1>
    <p>{html.escape(self.organization)} {self.year} - Challenge Archive</p>
</header>

{self._generate_nav('home')}

<div class="container">
    {stats_html}
    
    <h2 style="margin-bottom: 1.5rem;">📌 最新題目</h2>
    <div class="challenge-grid" style="margin-bottom: 3rem;">
        {recent_html}
    </div>
    
    {categories_html}
</div>

{self._generate_footer()}
"""
        
        index_path = output_path / 'index.html'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_challenge_cards(self, challenges: List[Challenge]) -> str:
        """生成題目卡片 HTML"""
        cards = ""
        for c in challenges:
            tags_html = ''.join(f'<span class="tag">{html.escape(tag)}</span>' for tag in c.tags[:3])
            
            cards += f"""
<div class="challenge-card">
    <div class="card-header">
        <h3>{html.escape(c.title)}</h3>
        <div class="category">{self._get_category_emoji(c.category)} {c.category.title()}</div>
    </div>
    <div class="card-body">
        <div class="meta">
            {c.difficulty_badge}
            <span class="points">{c.points} pts</span>
        </div>
        <p class="description">{html.escape(c.description[:150])}{'...' if len(c.description) > 150 else ''}</p>
        <div class="tags">{tags_html}</div>
        <p style="margin-top: 1rem;"><a href="{c.path}/index.html" class="btn">查看詳情</a></p>
    </div>
</div>
"""
        return cards
    
    def _generate_category_pages(self, output_path: Path):
        """生成分類頁面"""
        for category, challenges in self.categories.items():
            emoji = self._get_category_emoji(category)
            cards_html = self._generate_challenge_cards(challenges)
            
            content = f"""
{self._generate_html_header(f'{category.title()} 題目')}
<header class="header">
    <h1>{emoji} {category.title()}</h1>
    <p>{len(challenges)} 個題目 | 總分: {sum(c.points for c in challenges)} pts</p>
</header>

{self._generate_nav(category)}

<div class="container">
    <div class="challenge-grid">
        {cards_html}
    </div>
</div>

{self._generate_footer()}
"""
            
            page_path = output_path / f'{category}.html'
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _generate_challenge_pages(self, output_path: Path, input_dir: str):
        """生成題目詳情頁面"""
        for challenge in self.challenges:
            challenge_dir = output_path / challenge.path
            challenge_dir.mkdir(parents=True, exist_ok=True)
            
            # 讀取 README
            readme_content = ""
            readme_path = Path(input_dir) / challenge.path / 'README.md'
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        readme_content = f.read()
                except Exception:
                    pass
            
            # 生成提示 HTML
            hints_html = ""
            if challenge.hints:
                hints_html = '<div class="hints"><h3>💡 提示</h3>'
                for hint in challenge.hints:
                    hints_html += f"""
<div class="hint">
    <div class="hint-header">
        <span>Level {hint.get('level', '?')}</span>
        <span class="cost">💰 -{hint.get('cost', 0)} pts</span>
    </div>
    <p>{html.escape(str(hint.get('content', '')))}</p>
</div>
"""
                hints_html += '</div>'
            
            # 生成檔案列表
            files_html = ""
            if challenge.files:
                files_html = '<div class="files"><h3>📎 附件</h3>'
                for file in challenge.files:
                    files_html += f"""
<div class="file-item">
    <span>📄</span>
    <a href="files/{html.escape(file)}" download>{html.escape(file)}</a>
</div>
"""
                files_html += '</div>'
            
            content = f"""
{self._generate_html_header(challenge.title, '<link rel="stylesheet" href="../../style.css">')}
<header class="header">
    <h1>{html.escape(challenge.title)}</h1>
    <p>{self._get_category_emoji(challenge.category)} {challenge.category.title()} | {challenge.difficulty_badge}</p>
</header>

<div class="container">
    <a href="../../{challenge.category}.html" style="color: var(--accent-color); text-decoration: none; display: inline-block; margin-bottom: 1rem;">← 返回 {challenge.category.title()}</a>
    
    <div class="challenge-detail">
        <div class="meta-info">
            <div><strong>分數</strong><br><span class="points">{challenge.points} pts</span></div>
            <div><strong>難度</strong><br>{challenge.difficulty_badge}</div>
            <div><strong>作者</strong><br>{html.escape(challenge.author)}</div>
            <div><strong>分類</strong><br>{html.escape(challenge.category)}</div>
        </div>
        
        <h3>📝 題目描述</h3>
        <div class="description">{html.escape(challenge.description)}</div>
        
        {files_html}
        
        {hints_html}
        
        <div class="tags" style="margin-top: 2rem;">
            {''.join(f'<span class="tag">{html.escape(tag)}</span>' for tag in challenge.tags)}
        </div>
    </div>
</div>

{self._generate_footer()}
"""
            
            page_path = challenge_dir / 'index.html'
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _generate_search_page(self, output_path: Path):
        """生成搜尋頁面"""
        content = f"""
{self._generate_html_header('搜尋')}
<header class="header">
    <h1>🔍 搜尋題目</h1>
    <p>搜尋所有 {len(self.challenges)} 個題目</p>
</header>

{self._generate_nav('search')}

<div class="container">
    <div style="margin-bottom: 2rem;">
        <input type="text" id="search-input" placeholder="輸入關鍵字搜尋..." 
               style="width: 100%; padding: 1rem; font-size: 1.1rem; border: 2px solid var(--border-color); border-radius: 8px; background: var(--card-bg); color: var(--text-color);">
    </div>
    
    <div id="search-results" class="challenge-grid">
        {self._generate_challenge_cards(self.challenges)}
    </div>
</div>

<script>
const challenges = {json.dumps([{
    'name': c.name,
    'title': c.title,
    'category': c.category,
    'difficulty': c.difficulty,
    'points': c.points,
    'description': c.description,
    'author': c.author,
    'tags': c.tags,
    'path': c.path
} for c in self.challenges], ensure_ascii=False)};

const searchInput = document.getElementById('search-input');
const resultsContainer = document.getElementById('search-results');

// 從 URL 參數讀取搜尋詞
const urlParams = new URLSearchParams(window.location.search);
const initialQuery = urlParams.get('q');
if (initialQuery) {{
    searchInput.value = initialQuery;
    performSearch(initialQuery);
}}

searchInput.addEventListener('input', function() {{
    performSearch(this.value);
}});

function performSearch(query) {{
    query = query.toLowerCase().trim();
    
    if (query.length < 2) {{
        // 顯示所有題目
        resultsContainer.innerHTML = generateCards(challenges);
        return;
    }}
    
    const results = challenges.filter(c => {{
        return c.title.toLowerCase().includes(query) ||
               c.description.toLowerCase().includes(query) ||
               c.category.toLowerCase().includes(query) ||
               c.author.toLowerCase().includes(query) ||
               c.tags.some(t => t.toLowerCase().includes(query));
    }});
    
    if (results.length > 0) {{
        resultsContainer.innerHTML = generateCards(results);
    }} else {{
        resultsContainer.innerHTML = '<p style="text-align: center; color: var(--text-muted);">未找到符合的題目</p>';
    }}
}}

function generateCards(items) {{
    return items.map(c => `
        <div class="challenge-card">
            <div class="card-header">
                <h3>${{escapeHtml(c.title)}}</h3>
                <div class="category">${{c.category.charAt(0).toUpperCase() + c.category.slice(1)}}</div>
            </div>
            <div class="card-body">
                <div class="meta">
                    <span class="difficulty-badge">${{c.difficulty}}</span>
                    <span class="points">${{c.points}} pts</span>
                </div>
                <p class="description">${{escapeHtml(c.description.substring(0, 150))}}...</p>
                <p style="margin-top: 1rem;"><a href="${{c.path}}/index.html" class="btn">查看詳情</a></p>
            </div>
        </div>
    `).join('');
}}

function escapeHtml(text) {{
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}}
</script>

{self._generate_footer()}
"""
        
        search_path = output_path / 'search.html'
        with open(search_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_json_data(self, output_path: Path):
        """生成 JSON 資料檔案"""
        data = {
            'generated_at': datetime.now().isoformat(),
            'site': {
                'title': self.site_title,
                'organization': self.organization,
                'year': self.year,
                'flag_prefix': self.flag_prefix
            },
            'statistics': {
                'total_challenges': len(self.challenges),
                'total_points': sum(c.points for c in self.challenges),
                'categories': len(self.categories)
            },
            'challenges': [
                {
                    'name': c.name,
                    'title': c.title,
                    'category': c.category,
                    'difficulty': c.difficulty,
                    'points': c.points,
                    'author': c.author,
                    'tags': c.tags,
                    'path': c.path
                }
                for c in self.challenges
            ]
        }
        
        json_path = output_path / 'challenges.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _copy_attachments(self, input_dir: str, output_path: Path):
        """複製附件檔案"""
        import shutil
        
        for challenge in self.challenges:
            src_files_dir = Path(input_dir) / challenge.path / 'files'
            dst_files_dir = output_path / challenge.path / 'files'
            
            if src_files_dir.exists():
                dst_files_dir.mkdir(parents=True, exist_ok=True)
                
                for file in src_files_dir.iterdir():
                    if file.is_file():
                        shutil.copy2(file, dst_files_dir / file.name)


def main():
    parser = argparse.ArgumentParser(
        description='CTF GitHub Pages Generator - 題目展示網站生成器',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--input', '-i', default='./public-release',
                       help='輸入目錄 (預設: ./public-release)')
    parser.add_argument('--output', '-o', default='./_site',
                       help='輸出目錄 (預設: ./_site)')
    parser.add_argument('--config', '-c', default='config.yml',
                       help='配置檔案路徑 (預設: config.yml)')
    parser.add_argument('--theme', '-t', choices=['light', 'dark'],
                       default='dark', help='主題 (預設: dark)')
    
    args = parser.parse_args()
    
    generator = PagesGenerator(args.config)
    generator.generate(args.input, args.output, args.theme)


if __name__ == "__main__":
    main()

