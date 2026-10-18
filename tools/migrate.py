"""One-time migration of the 2009 PDF. Edit articles/*.html after migration."""
from pathlib import Path
import argparse
from html import escape
import difflib
import json
import re
import subprocess
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Archived one-time PDF import: overwrites reviewed articles and manifest.')
parser.add_argument('--allow-overwrite', action='store_true')
parser.add_argument('--pdf', type=Path, default=ROOT / 'source' / 'windsurf_0409.pdf')
parser.add_argument('--pdftoppm', default=shutil.which('pdftoppm'))
args = parser.parse_args()
if not args.allow_overwrite:
    parser.error('Normal builds use tools/build.py. This importer overwrites reviewed content; --allow-overwrite is required.')
PDF = args.pdf.expanduser().resolve()
if not PDF.is_file():
    parser.error('Provide the source PDF using --pdf; see the public PDF link in README.md.')
if not args.pdftoppm:
    parser.error('Install Poppler and put pdftoppm on PATH, or supply --pdftoppm.')

from PIL import Image
from pypdf import PdfReader
import pdfplumber

reader = PdfReader(PDF)
ARTICLES = ROOT / 'articles'
ASSETS = ROOT / 'assets'
EDITORIAL = ROOT / 'editorial'
for folder in [ARTICLES, ASSETS, EDITORIAL]:
    folder.mkdir(parents=True, exist_ok=True)


def page_text(index):
    page = reader.pages[index - 1]
    plain = page.extract_text()
    layout = page.extract_text(extraction_mode='layout')
    # Correct artificial spaces within words, without changing the PDF wording
    # or using layout mode's interleaved columns as the reading order.
    a = list(re.finditer(r'\S+', plain))
    b = layout.split()
    edits = []
    for op, i, j, k, l in difflib.SequenceMatcher(None, [m.group() for m in a], b, autojunk=False).get_opcodes():
        if op == 'replace' and ''.join(m.group() for m in a[i:j]) == ''.join(b[k:l]):
            edits.append((a[i].start(), a[j - 1].end(), ' '.join(b[k:l])))
    for start, end, value in reversed(edits):
        plain = plain[:start] + value + plain[end:]
    plain = re.sub(r'^\s*' + str(index) + r'\s*\n', '', plain, count=1)
    plain = re.sub(r'(?m)^\s*N\s*$', '', plain)
    plain = re.sub(r'[ \t]+\n', '\n', plain)
    return plain


pages = {i: page_text(i) for i in range(3, 22)}
source = '\n'.join(p.strip() for p in pages.values())
(EDITORIAL / 'source-2009.txt').write_text(source, encoding='utf-8')


def section(start, end, text=source):
    # Match headings at the start of a line, not mentions in running prose.
    def heading(value):
        return re.compile(r'(?m)^[ \t]*' + re.escape(value.strip()) + r'(?=[ \t\n]|$)')
    match = heading(start).search(text)
    if not match:
        raise ValueError(f'Missing heading: {start!r}')
    begin = match.end()
    final = heading(end).search(text, begin)
    if not final:
        raise ValueError(f'Missing end heading: {end!r}')
    return text[begin:final.start()].strip()


def prose(text):
    """Reflow PDF lines, retaining headings, numbered items, and bullet lists."""
    output, buffer, list_kind = [], [], None

    def flush():
        if buffer:
            value = re.sub(r'\s+', ' ', ' '.join(buffer)).strip()
            output.append('<li>' + escape(value) + '</li>' if list_kind else '<p>' + escape(value) + '</p>')
            buffer.clear()

    def close_list():
        nonlocal list_kind
        if list_kind:
            output.append('</' + list_kind + '>')
            list_kind = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            flush()
            close_list()
            continue
        match = re.match(r'^(?:([0-9]+)\.\s+|([\u2022])\s*)(.*)$', line)
        if match:
            flush()
            kind = 'ol' if match[1] else 'ul'
            if kind != list_kind:
                close_list()
                list_kind = kind
                output.append('<' + kind + '>')
            buffer.append(match[3])
        else:
            if buffer and re.search(r'[.!?:][\u201d\u2019\"]?$', buffer[-1]) and not list_kind:
                flush()
            buffer.append(line)
    flush()
    close_list()
    return '\n'.join(output)


