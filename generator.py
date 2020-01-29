#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Author: Michaël Arnauts
# Manage a Kodi addon repository with already build zip files.
# Based on various Kodi repository generators online.

import hashlib
import os
import re
import xml.etree.ElementTree as ET
from functools import cmp_to_key
from zipfile import ZipFile

REPO_DIR = 'repo/'


class AddonsGenerator:
    def __init__(self, path, previous_versions):
        self.generate_addons_xml(path, previous_versions)
        self.generate_md5(os.path.join(path, 'addons.xml'), os.path.join(path, 'addons.xml.md5'))

    def generate_addons_xml(self, path, previous_versions=0):
        """ Generate the addons.xml file and extract assets. """
        addons_file = os.path.join(path, 'addons.xml')

        xmls = []
        # Loop over all addons
        for addon_path in self._get_addons(path):

            # Loop over all files of this addon
            index = 0
            addon_files = sorted(os.listdir(addon_path), key=cmp_to_key(self._file_compare_version), reverse=True)
            for addon_file in addon_files:
                # Stop when we have the requested previous_versions
                if index > previous_versions:
                    break
                # Skip non-zip files
                if not addon_file.endswith('.zip'):
                    continue

                xmls.append(
                    self._process_addon_zip(addon_path, addon_file, index == 0)
                )
                index += 1

        # Generate XML
        addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
        addons_xml += ''.join(xmls)
        addons_xml += '</addons>'

        # Save the XML file
        with open(addons_file, 'w', encoding='utf-8') as f:
            f.write(addons_xml)

    def _process_addon_zip(self, addon_path, addon_file, copy=False):
        """ Process the specified zip file of the specified addon. """
        addon_folder_name = os.path.basename(addon_path)

        with ZipFile(os.path.join(addon_path, addon_file)) as z:
            xml = z.read(os.path.join(addon_folder_name, 'addon.xml')).decode('utf-8')

            # Parse thie metadata from addon.xml
            metadata = self.parse_metadata(xml)

            # Copy out the changelog if it exists
            if metadata['changelog']:
                with open(os.path.join(addon_path, 'changelog-%s.txt' % metadata['version']), 'wb') as f:
                    f.write(metadata['changelog'].encode('utf-8'))

            if copy:
                # Copy out the icon
                with open(os.path.join(addon_path, os.path.basename(metadata['icon'])), 'wb') as f:
                    f.write(z.read(os.path.join(addon_folder_name, metadata['icon'])))

                # Copy out the fanart
                with open(os.path.join(addon_path, os.path.basename(metadata['fanart'])), 'wb') as f:
                    f.write(z.read(os.path.join(addon_folder_name, metadata['fanart'])))

        # Modify the XML so the icon paths are correct
        xml = re.sub(r'(?<=<icon>).*(?=</icon>)', os.path.basename(metadata['icon']), xml)
        xml = re.sub(r'(?<=<fanart>).*(?=</fanart>)', os.path.basename(metadata['fanart']), xml)

        return self._clean_xml(xml)

    @staticmethod
    def _get_addons(path):
        """ Return a list of all addons that are managed in this repository. """
        addons = []
        dir_list = sorted(os.listdir(path))
        for item in dir_list:
            full_path = os.path.join(path, item)

            # Check if it is a real directory
            if not os.path.isdir(full_path):
                continue

            addons.append(full_path)
        return addons

    @staticmethod
    def _file_compare_version(item1, item2):
        """ This file version compare accept this file name format: some_name-0.15.11.zip. """
        if '-' in item1 and '-' in item2:
            version1 = item1.split('-')[1][0:-4]
            version2 = item2.split('-')[1][0:-4]
            if list(map(int, version1.split('.'))) < list(map(int, version2.split('.'))):
                return -1
            else:
                return 1
        return 0

    @staticmethod
    def parse_metadata(xml):
        """ Parse an addon.xml and return the metadata. """
        tree = ET.fromstring(xml)  # type: xml.etree.ElementTree.Element

        metadata = {
            'name': tree.get('id'),
            'version': tree.get('version'),
            'icon': tree.find("./extension[@point='xbmc.addon.metadata']/assets/icon").text,
            'fanart': tree.find("./extension[@point='xbmc.addon.metadata']/assets/fanart").text,
        }

        # Parse optional news section
        changes = tree.find("./extension[@point='xbmc.addon.metadata']/news")
        metadata['changelog'] = changes.text.strip() if changes is not None else None

        return metadata

    @staticmethod
    def _clean_xml(xml):
        """ Remove the <?xml lines from the xml. """
        xml_formatted = ''
        for line in xml.split('\n'):
            if line.find('<?xml') >= 0:
                continue
            xml_formatted += line + '\n'
        return xml_formatted

    @staticmethod
    def generate_md5(source, destination):
        """ Generate a md5sum of <source> and save it to <destination>. """
        with open(source, 'r', encoding='utf-8') as f:
            md5sum = hashlib.md5(f.read().encode('utf-8')).hexdigest()

        with open(destination, 'w', encoding='utf-8') as f:
            f.write(md5sum)


if __name__ == "__main__":
    AddonsGenerator(path=REPO_DIR, previous_versions=2)
