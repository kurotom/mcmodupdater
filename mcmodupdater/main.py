# -*- coding: utf-8 -*-
"""
"""

from mcmodupdater.models import (
    CurseForgeAPI,
    ModFile
)

from mcmodupdater.utils import *

from mcmodupdater.pathclass import PathClass

from mcmodupdater.requests_handler import RequestData

from mcmodupdater.hashing import MurmurHash2CurseForge


from mcmodupdater.executorThreadsHandler import ThreadExecutor

from mcmodupdater.writer import Writer


import multiprocessing


from time import sleep

import re


from typing import (
    Literal,
    Union,
    List,
)





default_filters = [
    "forge", "cauldron", "liteloader",
    "fabric", "quilt", "neoforge",
    "neo", "jar",
]

MODLOADERS = Literal[
    'forge', 'cauldron', 'liteloader', 'fabric', 'quilt', 'neoforge'
]


class ModUpdater:
    DIRECTORY = "mods_updated"
    BASEPATH = PathClass.join(
                            PathClass.get_desktop(),
                            DIRECTORY
                        )

    def __init__(
        self,
        api_key: str,
        modloader: MODLOADERS = "forge",
        auto_report: bool = False
    ) -> None:
        """
        """
        self.api_key = api_key
        self.modloader = modloader
        self.auto_report = auto_report
        self.modloaderId = CurseForgeAPI.getModLoaderId(modloader)
        self.n_threads = max(1, multiprocessing.cpu_count() // 2)
        self.failed_update = set() #[]

    def some_errors(self) -> bool:
        """
        """
        return len(self.failed_update) > 0

    def change_api_key(
        self,
        newkey: str
    ) -> None:
        """
        """
        self.api_key = newkey

    def change_modloader(
        self,
        modloader: MODLOADERS,
    ) -> None:
        """
        """
        self.modloader = modloader
        self.modloaderId = CurseForgeAPI.getModLoaderId(modloader)


    def calculate_hashes(
        self,
        filesList: list,
    ) -> List[int]:
        """
        """
        if len(filesList) > 10:
            return ThreadExecutor.to_thread(
                                        MurmurHash2CurseForge.hash32,
                                        "Calculating hash",
                                        None,
                                        self.n_threads + 1,
                                        filesList,
                                    )
        else:
            return [
                MurmurHash2CurseForge.hash32(data=item, seed=1)
                for item in filesList
            ]

    def from_file(
        self,
        file: str,
        version: str,
        filters: list = [],
        only_release: bool = True
    ) -> dict:
        """
        """
        if PathClass.is_file(file) is False:
            return

        data = load_data(file)
        modelsData = self.to_model(
                            data=data,
                            filters=filters,
                        )

        modelsData.sort()

        mods = []

        for i in range(0, len(modelsData), 5):
            # print("Chunk ", 0 + i, 5 + i)
            # print(modelsData[0 + i : 5 + i])
            # if i == 120:
            for item in modelsData[0 + i : 5 + i]:
                print(item)

                x = self.search_mod(
                    name=item.name,
                    version=version,
                    only_release=only_release
                )
                # mods.append(x)
                if len(x) == 0:
                    print(item.name, len(x))
                sleep(1)


    def from_path(
        self,
        path: str,
        version: str,
        modloader: MODLOADERS = None,
        only_release: bool = True
    ) -> List[ModFile]:
        """
        """
        results = []
        if modloader:
            self.change_modloader(modloader)

        if PathClass.is_dir(path) is False:
            return []

        abs_path_dir = PathClass.absolute_path(path)
        dirFiles = PathClass.listdir(abs_path_dir)


        filter_jars = [
            PathClass.join(abs_path_dir, item)
            for item in dirFiles
            if PathClass.is_file(PathClass.join(abs_path_dir, item))
            if item.endswith(".jar")
        ]

        mmh2_hashes = self.calculate_hashes(filesList=filter_jars)

        results = self.get_files_by_fingerprints(
                                fingerprints=mmh2_hashes,
                                version=version,
                                modloader=self.modloader,
                                only_release=only_release,
                            )

        return results



    def get_files_by_fingerprints(
        self,
        fingerprints: List[int],
        version: str,
        modloader: List[MODLOADERS] = None,
        only_release: bool = True,
    ) -> List[ModFile]:
        """
        It obtains information from mods using their fingerprints.

        Máximum of 100 fingerprints per request.
        """
        if modloader:
            self.change_modloader(modloader)

        modslist = set()

        # prepare args for the function.
        chunks = [
            fingerprints[i: i+100]
            for i in range(0, len(fingerprints), 100)
        ]
        # print(chunks)
        args_fingerprints = [
                    (self.api_key, chunk)
                    for chunk in chunks
                ]
        # print(args_fingerprints)

        datafingerprints = ThreadExecutor.to_thread(
                                    RequestData.get_files_by_fingerprints,
                                    "Searching",
                                    False,
                                    self.n_threads + 1,
                                    args_fingerprints,
                                )

        if datafingerprints:
            if datafingerprints[0] == {}:
                return []

        # # prepare args for the function.
        # projectsIds = fingerprints  # test
        projectsIds = [
                        item["id"]
                        for items in datafingerprints
                        for item in items["exactMatches"]
                    ]

        if len(projectsIds) == 0:
            return []

        args_getmodfiles = [
                    (
                        self.api_key,
                        modId,
                        version,
                        self.modloaderId,
                        # CurseForgeAPI.getModLoaderId(modloader),
                        0
                    )
                    for modId in projectsIds
                ]
        # print(args_getmodfiles)

        datagetmodfiles = ThreadExecutor.to_thread(
                                RequestData.getModFiles,
                                "Getting files",
                                True,
                                self.n_threads + 1,
                                args_getmodfiles
                            )

        for results in datagetmodfiles:
            for id, items in results.items():
                try:
                    item = items[0]  # last element - last updated
                    modfile = ModFile(
                                id=item["id"],
                                modId=item["modId"],
                                displayName=item["displayName"],
                                fileName=item["fileName"],
                                releaseType=item["releaseType"],
                                fileLength=item["fileLength"],
                                downloadUrl=item["downloadUrl"],
                                dependencies=item["dependencies"],
                                fileFingerprint=item["fileFingerprint"],
                            )

                    if modfile.downloadUrl:
                        if only_release:
                            relType = CurseForgeAPI.releaseType["release"]
                            if modfile.releaseType == relType:
                                modslist.add(modfile)
                        else:
                            modslist.add(modfile)
                    else:
                        self.add_failed_update(modfile=modfile)

                except IndexError as e:
                    self.add_failed_update(id=id)

        return list(modslist)


    def search_mod(
        self,
        name: str,
        version: str = "last",
        only_release: bool = True
    ) -> dict:
        """
        """
        # name = name.lower()

        results = RequestData.search_mod(
            api_key=self.api_key,
            version=version,
            modloader=self.modloader,
            name=name,
            sortField="lastupdated",
        )

        # print(len(results))
        mod_matches = []

        for item in results:
            for it in item["latestFilesIndexes"]:
                if name == it["filename"]:
                    # print(it["filename"])
                    if it["gameVersion"] == version:
                        if "modLoader" in it:
                            # print(">", item["name"])
                            mod = ModFile(
                                name=item["name"],
                                filename=it["filename"],
                                slug=item["slug"],
                                modId=item["id"],
                                fileId=it["fileId"],
                                modLoader=it["modLoader"],
                                releaseType=it["releaseType"],
                                version=it["gameVersion"],
                            )
                            mod_matches.append(mod)

        if len(mod_matches) == 0:
            print(name)




        # for item in results:
        #     n = item["name"].lower().replace(" ", "")
        #     # print(n, get_names_flat(n))
        #     if name in get_names_flat(n):
        #         for it in item["latestFilesIndexes"]:
        #             if it["gameVersion"] == version:
        #                 if "modLoader" in it:
        #                     # print(item["name"])
        #                     mod = ModFile(
        #                         name=item["name"],
        #                         filename=it["filename"],
        #                         slug=item["slug"],
        #                         modId=item["id"],
        #                         fileId=it["fileId"],
        #                         modLoader=it["modLoader"],
        #                         releaseType=it["releaseType"],
        #                         version=it["gameVersion"],
        #                     )
        #                     mod_matches.append(mod)
        #
        # files = []
        # for mod in mod_matches:
        #     if mod.releaseType is not None:
        #         if only_release:
        #             if int(mod.releaseType) == CurseForgeAPI.releaseType["release"]:
        #                 files.append(mod)
        #         else:
        #             files.append(mod)

                # print(files)
                # matches[item["name"]] = files
        # return files


    def get_file(
        self,
        mod: Union[int, ModFile],
        modInstance: ModFile = None,
        modId: int = None,
        fileID: int = None,
        download: bool = False,
    ) -> None:
        """
        """
        if modInstance is None and modId is None and fileID is None:
            return None

        if modInstance is not None:
            if isinstance(modInstance, ModFile):
                modId = modInstance.modId
                fileID = modInstance.fileID

        elif modId is not None and fileID is not None:
            modId = modId
            fileID = fileID

        data = RequestData.get_file(
                                modId=modId,
                                fileId=fileID,
                                api_key=self.api_key,
                            )

        if modInstance is None:
            modInstance = ModFile(
                            name=data["displayName"],
                            filename=data["fileName"],
                            slug="",
                            modId=data["modId"],
                            fileId=data["id"]
                        )

        modInstance.fileFingerprint = data["fileFingerprint"]
        modInstance.downloadUrl = data["downloadUrl"]

        return modInstance

    def get_files(
        self,
        filesIds: list,
    ) -> None:
        """
        """
        data = RequestData.get_files(
                            filesIds=filesIds,
                            api_key=self.api_key,
                        )

    def getMod(
        self,
        modfile: ModFile
    ) -> dict:
        """
        """
        if modfile:
            modid = modfile.modId

        data = RequestData.getMod(self.api_key, modid)
        return data

    def download_file(
        self,
        modfile: ModFile
    ) -> bool:
        """
        """
        PathClass.makedirs(ModUpdater.BASEPATH)

        try:
            if modfile.downloadUrl:
                path = PathClass.join(ModUpdater.BASEPATH, modfile.fileName)

                # print(">", modfile)
                with Writer(path, "wb") as file:
                    data = RequestData.download_file(modfile.downloadUrl)
                    file.write(data)

                modfile.is_download = True

                return True

                # print(modfile)
            self.add_failed_update(modfile=modfile)
            return False

        except Exception as e:
            print(">>>", e)
            self.add_failed_update(modfile=modfile)
            return False


    def download_files(
        self,
        modfiles: List[ModFile]
    ) -> None:
        """
        """
        if not isinstance(modfiles, (list, tuple, set)):
            return
        if not modfiles:
            return

        ThreadExecutor.to_thread(
                            self.download_file,
                            "Downloading",
                            True,
                            self.n_threads + 1,
                            modfiles
                        )

    def add_failed_update(
        self,
        id: int = None,
        modfile: ModFile = None,
    ) -> None:
        """
        """
        if isinstance(id, int):
            modfile = ModFile(
                            id=id,
                            modId=id,
                        )
        try:
            self.failed_update.add(modfile)
        except Exception as e:
            print(e)

    def report_failed_updates(
        self,
        show: bool = False
    ) -> list:
        """
        If the download URL is unavailable (e.g., the mod/project
        license) or the update for the specified version cannot be
        found, please refer to the official CurseForge website.

        Returns
            list: list of filenames and URLs from the mod's website.
        """
        if not self.failed_update:
            print("All mods are updated successfully.")
            return []

        results = ThreadExecutor.to_thread(
                                        self.getMod,
                                        "Information gathering",
                                        True,
                                        self.n_threads + 1,
                                        self.failed_update
                                    )
        return self.__format_report(results)


    def __format_report(
        self,
        results: list
    ) -> list:
        """
        """
        data = []
        for item in results:
            mod_ = [
                    it
                    for it in self.failed_update
                    if item["id"] == it.modId
                ]
            if mod_:
                url = f"/files/all?page=1&pageSize=20"
                url += f"&gameVersionTypeId={self.modloaderId}"
                d = (item["name"], item["links"]["websiteUrl"] + url)
                data.append(d)
        return data





    # def get_mod_model(
    #     self,
    #     filename: str
    # ) -> None:
    #     """
    #     """
    #     data = clear_text(filename=filename, filters=default_filters)
    #     print(">>", data)
    #     return ModFile(
    #         name=data[1],
    #         filename=data[0],
    #         slug=data[1],
    #         in_db=False,
    #     )

    def to_model(
        self,
        data: list,
        # filepath: str,
        filters: list = []
    ) -> list:
        """
        """
        filters = filters + default_filters
        # data = load_data(path=filepath)
        data_clean = clear_data(
                            data=data,
                            custom_filters=filters,
                        )
        return get_models(data_clean)

    def write_report(self) -> None:
        """
        """
        if len(self.failed_update) == 0:
            return

        filename_ = "failed_mod_updates.txt"

        results = ThreadExecutor.to_thread(
                                        self.getMod,
                                        None,
                                        True,
                                        self.n_threads + 1,
                                        self.failed_update
                                    )

        list_data_formatted = self.__format_report(results)

        strings = ""
        for name, link in list_data_formatted:
            strings += f"{name}, {link}\n"

        path = PathClass.join(PathClass.get_desktop(), filename_)

        with Writer(filename=path, mode="w") as file:
            file.write(strings)

        print(f'\nReport written in "{path}".')


    def __enter__(self) -> None:
        """
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        """
        if self.auto_report:
            self.write_report()
        print("Good bye.")