SITE = 'https://www.cal-sailing.org'
LINKS = {
    'lessons': ('Windsurfing lessons', '/lessons-menu/windsurfing/lessons-windsurfing'),
    'signups': ('Lesson registration (login required)', '/lessons-menu/windsurfing/lesson-signups?view=lessonsignups&lessontypeid=2'),
    'ratings': ('Windsurfing ratings and tests', '/ratings-menu/rating-for-windsurf'),
    'areas': ('Sailing areas and boundaries', '/ratings-menu/sailing-areas'),
    'hours': ('Club opening and closing times', '/resources/csc-openclose-times?view=month'),
    'calendar': ('Club calendar', '/resources/calendar'),
    'videos': ('Instructional windsurfing videos', '/lessons-menu/windsurfing/videos'),
    'guide': ('The existing 10-Step Guide', '/lessons-menu/windsurfing/the-10-step-guide-to-windsurfing'),
    'fleet': ('Windsurfing fleet', '/about-us/fleet-menu/fleet-windsurfing'),
    'damage': ('Contact the windsurfing team (login required)', '/resources/contact-windsurf-vices'),
    'incident': ('Incident report', '/resources/incident-report-form'),
    'volunteer': ('Volunteering opportunities', '/memberships-menu/volunteering-opportunities'),
    'join': ('Membership', '/memberships-menu/memberships-reg'),
}


def link(key):
    label, url = LINKS[key]
    return f'<a href="{escape(SITE + url, quote=True)}">{escape(label)}</a>'


def resources(keys):
    return '<ul>\n' + '\n'.join('<li>' + link(key) + '</li>' for key in keys) + '\n</ul>'


def local(slug, title):
    return f'<a href="{slug}.html">{escape(title)}</a>'


def figure(name, alt, caption):
    im = Image.open(ASSETS / name)
    width, height = im.size
    return f'<figure><img class="img-responsive" src="assets/{name}" width="{width}" height="{height}" alt="{escape(alt, quote=True)}" loading="lazy"><figcaption>{escape(caption)}</figcaption></figure>'


def embedded(page, original_name, filename):
    item = next(i for i in reader.pages[page - 1].images if i.name == original_name)
    item.image.convert('RGB').save(ASSETS / filename, quality=94)


for args in [
    (7, 'R53.png', 'dock-layout.jpg'), (7, 'R54.jpg', 'batten-and-mast.jpg'),
    (11, 'R83.jpg', 'carrying-the-rig.jpg'), (11, 'R82.jpg', 'uphauling.jpg'),
    (12, 'R90.jpg', 'starting.jpg'), (13, 'R97.jpg', 'steering.jpg'),
    (14, 'R128.jpg', 'jibing.jpg'), (19, 'R187.jpg', 'double-half-hitch.jpg'),
    (19, 'R188.jpg', 'marlinspike-hitch.jpg'), (19, 'R189.jpg', 'clove-and-cow-hitch.jpg'),
    (21, 'R201.jpg', 'parts-of-the-rig.jpg'),
]:
    embedded(*args)

# Some original photographs are tiled inside the PDF. Render their combined
# image bounds to preserve the full sequence, labels, and original arrangement.
poppler = Path(args.pdftoppm)
with pdfplumber.open(PDF) as document, tempfile.TemporaryDirectory() as temp:
    for number, exclude, filename in [(13, 'R97', 'stance.jpg'), (14, 'R128', 'tacking.jpg'), (15, '', 'sailing-downwind.jpg')]:
        p = document.pages[number - 1]
        imgs = [i for i in p.images if i['name'] != exclude]
        bounds = (min(i['x0'] for i in imgs), min(i['top'] for i in imgs), max(i['x1'] for i in imgs), max(i['bottom'] for i in imgs))
        target = str(Path(temp) / f'page-{number}')
        subprocess.run([str(poppler), '-f', str(number), '-l', str(number), '-singlefile', '-r', '150', '-png', str(PDF), target], check=True, capture_output=True)
        image = Image.open(target + '.png')
        sx, sy = image.width / p.width, image.height / p.height
        image.crop((int(bounds[0]*sx), int(bounds[1]*sy), int(bounds[2]*sx + 1), int(bounds[3]*sy + 1))).convert('RGB').save(ASSETS / filename, quality=94)


