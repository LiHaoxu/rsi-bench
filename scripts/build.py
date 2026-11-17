#!/usr/bin/env python3
"""Build a dependency-free Bench website; does not run model experiments."""
from html import escape
import json
from pathlib import Path
import shutil
import sys
from urllib.parse import urlparse

from validate_result import validate

ROOT = Path(__file__).resolve().parents[1]
ASOF = "2026-11-17"


def e(value):
    return escape(str(value), quote=True)


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def link(url, label, extra=""):
    if not url:
        return ""
    if not isinstance(url, str) or not url.startswith("https://") or not urlparse(url).hostname:
        raise ValueError(f"Not a valid HTTPS source URL: {url!r}")
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer" {extra}>{e(label)} ↗</a>'


def check_catalog(data):
    seen = set()
    schemas = {
        "datasets": {"id", "name", "kind", "description", "feedback", "suitable", "limitation", "url", "license_note", "sources"},
        "tools": {"id", "name", "description", "use", "limitation", "url", "sources"},
        "protocols": {"id", "title", "question", "data", "baselines", "metrics", "controls", "risk"},
    }
    for section, fields in schemas.items():
        if not isinstance(data.get(section), list) or not data[section]:
            raise ValueError(f"Missing catalog array: {section}")
        for row in data[section]:
            missing = fields - row.keys()
            if missing:
                raise ValueError(f"{section}: missing {sorted(missing)}")
            if row["id"] in seen:
                raise ValueError(f"Duplicate id: {row['id']}")
            seen.add(row["id"])
            for url in row.get("sources", []):
                link(url, "source")


def shell(title, body, current, config):
    counts = read('data/resources.json')
    nav = [
        ("index.html#catalog", "资源目录", "01"),
        ("index.html?type=dataset#catalog", "数据集", f"{len(counts['datasets']):02d}"),
        ("index.html?type=tool#catalog", "工具与模拟器", f"{len(counts['tools']):02d}"),
        ("protocols.html", "评测协议", f"{len(counts['protocols']):02d}"),
        ("results.html", "结果与提交", "↗"),
    ]
    links = []
    for url, label, count in nav:
        active = ' aria-current="page"' if url.split('#')[0] == current else ''
        links.append(f'<a href="{url}"{active}>{label}<small>{count}</small></a>')
    nav_html = ''.join(links)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="推荐系统自进化的评测资源、可复现协议与结果提交规范。真实日志、模拟反馈和统一运行结果分别呈现。">
<meta name="theme-color" content="#206752"><title>{e(title)} · RSI Atlas Bench</title>
<link rel="stylesheet" href="assets/styles.css"><script defer src="assets/app.js"></script></head>
<body><a class="skip" href="#main">跳到正文</a><div class="layout">
<aside class="sidebar"><a class="brand" href="index.html">RSI Atlas<span class="mark">RECOMMENDER SYSTEM EVOLUTION</span></a>
<div class="switch"><a href="{e(config['survey_url'])}">SURVEY</a><a class="active" href="{e(config['bench_url'])}" aria-current="true">BENCH</a></div>
<nav aria-label="Bench 导航"><div class="nav-label">Evaluation resources</div>{nav_html}</nav>
<div class="bottom"><span>数据、协议与可复现证据</span><span>文献核验 · {ASOF}</span><a href="{e(config['repo_url'])}" target="_blank" rel="noopener noreferrer">GitHub ↗</a></div></aside>
<main class="main" id="main"><div class="topline"><a class="mobile-brand" href="index.html">RSI Atlas</a><span class="edition">RESEARCH COLLECTION / BENCH</span>
<nav aria-label="站点入口"><a href="{e(config['survey_url'])}">Survey</a><a href="index.html">Bench</a><a href="{e(config['repo_url'])}" target="_blank" rel="noopener noreferrer">GitHub ↗</a></nav></div>
{body}
<footer class="footer"><div>RSI Atlas · 推荐系统自进化<br>维护者 {e(config['owner'])} · 核验截至 {ASOF}</div><div><a href="{e(config['survey_url'])}">阅读 Survey ↗</a><br>资源索引与建议协议；不代替原论文与正式实验报告。</div></footer>
</main></div></body></html>'''


def hero(eyebrow, title, text, actions=""):
    return f'<header class="hero"><div class="eyebrow">{e(eyebrow)}</div><h1>{title}</h1><p class="lead">{e(text)}</p>{actions}</header>'


def section_head(number, title, description=""):
    return f'<div class="section-head"><div><div class="eyebrow">{e(number)}</div><h2>{e(title)}</h2></div><p>{e(description)}</p></div>'


def resource(row, is_dataset):
    kind = row.get("kind", "框架与工具")
    category = "real" if is_dataset else ("simulation" if row["id"] in {"recsim", "recsim-ng", "agent4rec", "easyrl4rec"} else "framework")
    label = "数据集" if is_dataset else "工具"
    tags = "".join(f'<span class="tag">{e(tag)}</span>' for tag in row.get("suitable", []))
    usage = f'<p><span class="field-label">反馈信息</span>{e(row["feedback"])}</p>' if is_dataset else f'<p><span class="field-label">如何使用</span>{e(row["use"])}</p>'
    license_note = f'<p><span class="field-label">获取与使用</span>{e(row["license_note"])}</p>' if is_dataset else ""
    sources = "".join(link(url, f"核验来源 {i + 1}") for i, url in enumerate(row["sources"]))
    return f'''<article class="resource" id="{e(row['id'])}" data-entry data-type="{'dataset' if is_dataset else 'tool'}" data-category="{category}">
