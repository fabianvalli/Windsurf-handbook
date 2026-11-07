"""Package the handbook and its comment server for IIS staging."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / 'staging'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new folder for the IIS app; default: a fresh folder under tmp/')
    parser.add_argument('--self-contained-win-x64', action='store_true',
                        help='include .NET for a 64-bit Windows IIS server with the ASP.NET Core Module installed')
    args = parser.parse_args()
    dotnet = shutil.which('dotnet')
    if not dotnet:
        parser.error('Install the .NET 10 SDK to build the review app.')
    if args.output:
        output = args.output.resolve()
        if output.exists() or output.with_name(output.name + '.zip').exists():
            parser.error('Choose a new output folder and ZIP name so a previous build is preserved.')

    subprocess.run([sys.executable, str(ROOT / 'tools' / 'build.py')], cwd=ROOT, check=True)
    if not args.output:
        temp_root = ROOT / 'tmp'
        temp_root.mkdir(exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix='handbook-review-iis-', dir=temp_root))
    else:
        output.mkdir(parents=True)

    command = [dotnet, 'publish', str(STAGING / 'ReviewServer.csproj'), '-c', 'Release',
               '-o', str(output), '--nologo']
    if args.self_contained_win_x64:
        command += ['--runtime', 'win-x64', '--self-contained', 'true', '-p:AspNetCoreHostingModel=OutOfProcess']
    subprocess.run(command, cwd=ROOT, check=True)
    if not (output / 'web.config').is_file():
        raise RuntimeError('The IIS web.config was not generated.')

    webroot = output / 'wwwroot'
    shutil.copytree(ROOT / 'dist', webroot, dirs_exist_ok=True)
    for name in ('review.css', 'review.js'):
        shutil.copy2(STAGING / 'client' / name, webroot / 'assets' / name)
    chapters_file = ROOT / 'chapters.json'
    shutil.copy2(chapters_file, output / 'chapters.json')
    for chapter in json.loads(chapters_file.read_text(encoding='utf-8')):
        slug = chapter['slug']
        html_path = webroot / (slug + '.html')
        html = html_path.read_text(encoding='utf-8')
        review_assets = (
            f'<meta name="handbook-review-page" content="{slug}">\n'
            '<link rel="stylesheet" href="assets/review.css">'
            '<script src="assets/review.js" defer></script>\n'
        )
        if html.count('</head>') != 1:
            raise ValueError(f'Expected one closing head tag in {html_path.name}.')
        html_path.write_text(html.replace('</head>', review_assets + '</head>'), encoding='utf-8', newline='\n')
    shutil.copy2(STAGING / 'README.md', output / 'IIS-SETUP.md')
    archive = shutil.make_archive(str(output), 'zip', root_dir=output)
    print(f'IIS app folder: {output}\nReview package: {archive}', flush=True)


if __name__ == '__main__':
    main()
