#!/usr/bin/env python3
# scripts/generate-dashboard.py

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent))
import challenge_schema as cs
from pathlib import Path

import yaml


def generate_development_dashboard():
    """生成開發儀表板"""

    dashboard_data = {
        "generated_at": datetime.now().isoformat(),
        "challenge_progress": get_challenge_progress(),
        "quality_metrics": get_quality_metrics(),
        "development_timeline": get_development_timeline(),
    }

    # 生成 HTML 儀表板
    generate_html_dashboard(dashboard_data)

    # 生成 JSON 數據
    with open("dashboard.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=2, ensure_ascii=False)

    return dashboard_data


def get_challenge_progress():
    """獲取題目進度統計"""
    challenges_dir = Path("challenges")
    progress = {
        "total_challenges": 0,
        "by_category": defaultdict(int),
        "by_difficulty": defaultdict(int),
        "by_status": defaultdict(int),
        "by_type": defaultdict(int),
        "completion_rate": 0,
    }

    if not challenges_dir.exists():
        return progress

    for category_dir in challenges_dir.iterdir():
        if not category_dir.is_dir():
            continue

        for challenge_dir in category_dir.iterdir():
            if not challenge_dir.is_dir():
                continue

            public_yml = challenge_dir / "public.yml"
            if public_yml.exists():
                try:
                    with open(public_yml, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)

                    progress["total_challenges"] += 1
                    progress["by_category"][category_dir.name] += 1
                    progress["by_difficulty"][data.get("difficulty", "unknown")] += 1
                    progress["by_status"][data.get("status", "unknown")] += 1
                    progress["by_type"][cs.kind(data)] += 1
                except:
                    continue

    # 計算完成率
    completed = progress["by_status"]["completed"] + progress["by_status"]["ready"]
    if progress["total_challenges"] > 0:
        progress["completion_rate"] = round(
            (completed / progress["total_challenges"]) * 100, 1
        )

    return progress


def get_quality_metrics():
    """獲取品質指標"""
    metrics = {"automated_tests": 0, "documentation_coverage": 0, "validation_score": 0}

    # 檢查文檔覆蓋率
    challenges_dir = Path("challenges")
    if challenges_dir.exists():
        total_challenges = 0
        documented_challenges = 0

        for category_dir in challenges_dir.iterdir():
            if not category_dir.is_dir():
                continue

            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue

                public_yml = challenge_dir / "public.yml"
                if public_yml.exists():
                    total_challenges += 1

                    # 檢查是否有完整文檔
                    readme = challenge_dir / "README.md"
                    writeup = challenge_dir / "writeup"

                    if readme.exists() and writeup.exists():
                        documented_challenges += 1

        if total_challenges > 0:
            metrics["documentation_coverage"] = round(
                (documented_challenges / total_challenges) * 100, 1
            )

    return metrics


def get_development_timeline():
    """獲取開發時程表"""
    timeline = {
        "milestones": [
            {"name": "題目開發階段", "progress": 65, "status": "in_progress"},
            {"name": "測試與驗證", "progress": 30, "status": "in_progress"},
            {"name": "平台部署", "progress": 0, "status": "pending"},
            {"name": "比賽執行", "progress": 0, "status": "pending"},
        ]
    }

    return timeline


def generate_html_dashboard(data):
    """生成 HTML 儀表板"""
    html_template = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CTF 開發儀表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="container mt-4">
        <div class="row mb-4">
            <div class="col-12">
                <h1><i class="fas fa-tachometer-alt me-2"></i>CTF 開發儀表板</h1>
                <p class="text-muted">最後更新: {generated_at}</p>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{total_challenges}</h4>
                                <p class="mb-0">總題目數</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-list fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{completion_rate}%</h4>
                                <p class="mb-0">完成率</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-chart-pie fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card bg-info text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{documentation_coverage}%</h4>
                                <p class="mb-0">文檔覆蓋率</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-book fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3">
                <div class="card bg-warning text-white">
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <div>
                                <h4>{category_count}</h4>
                                <p class="mb-0">分類數量</p>
                            </div>
                            <div class="align-self-center">
                                <i class="fas fa-tags fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-bar me-2"></i>按分類統計</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="categoryChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line me-2"></i>開發進度</h5>
                    </div>
                    <div class="card-body">
                        {timeline_html}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 分類圖表
        const ctx = document.getElementById('categoryChart').getContext('2d');
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: {category_labels},
                datasets: [{{
                    data: {category_data},
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
    </script>
</body>
</html>
    """

    # 準備數據
    progress = data["challenge_progress"]
    categories = dict(progress["by_category"])

    timeline_html = ""
    for milestone in data["development_timeline"]["milestones"]:
        status_class = {
            "completed": "success",
            "in_progress": "primary",
            "pending": "secondary",
        }.get(milestone["status"], "secondary")

        timeline_html += f"""
        <div class="mb-3">
            <div class="d-flex justify-content-between mb-1">
                <span>{milestone["name"]}</span>
                <span>{milestone["progress"]}%</span>
            </div>
            <div class="progress">
                <div class="progress-bar bg-{status_class}" style="width: {milestone["progress"]}%"></div>
            </div>
        </div>
        """

    html_content = html_template.format(
        generated_at=data["generated_at"][:19],
        total_challenges=progress["total_challenges"],
        completion_rate=progress["completion_rate"],
        documentation_coverage=data["quality_metrics"]["documentation_coverage"],
        category_count=len(categories),
        category_labels=json.dumps(list(categories.keys())),
        category_data=json.dumps(list(categories.values())),
        timeline_html=timeline_html,
    )

    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_content)


def main():
    print("📊 生成開發儀表板...")
    dashboard = generate_development_dashboard()
    print("✅ 儀表板生成完成！")
    print(f"📊 總題目數: {dashboard['challenge_progress']['total_challenges']}")
    print(f"📈 完成率: {dashboard['challenge_progress']['completion_rate']}%")
    print("📄 HTML 儀表板: dashboard.html")
    print("📋 JSON 數據: dashboard.json")


if __name__ == "__main__":
    main()