<div class="entry-top"><span class="badge venue">{label}</span><span>{e(kind)}</span></div>
<h3>{e(row['name'])}</h3><p>{e(row['description'])}</p><div class="tags">{tags}</div>{usage}
<details><summary>适用边界与来源</summary><p class="limitation">{e(row['limitation'])}</p>{license_note}<div class="sources">{sources}</div><p class="source-note">核验日期：{e(row.get('verified', ASOF))}</p></details>
<div class="sources">{link(row['url'], '官方入口')}{link(row.get('paper'), '论文')}</div></article>'''


def index(data, results, config):
    actions = '<div class="hero-actions"><a class="btn primary" href="#catalog">浏览评测资源 ↓</a><a class="btn" href="protocols.html">选择评测协议 ↗</a><span class="status">轻量资源索引 · 持续维护</span></div>'
    body = hero("From literature to evidence", "推荐系统自进化<br><em>评测与复现</em>", "从一次离线提升，到可验证的持续改进。把数据、反馈、更新预算和评测口径放在一起，为自训练、持续学习、策略更新与智能体反思建立可复现的起点。", actions)
    stats = [(len(data['datasets']), '公开数据资源'), (len(data['tools']), '框架与模拟器'), (len(data['protocols']), '建议评测协议'), (len(results), '已收录测量记录')]
    body += '<div class="stats">' + ''.join(f'<div class="stat"><strong>{n:02d}</strong><span>{e(label)}</span></div>' for n, label in stats) + '</div>'
    body += '<section id="principles">' + section_head('01 / START WITH A QUESTION', '先定义要验证的改进', '不同类型的反馈，能支持的结论不同。')
    body += '''<div class="loop"><div><span class="n">01</span><b>固定起点</b><p>明确初始模型、数据版本、候选池与切分。</p></div><div><span class="n">02</span><b>记录更新</b><p>逐轮保存反馈来源、模型变化与计算预算。</p></div><div><span class="n">03</span><b>设置对照</b><p>控制额外训练、调用次数和教师信号。</p></div><div><span class="n">04</span><b>保留证据</b><p>公开配置、逐 seed 结果与完整实验日志。</p></div></div></section>'''
    body += '<section id="catalog">' + section_head('02 / RESOURCE CATALOG', '数据集、工具与模拟器', '资源可用于搭建实验；收录不代表已在本站完成复现。')
    body += '''<form class="filters" data-filters role="search" aria-label="筛选评测资源"><div class="controls"><label>搜索资源<input name="q" type="search" placeholder="名称、反馈类型、应用场景…" autocomplete="off"></label><label>资源类型<select name="type"><option value="">全部资源</option><option value="dataset">数据集</option><option value="tool">工具与模拟器</option></select></label><label>资源性质<select name="category"><option value="">全部性质</option><option value="real">真实数据</option><option value="framework">训练与评估框架</option><option value="simulation">交互与模拟工具</option></select></label></div><div class="toolbar"><button type="button" data-reset>重置筛选</button><button type="button" data-expand>展开来源</button><button type="button" data-collapse>收起来源</button><span class="count-output" data-count aria-live="polite"></span></div></form><noscript>JavaScript 未启用，以下完整目录仍可阅读；搜索和筛选不可用。</noscript>'''
    body += '<div class="resource-grid" style="margin-top:22px">' + ''.join(resource(row, True) for row in data['datasets']) + ''.join(resource(row, False) for row in data['tools']) + '</div><p class="empty" data-empty hidden>没有符合条件的资源。请减少关键词或重置筛选。</p></section>'
    result_status = f'当前收录 {len(results)} 条测量记录，配置与证据见结果页。' if results else '当前尚未收录测量记录。'
    body += f'<section class="scope"><h2>如何理解 Bench</h2><p>这是推荐系统自进化的轻量评测资源入口：整理资源、说明建议协议、规范结果提交。{result_status}本仓库不包含训练执行器。</p><p>真实日志、模拟用户反馈、论文中的作者报告与本站收录的测量记录属于不同证据。跨数据版本、切分、候选池或预算的分数不直接合并排名。</p><a href="results.html">查看结果状态与提交要求 →</a></section>'
    return shell('评测与复现', body, 'index.html', config)


def list_html(items):
    return '<ul>' + ''.join(f'<li>{e(x)}</li>' for x in items) + '</ul>'


def protocols(data, results, config):
    body = hero('Evaluation protocols', '让每一轮改进<br><em>都有可比较的证据</em>', '以下四套协议是本站整理的实验设计建议。先选择研究问题，再固定数据、基线、指标和预算；执行前应在仓库中冻结具体配置。')
    body += '<section><div class="protocol-tabs">' + ''.join(f'<a href="#{e(p["id"])}">{e(p["title"])}</a>' for p in data['protocols']) + '</div></section>'
    for i, protocol in enumerate(data['protocols'], 1):
        result_count = sum(record['protocol'] == protocol['id'] for record in results)
        result_status = f'已收录 {result_count} 条测量记录，详见结果页。' if result_count else '尚未收录此协议的测量记录。'
        rows = [('数据设置', e(protocol['data'])), ('必备对照', list_html(protocol['baselines'])), ('报告指标', list_html(protocol['metrics'])), ('控制变量', list_html(protocol['controls']))]
        body += f'<section class="protocol" id="{e(protocol["id"])}"><div class="eyebrow">Protocol {i:02d} / {e(protocol["id"])}</div><h3>{e(protocol["title"])}</h3><p>{e(protocol["question"])}</p><dl>' + ''.join(f'<dt>{label}</dt><dd>{value}</dd>' for label, value in rows) + f'</dl><div class="callout">主要风险：{e(protocol["risk"])}</div><p class="source-note">本站建议协议；{result_status}</p></section>'
    body += '<section class="scope"><h2>协议如何落地</h2><p>使用固定的数据版本与文件校验值，记录所有随机种子和环境依赖。公开结果时同时提交初始轮与更新轮、逐 seed 数值、总成本及证据链接。协议中的具体窗口、轮数、候选数和预算由实验者预先确定并披露。</p><a href="results.html">查看结果提交格式 →</a></section>'
    return shell('评测协议', body, 'protocols.html', config)


def results_page(results, config):
    body = hero('Results & reproducibility', '结果从证据开始，<br><em>从第 0 轮开始</em>', '只接收能对应到代码、数据协议、逐轮测量与运行日志的记录。结构校验是第一步，独立复现和人工核验仍然必要。')
    if not results:
        body += '<section class="result-empty"><strong>0</strong><h3>暂无本站统一运行结果</h3><p>当前版本提供资源目录、评测协议与提交格式。这里没有模拟榜单，也没有把不同论文的分数拼成可比排名。</p><p>待实际实验完成并核验后，结果会连同配置和证据一并发布。</p></section>'
    else:
        body += '<section>' + section_head('01 / MEASURED RECORDS', '已提交测量记录', '仅按协议阅读记录；不同配置的指标不直接排序。')
        for record in results:
            body += f'<article class="protocol" id="{e(record["id"])}"><div class="eyebrow">{e(record["protocol"])}</div><h3>{e(record["method"])}</h3><p>{e(record["dataset"]["name"])} · {e(record["dataset"]["version"])} · {len(record["seeds"])} seeds · {len(record["rounds"])} rounds</p><p class="source-note">结构与数值一致性已校验；这不表示独立复现认证。</p><div class="sources">{link(record["repository"], "代码")}{link(record["evidence_artifact_url"], "实验记录")}</div><details><summary>完整测量记录</summary><pre>{e(json.dumps(record, ensure_ascii=False, indent=2))}</pre></details></article>'
        body += '</section>'
    body += '<section id="submission">' + section_head('02 / SUBMISSION', '提交一条可核验的记录', '下载模板是开始；模板中的 null 表示尚未测量。')
    body += '''<div class="principles"><div><h3>明确实验身份</h3><p>给出代码仓库、完整 commit SHA、测量日期，以及数据版本、切分和候选集合规则。</p></div><div><h3>保留逐轮与逐 seed 数据</h3><p>至少 3 个独立随机种子，包含第 0 轮与至少 1 个更新轮次。逐 seed 数值与汇总均值、样本标准差应一致。</p></div><div><h3>公开全部成本</h3><p>记录所列实验的训练秒数、生成秒数、GPU 小时与 LLM token 总量。不适用的实际成本填写 0，未知值不得填写成 0。</p></div><div><h3>提供可访问的证据</h3><p>链接到配置、日志与必要产物。数据中的数值不能只靠手填声明，维护者需要核对原始证据。</p></div></div>