records = []


def add(slug, title, group, summary, body, source_pages, related=(), site_links=(), notes='', status='2009 text; 2026 review pending', learning=False):
    # Blank space for a picture or a page break is not a paragraph boundary.
    while True:
        merged = False
        for match in re.finditer(r'<p>([^<]*)</p>\s*(?=<p>)', body):
            if not re.search(r'[.!?:;][\u201d\u2019\"\']?$', match[1].strip()):
                body = body[:match.start()] + '<p>' + match[1].strip() + ' ' + body[match.end() + 3:]
                merged = True
                break
        if not merged:
            break
    records.append(dict(slug=slug, title=title, group=group, summary=summary,
                        source_pages=source_pages, related=list(related), site_links=list(site_links),
                        review_status=status, editorial_notes=notes, learning=learning))
    (ARTICLES / f'{slug}.html').write_text(body.strip() + '\n', encoding='utf-8')


add('getting-started', 'Getting started at CSC', 'Before you sail',
    'Find lessons, join the club, and plan your first session.',
    '<p>Welcome to windsurfing at Cal Sailing Club. Use this handbook alongside your lessons and on-water practice.</p>'
    '<h2>Start with the club’s current information</h2>' + resources(['join', 'lessons', 'signups']) +
    '<h2>Prepare for your visit</h2><p>Check the club’s opening times and the sailing area for your rating. Follow the Day Leader’s instructions for the session.</p>' + resources(['hours', 'areas', 'ratings']) +
    '<h2>Use the handbook as you learn</h2><p>Begin with ' + local('parts-of-the-rig', 'the parts of the rig') + ' and ' + local('wind-and-direction', 'wind and direction') + '. Then follow the practical skills in order, returning to the topics you want to practice.</p>'
    '<p>The club runs through volunteer contributions. See ' + link('volunteer') + ' for ways to participate.</p>',
    [3, 4], ['novice-checklist', 'check-out-and-return', 'self-rescue'], ['lessons', 'calendar'],
    'Replaces old fixed lesson times and membership/work requirements with maintained site links.', 'New orientation; review pending')

add('ratings-and-areas', 'Ratings and sailing areas', 'Before you sail',
    'Check current requirements and the boundaries for your rating.',
    '<p>Use the club’s existing pages for rating requirements, authorized equipment, and sailing boundaries.</p>' + resources(['ratings', 'areas', 'fleet']) +
    '<p>Check the Day Leader’s restrictions before going out. Conditions may limit the equipment or area available for a session.</p>',
    [3, 4, 5, 6, 17, 18], ['getting-started', 'novice-checklist', 'self-rescue'], ['hours'],
    'Old rating tests, hours, PFD exceptions, and boundary maps are retained only in editorial/source-2009.txt. Do not republish them as current policy.', 'Maintained links; review pending')

checkout = '<h2>Signing in and out</h2>' + prose(section('Signing In / Out', 'Sailing Hours'))
checkout += '<h2>When the club is open</h2><p>Check ' + link('hours') + ' and the Day Leader’s instructions for the session.</p>'
checkout += '<h2>Sharing equipment</h2>' + prose(section('Time Limits', 'Damage Responsibility'))
add('check-out-and-return', 'Checking equipment out and back in', 'Before you sail',
    'Check out your equipment, inspect it, and record your return.', checkout,
    [6, 7], ['launching-and-landing', 'equipment-care', 'rigging'], ['hours', 'damage'],
    'Confirm the checkout system, equipment identifiers, and equipment-sharing time limit. Historical opening schedule and dinner penalty not carried forward.')

add('launching-and-landing', 'Launching and landing', 'Before you sail',
    'Handle the board and rig at the dock.',
    prose(section('Launching/Safety', 'Time Limits')) + figure('dock-layout.jpg', 'Original dock diagram showing wind, launch side, and board placement.', 'Dock layout from the 2009 handbook; confirm against the current dock.'),
    [6, 7], ['carrying-the-rig', 'uphauling', 'check-out-and-return'], ['ratings'],
    'Review dock layout and landing procedure. The current ratings page describes stopping short of the dock and paddling in; resolve before publication.')

