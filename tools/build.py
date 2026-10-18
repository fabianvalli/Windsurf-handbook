"""Build three handbook chapters, forwarding pages, and Joomla bodies."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
DIST, JOOMLA = ROOT / 'dist', ROOT / 'joomla'
manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
topics = {p['slug']: p for p in manifest['pages']}
SITE = 'https://www.cal-sailing.org'
CSS = ['/templates/ja_edenite_ii/local/css/themes/orange/bootstrap.css', '/templates/ja_edenite_ii/local/css/themes/orange/legacy-grid.css', '/templates/ja_edenite_ii/local/css/themes/orange/template.css', '/templates/ja_edenite_ii/css/custom.css']
PROPOSED_ROUTE = '/lessons-menu/windsurfing/handbook'
IMAGE_ROUTE = '/images/windsurfing/handbook-2026'
CHAPTERS = [
    dict(slug='index', title='Before you sail', description='Start with the club, check its rules, and prepare for your session from signout to return.', topics=['getting-started', 'ratings-and-areas', 'safety-and-help', 'check-out-and-return', 'launching-and-landing', 'self-rescue', 'novice-checklist']),
    dict(slug='sailing-skills', title='Sailing skills', description='Use the wind and right-of-way illustrations, then practice the handbook’s lessons in order. Higher-wind practice comes later.', topics=['wind-and-direction', 'right-of-way', 'carrying-the-rig', 'uphauling', 'starting', 'stance', 'steering', 'tacking', 'sailing-downwind', 'jibing', 'high-wind', 'freestyle']),
    dict(slug='equipment-reference', title='Equipment & reference', description='Know your board and rig, check your equipment, and look up the terms used in lessons.', topics=['parts-of-the-rig', 'rigging', 'equipment-care', 'knots', 'glossary']),
]
topic_chapter = {s: c for c in CHAPTERS for s in c['topics']}
assert set(topic_chapter) == set(topics)
assert sum(len(c['topics']) for c in CHAPTERS) == len(topics)


def topic_url(slug):
    return 'index.html' if slug == 'index' else topic_chapter[slug]['slug'] + '.html#' + slug


def rewrite_links(body):
    for slug in topics:
        body = body.replace(f'href="{slug}.html"', f'href="{topic_url(slug)}"')
    return body


def sidebar(chapter):
    body = '<nav aria-label="Handbook chapters"><h2 class="module-title">In this handbook</h2><ol class="nav nav-pills nav-stacked hb-chapter-links">'
    for n, c in enumerate(CHAPTERS, 1):
        active = ' class="active"' if c == chapter else ''
        current = ' aria-current="page"' if c == chapter else ''
        body += f'<li{active}><a href="{c["slug"]}.html"{current}>{n}. {escape(c["title"])}</a></li>'
    body += '</ol></nav><nav aria-label="Sections on this page"><h3>On this page</h3><ol class="hb-section-links">'
    for slug in chapter['topics']:
        body += f'<li><a href="#{slug}">{escape(topics[slug]["title"])}</a></li>'
    body += '</ol></nav>'
    return '<aside class="hb-sidebar" aria-label="Handbook shortcuts"><details class="hb-contents" open><summary><strong>Handbook shortcuts</strong><span class="hb-current-chapter">' + escape(chapter['title']) + '</span></summary><div class="hb-contents-body">' + body + '</div></details></aside>'


def chapter_tabs(chapter):
    body = '<nav class="hb-chapters" aria-label="Reading sequence">'
    for n, c in enumerate(CHAPTERS, 1):
        current = ' aria-current="page"' if c == chapter else ''
        body += f'<a class="panel panel-default hb-chapter-tab" href="{c["slug"]}.html"{current}><small>PART {n}</small><strong>{escape(c["title"])}</strong></a>'
    return body + '</nav>'


def section_body(slug):
    p = topics[slug]
    body = (ROOT / 'articles' / (slug + '.html')).read_text(encoding='utf-8')
    body = rewrite_links(re.sub(r'<(/?)h2\b', r'<\1h3', body))
    chapter = topic_chapter[slug]
    position = chapter['topics'].index(slug)
    following = chapter['topics'][position + 1] if position + 1 < len(chapter['topics']) else None
    prose_links = set(re.findall(r'<a\b[^>]*\bhref="([^"]+)"', body))
    related = [s for s in dict.fromkeys(p['related'])
               if s != following and topic_url(s) not in prose_links][:3]
    if related:
        body += '<nav class="hb-related" aria-label="Continue after ' + escape(p['title'], quote=True) + '">'
        body += '<p><strong>Related:</strong> ' + ' · '.join('<a href="' + topic_url(s) + '">' + escape(topics[s]['title']) + '</a>' for s in related) + '</p>'
        body += '</nav>'
    return body


def component(chapter, show_title=True):
    n = CHAPTERS.index(chapter) + 1
    body = '<div class="hb-app" id="handbook-content">' + sidebar(chapter)
    body += f'<article class="t3-content hb-content"><header class="hb-intro"><p class="hb-eyebrow">Windsurfing handbook · Part {n} of 3</p>'
    if show_title:
        body += '<h1>' + escape(chapter['title']) + '</h1>'
    body += '<p class="lead">' + escape(chapter['description']) + '</p></header>' + chapter_tabs(chapter)
    body += '<div class="alert alert-warning hb-draft" role="note"><strong>2026 review draft.</strong> Procedures and original illustrations are awaiting updates. Follow current club requirements and the Day Leader’s instructions.</div>'
    body += '<div class="hb-section-tools"><p>Open a section to read or practice a topic.</p><div class="hb-controls"><button class="btn btn-default" type="button" data-expand="true">Expand all</button><button class="btn btn-default" type="button" data-expand="false">Collapse all</button></div></div><div class="hb-sequence">'
    for i, slug in enumerate(chapter['topics'], 1):
        p = topics[slug]
        opened = ' open' if i == 1 else ''
        body += f'<details class="panel panel-default hb-section" id="{slug}" data-topic{opened}><summary class="panel-heading"><h2 class="panel-title"><span class="hb-step" aria-hidden="true">{i:02}</span><span class="hb-section-label"><strong title="{escape(p["title"], quote=True)}">{escape(p["title"])}</strong><small>{escape(p["summary"])}</small></span><span class="hb-toggle" aria-hidden="true">+</span></h2></summary><div class="panel-body hb-section-body">' + section_body(slug) + '</div></details>'
    body += '</div><nav class="hb-next-chapter" aria-label="Next chapter">'
    if n > 1:
        previous = CHAPTERS[n - 2]
        body += f'<a href="{previous["slug"]}.html">← {escape(previous["title"])}</a>'
    if n < len(CHAPTERS):
        following = CHAPTERS[n]
        body += f'<a class="btn btn-primary" href="{following["slug"]}.html">Continue: {escape(following["title"])} →</a>'
    return body + '</nav><p class="text-muted hb-credit">Based on the CSC handbook revised April 2009. The 10-Step Guide is by Bill Prinzmetal; the source’s 2007 revision credits photographs by Rob Weinberg. Original artwork is retained during the 2026 review.</p></article></div>'


def site_shell(content, chapter):
    css = '\n'.join(f'<link rel="stylesheet" href="{SITE}{path}">' for path in CSS)
    links = [('About', '/about-us/who-we-are'), ('Membership', '/memberships-menu/memberships-registration'), ('Lessons', '/lessons-menu/windsurfing/lessons-windsurfing'), ('Ratings', '/ratings-menu/rating-for-windsurf'), ('Activities', '/activities/racing'), ('Resources', '/resources/calendar'), ('Blog', '/blogfrontpage/recent-blog-posts'), ('Gallery', 'https://cal-sailing.smugmug.com/')]
    nav = '<ul class="nav navbar-nav">' + ''.join('<li><a href="' + (path if path.startswith('https:') else SITE + path) + '">' + title + '</a></li>' for title, path in links) + '</ul>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">
<meta name="description" content="{escape(chapter['description'], quote=True)}"><title>{escape(chapter['title'])} | CSC Windsurfing Handbook</title>
{css}
<link rel="stylesheet" href="assets/handbook.css"><script src="assets/handbook.js" defer></script></head>
<body class="hb-preview csc-handbook-page"><a class="sr-only sr-only-focusable" href="#handbook-content">Skip to handbook content</a><div class="t3-wrapper">
<header id="t3-header" class="t3-header hb-utility"><div><a class="btn btn-default" href="{SITE}/memberships-menu/memberships-registration">Join now</a> <a class="btn btn-default" href="{SITE}/login">Login</a></div><a class="btn btn-default" href="{SITE}/resources/csc-openclose-times?view=month">Club opening times</a></header>
<div id="t3-banner" class="t3-banner-header container"><div class="col-xs-12 t3-banner"><a href="{SITE}/"><img src="https://static.cal-sailing.org/media/header/CSC_logo.png" alt="Cal Sailing Club, Berkeley" id="csc_logo" width="410" height="70"></a></div></div>
<nav id="t3-mainnav" class="wrap navbar navbar-default t3-mainnav" aria-label="Cal Sailing Club"><div class="mainnav-inner clearfix hb-global-nav"><details class="hb-site-menu" open><summary class="navbar-brand">Menu</summary>{nav}</details><ul class="nav navbar-nav hb-actions"><li class="active"><a class="hb-donate" href="{SITE}/donation">Donate</a></li></ul></div></nav>
<nav aria-label="Breadcrumb" class="hb-breadcrumb"><ol class="breadcrumb"><li><a href="{SITE}/">Cal Sailing Club</a></li><li><a href="index.html">Windsurfing handbook</a></li><li class="active" aria-current="page">{escape(chapter['title'])}</li></ol></nav>
<main id="t3-mainbody" class="t3-mainbody">{content}</main><footer class="wrap t3-footer hb-footer"><p><a href="{SITE}/contact-webmaster">Contact Webmaster</a> · <a href="{SITE}/privacy-policy">Privacy Policy</a></p><p>© 2026 Cal Sailing Club · Windsurfing handbook review draft</p></footer></div></body></html>'''


def joomla_body(content):
    content = content.replace('src="assets/', f'src="{IMAGE_ROUTE}/')
    content = content.replace('href="assets/', f'href="{IMAGE_ROUTE}/')
    for c in CHAPTERS:
        route = PROPOSED_ROUTE if c['slug'] == 'index' else PROPOSED_ROUTE + '/' + c['slug']
        content = content.replace(f'href="{c["slug"]}.html', f'href="{route}')
    return content


for folder in [DIST, JOOMLA, ROOT / 'editorial']:
    folder.mkdir(exist_ok=True)
shutil.copytree(ROOT / 'assets', DIST / 'assets', dirs_exist_ok=True)
for c in CHAPTERS:
    (DIST / (c['slug'] + '.html')).write_text(site_shell(component(c), c), encoding='utf-8', newline='\n')
    (JOOMLA / (c['slug'] + '.html')).write_text(joomla_body(component(c, show_title=False)) + '\n', encoding='utf-8', newline='\n')
for slug in topics:
    url = topic_url(slug)
    legacy = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow"><title>{escape(topics[slug]["title"])}</title><meta http-equiv="refresh" content="0;url={url}"></head><body><p>This topic has moved. <a href="{url}">Read {escape(topics[slug]["title"])}</a>.</p></body></html>'
    (DIST / (slug + '.html')).write_text(legacy, encoding='utf-8', newline='\n')
    (JOOMLA / (slug + '.html')).write_text(joomla_body('<p>This topic has moved. <a href="' + url + '">Read ' + escape(topics[slug]['title']) + '</a>.</p>'), encoding='utf-8', newline='\n')
routes = [dict(file=c['slug'] + '.html', article_title=c['title'], proposed_route=PROPOSED_ROUTE if c['slug'] == 'index' else PROPOSED_ROUTE + '/' + c['slug'], published=False) for c in CHAPTERS]
(JOOMLA / 'routes.json').write_text(json.dumps(routes, indent=2) + '\n', encoding='utf-8', newline='\n')
redirects = {s: joomla_body('<a href="' + topic_url(s) + '">').split('"')[1] for s in topics}
(JOOMLA / 'legacy-redirects.json').write_text(json.dumps(redirects, indent=2) + '\n', encoding='utf-8', newline='\n')
(ROOT / 'chapters.json').write_text(json.dumps(CHAPTERS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
review = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Editorial review</title></head><body><h1>Handbook review</h1><p>Three subject pages with 24 collapsible sections. All content awaits 2026 review. PDF references use physical pages.</p><table border="1" cellpadding="8"><caption>Section review register</caption><thead><tr><th scope="col">Section</th><th scope="col">Chapter</th><th scope="col">PDF pages</th><th scope="col">Status</th><th scope="col">Editorial work</th></tr></thead><tbody>'
for slug, p in topics.items():
    review += '<tr><th scope="row"><a href="../dist/' + topic_url(slug) + '">' + escape(p['title']) + '</a></th><td>' + escape(topic_chapter[slug]['title']) + '</td><td>' + ', '.join(map(str, p['source_pages'])) + '</td><td>' + escape(p['review_status']) + '</td><td>' + escape(p['editorial_notes']) + '</td></tr>'
(ROOT / 'editorial' / 'review.html').write_text(review + '</tbody></table><p>The 24 editable article fragments are source sections, not separate reading pages. Historical source is retained in source-2009.txt.</p></body></html>', encoding='utf-8', newline='\n')


class CheckHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.h1s, self.sections = [], [], 0, []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if 'id' in d: self.ids.append(d['id'])
        if tag == 'a' and 'href' in d: self.links.append(d['href'])
        if tag == 'h1': self.h1s += 1
        if tag == 'details' and 'data-topic' in d: self.sections.append(d['id'])
        if tag == 'img':
            assert d.get('alt'), 'Image without alternative text'
            if not d['src'].startswith('https:'): assert (DIST / d['src']).is_file(), d['src']
        if tag in ['link', 'script']:
            url = d.get('href', d.get('src', ''))
            if url and not url.startswith('https:'): assert (DIST / url).is_file(), url


parsers = {}
for file in DIST.glob('*.html'):
    p = CheckHTML()
    text = file.read_text(encoding='utf-8')
    p.feed(text)
    assert len(p.ids) == len(set(p.ids)), f'Duplicate ID: {file.name}'
    assert '\ufffd' not in text
    parsers[file.name] = p
for c in CHAPTERS:
    p = parsers[c['slug'] + '.html']
    assert p.h1s == 1 and p.sections == c['topics'], c['slug']
for name, p in parsers.items():
    for href in p.links:
        if href.startswith(('http:', 'https:', 'mailto:')): continue
        if href.startswith('assets/'):
            assert (DIST / href).is_file(), f'Missing linked asset in {name}: {href}'
            continue
        path, _, fragment = href.partition('#')
        dest = parsers.get(path or name)
        assert dest is not None, f'Broken page in {name}: {href}'
        if fragment: assert fragment in dest.ids, f'Broken anchor in {name}: {href}'
print('Built 3 subject pages with 24 collapsible sections. Old topic links forward to their sections. Links, anchors, assets, and section coverage passed.')