<div class="hero-actions"><a class="btn primary" href="data/result-template.json" download>下载 JSON 模板 ↓</a><a class="btn" href="data/results.json" download>下载已收录结果 ↓</a></div>
<p class="note">未填写模板的 status 为 unmeasured，校验失败是预期行为；它不会被计入结果。当前模板面向可数值化的多轮实验，不代替人工对话质量评价报告。</p>
<pre><code>python3 scripts/validate_result.py path/to/measured-result.json</code></pre>
<p class="note">校验器检查字段、有限数值、种子与轮次、逐 seed 汇总一致性及证据 URL 格式。指标可为负，以保留退化、奖励和估计值；标准差与成本必须非负。具体指标的取值范围仍需人工核对。校验器不会运行实验，也不会自动证明链接中的实验真实。</p></section>'''
    body += f'<section class="scope"><h2>提交与维护</h2><p>完成实测后，把验证通过的记录追加到 <code>data/results.json</code> 数组，附上运行配置与可访问的证据，向 <a href="{e(config["repo_url"])}">GitHub 仓库</a> 提交 Pull Request。构建时会重新校验所有记录；未完成的模板不得放入结果数组。</p><p>初始版本不设跨协议总排名。结果应按同一数据版本、切分、候选协议、模型及预算分别比较。</p></section>'
    return shell('结果与提交', body, 'results.html', config)


def main():
    data, config, results = read('data/resources.json'), read('config.json'), read('data/results.json')
    check_catalog(data)
    if not isinstance(results, list):
        raise ValueError('data/results.json must be an array')
    result_ids = set()
    for record in results:
        errors = validate(record)
        if errors:
            raise ValueError('Invalid result: ' + '; '.join(errors))
        if record['id'] in result_ids:
            raise ValueError('Duplicate result id: ' + record['id'])
        result_ids.add(record['id'])
    for name in ('styles.css', 'app.js'):
        if not (ROOT / 'assets' / name).is_file():
            raise ValueError(f'Missing assets/{name}')
    pages = {'index.html': index(data, results, config), 'protocols.html': protocols(data, results, config), 'results.html': results_page(results, config)}
    for filename, html in pages.items():
        (ROOT / filename).write_text(html, encoding='utf-8')
    if '--stage' in sys.argv:
        stage = ROOT / '_site'
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(exist_ok=True)
        for filename in pages:
            shutil.copy2(ROOT / filename, stage / filename)
        for directory in ('assets', 'data'):
            shutil.copytree(ROOT / directory, stage / directory, dirs_exist_ok=True)
        (stage / '.nojekyll').touch()
    print(f'Built {len(pages)} pages: {len(data["datasets"])} datasets, {len(data["tools"])} tools, {len(data["protocols"])} protocols, {len(results)} measured results.')


if __name__ == '__main__':
    main()