add('rigging', 'Checking and tuning the rig', 'Equipment and reference',
    'Understand the basic rig checks and handle sails carefully.',
    prose(section('Sail Rigging\n', 'Self-Rescue Procedure')) + figure('batten-and-mast.jpg', 'Original diagram of the overlap between a batten and the mast.', 'Batten-to-mast relationship illustrated in the 2009 handbook.'),
    [7], ['parts-of-the-rig', 'knots', 'equipment-care'], ['fleet', 'lessons'],
    'Confirm tuning recommendations against current sails; the 2009 text explicitly describes equipment of its time.')

rescue = section('Self-Rescue Procedure', '\nSafety\n')
rescue = rescue.replace('Suggested Self-Rescue methods:', '\nSuggested self-rescue methods\n')
add('self-rescue', 'Self-rescue and getting back', 'Before you sail',
    'Know how to return when sailing is no longer working.', prose(rescue).replace('<p>Suggested self-rescue methods</p>', '<h2>Suggested self-rescue methods</h2>'),
    [8], ['ratings-and-areas', 'launching-and-landing', 'equipment-care'], ['areas', 'lessons'],
    'Priority review: local landmarks, recovery destinations, conditions for each method, rig release, rescue signals, and current paddle-test expectations.')

add('equipment-care', 'Equipment care and damage', 'Equipment and reference',
    'Find the current reporting route and repair instruction.',
    '<p>Inspect equipment before taking it out. If you find damage, ask the Day Leader or windsurfing team what to do with the equipment and how to report the problem.</p>' + resources(['damage', 'incident', 'lessons']) +
    '<p>The club home page also links to a board-repair tutorial. Use the maintained club resources and repair clinics for current repair instruction.</p>',
    [7, 8, 9], ['check-out-and-return', 'rigging', 'parts-of-the-rig'], ['fleet'],
    'Keep liability limits, repair restrictions, workshop locations, resin/solvent instructions, and old fleet-specific advice in the editorial source pending replacement.', 'Resource page; procedure update pending')

safety = '<h2>Safety equipment and warmth</h2>' + prose(section('\nSafety\n', 'Broken Equipment'))
safety += '<h2>If you cannot sail upwind</h2>' + prose(section("If you can't sail upwind", '5. Steering'))
add('safety-and-help', 'Safety and asking for help', 'Before you sail',
    'Prepare for cold water and recognize when you need help.', safety,
    [8, 13], ['self-rescue', 'ratings-and-areas', 'novice-checklist'], ['lessons', 'incident'],
    'Priority review: PFD guidance, equipment requirements, rescue signals, and the current recovery locations. Original third-dock/shore-walking advice is historical.')

port = section('Port and Starboard Tacks\n', 'Right-of-Way Rules')
port = re.sub(r'Boards marked with a.*', '', port, flags=re.S)
points = section('Points of Sail\n', '\nWIND\n', pages[9]) + ' ' + pages[10].strip()
add('wind-and-direction', 'Wind, direction, and points of sail', 'Learn to windsurf',
    'Recognize port and starboard tack and the main points of sail.',
    '<h2>Port and starboard</h2>' + prose(port) + '<h2>Points of sail</h2>' + prose(points),
    [9, 10], ['right-of-way', 'steering', 'glossary'], ['videos'],
    'Redraw points-of-sail diagram. Resolve overlapping angle ranges in the original text and glossary before review sign-off.')

add('right-of-way', 'Sharing the water', 'Learn to windsurf',
    'Review the handbook’s rules for meeting other sailors.',
    prose(section('Right-of-Way Rules\n', 'Points of Sail\n')),
    [9], ['wind-and-direction', 'tacking', 'jibing'], ['lessons'],
    'Priority review: the original blanket statement giving towing vessels right of way needs correction/qualification. Redraw the flowchart after the wording is approved.')

