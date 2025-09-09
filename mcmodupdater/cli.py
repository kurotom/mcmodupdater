# -*- coding: utf-8 -*-
"""
"""

from mcmodupdater.main import ModUpdater

from mcmodupdater.utils import check_version_format


import argparse


def main():
    main_parser = argparse.ArgumentParser(
        prog="mcupdater",
        description="",
        epilog=""
    )

    main_parser.add_argument(
        "-k",
        "--key-api",
        type=str,
        required=True,
        help="",
    )

    main_parser.add_argument(
        "-p",
        "--path",
        help="",
    )

    main_parser.add_argument(
        "-m",
        "--modloader",
        default="forge",
        choices=[
            "forge", "cauldron", "liteloader", "fabric", "quilt", "neoforge"
        ],
        help="",
    )

    main_parser.add_argument(
        "-v",
        "--version",
        help="",
    )

    main_parser.add_argument(
        "--only-release",
        default=False,
        action="store_true",
        help="",
    )

    main_parser.add_argument(
        "--report-failed",
        default=False,
        action="store_true",
        help="",
    )

    main_parser.add_argument(
        "--silent",
        default=False,
        action="store_true",
        help="",
    )

    args = main_parser.parse_args()

    key_api = args.key_api
    path = args.path
    modloader = args.modloader
    version = args.version
    only_release = args.only_release
    report_failed = args.report_failed

    if not check_version_format(version=version):
        print("The argument `-v|--version` is not in the correct format.")
        return

    with ModUpdater(
        api_key=key_api,
        modloader=modloader,
        auto_report=report_failed,
    ) as updater:
        data = updater.from_path(
                            path=path,
                            version=version,
                            only_release=only_release
                        )
        updater.download_files(modfiles=data)
        if report_failed:
            report_data = updater.report_failed_updates()

            msg = "Manual update is required."
            msg += " Visit the links to download the corresponding mod."
            print(msg)
            for name, link  in report_data:
                print(name, link)
            print()



if __name__ == '__main__':
    main()
