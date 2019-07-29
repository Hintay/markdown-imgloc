#!/usr/bin/env python3
#
#  Markdown Image Localizer
#  comes with ABSOLUTELY NO WARRANTY.
#
#  Copyright (c) 2019 Hintay <hintay@me.com>
#
#  Localize the images in markdown.

import re
import os
import typing
import logging
import argparse
import requests
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

MD_IMAGE_REGEX = re.compile(r'(?P<start>!\[.*?\]\()(?P<url>http.+?)(?P<end>(?: ".*?")?\))')
HTML_IMAGE_REGEX = re.compile(r'(?P<start><img.*?src=[\'\"])(?P<url>http.+?)(?P<end>[\'\"].*?>)')


class MdImageLocalizer(object):
    def __init__(self, source_dir: Path, output_dir: Path, referer=None):
        self.output_dir = output_dir if output_dir.is_absolute() else source_dir / output_dir
        self.session = requests.session()
        if referer:
            self.session.headers['Referer'] = referer

        for source_file in source_dir.glob('**/*.md'):
            logging.debug("Processing: %s", source_file)
            # noinspection PyTypeChecker
            self.real_output_path = PurePosixPath(
                os.path.relpath(self.output_dir, source_file.parent).replace('..\\', '../')
            )  # 图片文件夹相对目录
            self.download_pics(source_file)

    def download_pics(self, article_path: Path):
        with article_path.open('r', encoding='utf-8') as fp:
            content = fp.read()
        content = MD_IMAGE_REGEX.sub(self.download_and_replace, content)
        content = HTML_IMAGE_REGEX.sub(self.download_and_replace, content)

        with article_path.open('w', encoding='utf-8') as fp:
            fp.write(content)

    def download_and_replace(self, match: typing.Match):
        img_url = match.group('url').split('!')[0]
        img_path = urlparse(img_url).path[1:]
        asset_path = self.output_dir / img_path
        replace_url = self.real_output_path / img_path

        if not asset_path.exists():  # 不存在则尝试下载
            response = self.session.get(img_url)
            if response.status_code == 200:
                asset_path.parent.mkdir(parents=True, exist_ok=True)  # 尝试创建目录
                with asset_path.open('wb') as img_fp:  # 保存图片
                    img_fp.write(response.content)
                return match.expand(r'\g<start>%s\g<end>' % replace_url)
            else:
                logging.error("Can not download images from url %s, code: %s", img_url, response.status_code)
                logging.debug(response.content)
                return match.group()
        else:
            return match.expand(r'\g<start>%s\g<end>' % replace_url)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_dir', metavar='source_dir', help='Input markdown directory for processing.')
    parser.add_argument('-o', '--output', default='assets', dest='output', help='Output directory.')
    parser.add_argument('-r', '--referer', dest='referer', help='The referer for download images.')
    return parser.parse_args()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%H:%M:%S')

    args = parse_args()
    MdImageReplace(Path(args.source_dir), Path(args.output), args.referer)