steps = [
    ('carrying-the-rig', 'Carrying the board and rig', 'Carry the equipment while keeping the sail oriented to the wind.', '1. Carrying The Rig', '2. Uphauling The Sail', [11], 'carrying-the-rig.jpg', 'Two views showing the sail orientation and carrying position.'),
    ('uphauling', 'Uphauling the sail', 'Lift the sail and settle into the basic position.', '2. Uphauling The Sail', '3. Startup Sequence', [11,12], 'uphauling.jpg', 'Original uphauling sequence showing board alignment and foot placement.'),
    ('starting', 'Starting and controlling power', 'Move from the basic position to sailing.', '3. Startup Sequence', '4. Sailing Stance', [12], 'starting.jpg', 'Four panels showing the startup sequence, labelled A through D.'),
    ('stance', 'Sailing stance and balance', 'Keep your stance balanced as the wind changes.', '4. Sailing Stance', '5. Steering', [12,13], 'stance.jpg', 'Four original stance examples, labelled A through D.'),
    ('steering', 'Steering upwind and downwind', 'Use the sail position to change the board’s direction.', '5. Steering', '6. Tacking', [13,14], 'steering.jpg', 'Two panels showing sail positions for steering upwind and downwind.'),
    ('tacking', 'Tacking: turning through the wind', 'Change direction by turning the bow into the wind.', '6. Tacking', '7. Nonplaning Jibe', [14], 'tacking.jpg', 'Four original photographs showing the tack, labelled A through D.'),
    ('jibing', 'The nonplaning jibe', 'Change direction by turning away from the wind.', '7. Nonplaning Jibe', '8. Sailing Downwind', [14,15], 'jibing.jpg', 'Five original views of the nonplaning jibe, labelled A through E.'),
    ('sailing-downwind', 'Sailing downwind', 'Practice a run and return to a normal sailing position.', '8. Sailing Downwind', '9. High Wind Sailing', [15], 'sailing-downwind.jpg', 'Original photograph showing the sailing-downwind position.'),
    ('high-wind', 'Building skills in higher winds', 'Understand how the handbook adapts the basic skills to stronger wind.', '9. High Wind Sailing', '10. Free Style', [15,16], None, None),
    ('freestyle', 'Light-wind practice and freestyle', 'Explore the original guide’s additional balance and rig-handling exercises.', '10. Free Style', 'Appendices', [16], None, None),
]
learning_slugs = [item[0] for item in steps]
learning_source = source[source.index('The 10 Step Guide to Windsurfing'):]
for i, (slug, title, summary, start, end, numbers, image, alt) in enumerate(steps):
    text = section(start, end, learning_source)
    text = re.sub(r'^\s*\(aka coming about\)', '', text)
    if slug == 'uphauling':
        text = re.sub(r'Choosing the right size of sail.*?time out\.', '', text, flags=re.S)
        text = re.sub(r"Don't pull\s+hard", "Don't pull hard", text)
    if slug == 'steering':
        text = re.sub(r'(?m)^\s*(WIND|Tacking|Jibing)\s*$', '', text)
    if slug == 'stance':
        text = text[:text.index('If you can\'t sail upwind')]
        text = text.replace('Centerboard Position', '\nCenterboard position\n')
    body = prose(text)
    body = body.replace('<p>Centerboard position ', '<h2>Centerboard position</h2><p>')
    body = body.replace('<p>Centerboard position</p>', '<h2>Centerboard position</h2>')
    if image:
        body += figure(image, alt, 'Original illustration from Bill Prinzmetal’s 10-Step Guide in the 2009 CSC handbook.')
    nearby = learning_slugs[max(0,i-1):i] + learning_slugs[i+1:i+2]
    nearby += ['self-rescue'] if slug in ['uphauling', 'high-wind'] else ['wind-and-direction']
    notes = 'Preserved from the PDF; modernize wording and diagrams when this section is reviewed.'
    if slug == 'freestyle':
        notes = 'Review which exercises belong in a beginner handbook, particularly high-wind head dips and historical anecdotes.'
    add(slug, title, 'Learn to windsurf', summary, body, numbers, nearby, ['videos', 'guide'], notes, learning=True)

knots = section('C. Knots.', 'D. Glossary.')
knot_parts = [
    ('Double half hitch on a bight (loop).', 'Marlinspike hitch.', 'double-half-hitch.jpg', 'Original three-panel double half hitch sequence.'),
    ('Marlinspike hitch.', 'Clove hitch and Cow Hitch.', 'marlinspike-hitch.jpg', 'Original marlinspike hitch tying sequence.'),
    ('Clove hitch and Cow Hitch.', None, 'clove-and-cow-hitch.jpg', 'Original comparison of cow hitch and clove hitch on a boom.'),
]
knot_body = '<p>These knots appear in the original handbook’s equipment reference.</p>'
for start, end, filename, alt in knot_parts:
    text = section(start, end, knots) if end else knots[knots.index(start)+len(start):]
    knot_body += '<h2>' + escape(start.rstrip('.')) + '</h2>' + prose(text) + figure(filename, alt, 'Original knot illustration from the 2009 handbook.')
add('knots', 'Useful knots', 'Equipment and reference',
    'Identify the knots used around the club and in the original rigging guide.', knot_body,
    [19], ['rigging', 'parts-of-the-rig'], ['lessons'],
    'Review improvised harness-line and downhaul advice. Redraw the knot illustrations with clear over/under crossings.')

glossary = section('D. Glossary.', 'F. Parts of the Rig.')
glossary = glossary[glossary.index('Apparent wind.'):]
glossary = glossary.replace('wind .Leeward.', 'wind.\nLeeward.')
glossary = re.sub(r'\.?\s*Leeward\.\s*', '.\nLeeward. ', glossary, count=1)
terms = []
for line in glossary.splitlines():
    match = re.match(r'^([A-Z][A-Za-z ()/+-]{1,55})\s*[.:]\s+(.*)', line.strip())
    if match:
        terms.append([match[1].strip(), match[2]])
    elif terms:
        terms[-1][1] += ' ' + line.strip()
glossary_body = '<p>Terms used throughout the handbook. Definitions are carried over from the 2009 edition.</p><dl>'
for term, definition in terms:
    glossary_body += '<dt>' + escape(term) + '</dt><dd>' + escape(re.sub(r'\s+', ' ', definition).strip()) + '</dd>\n'
glossary_body += '</dl>'
add('glossary', 'Windsurfing glossary', 'Equipment and reference',
    'Look up sailing directions, equipment names, and common instructions.', glossary_body,
    [19,20,21], ['wind-and-direction', 'parts-of-the-rig'], ['guide'],
    'Review old fleet descriptions and workshop locations. Check the original CE/CLR wording and all angle ranges.')

add('parts-of-the-rig', 'Parts of the board and rig', 'Equipment and reference',
    'Put names to the equipment used in lessons.',
    '<p>Use this diagram to identify the parts mentioned in the handbook. Board and sail designs vary.</p>' +
    figure('parts-of-the-rig.jpg', 'Labelled rig and board: mast cap, head, mast, leech, battens, luff, boom, uphaul, outhaul, clew, foot, downhaul, universal, fin, and centerboard.', 'Original equipment diagram from the 2009 CSC handbook.') +
    '<p>For definitions, see the ' + local('glossary', 'glossary') + '.</p>',
    [21], ['rigging', 'glossary', 'carrying-the-rig'], ['fleet'],
    'Replace the raster illustration with an editable SVG during the illustration pass.')

checklist = section('B. 16 Things Novices Should know', 'C. Knots.')
add('novice-checklist', 'Novice study checklist', 'Before you sail',
    'Use the original questions to identify topics to review.',
    '<p>These are the study questions from the 2009 handbook. This draft is a reading checklist; use the current ratings page for test requirements.</p>' + prose(checklist),
    [18], ['ratings-and-areas', 'self-rescue', 'check-out-and-return'], ['ratings', 'lessons'],
    'Rewrite questions with the updated procedures, particularly PFDs, time limits, local landmarks, volunteer requirements, and self-rescue.')

(ROOT / 'manifest.json').write_text(json.dumps(dict(title='CSC Windsurfing Handbook', source_pdf='https://static.cal-sailing.org/images/official_files/windsurf_0409.pdf', source_edition='April 2009', migration_date='2026-10-16', published=False, pages=records, site_links=LINKS), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Migrated {len(records)} topic articles and {len(list(ASSETS.iterdir()))} illustrations. Review before publication.')
