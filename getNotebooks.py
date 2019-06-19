#!/usr/bin/python
# encoding: utf-8

from __future__ import unicode_literals

import os
import sys
import re
import argparse
import plistlib

from workflow import Workflow3, ICON_INFO, ICON_WARNING

__version__ = '1.1'

wf = None
log = None

HELP_URL = 'https://github.com/kevin-funderburg/alfred-microsoft-onenote-navigator'

# GitHub repo for self-updating
UPDATE_SETTINGS={'github_slug': 'kevin-funderburg/alfred-microsoft-onenote-navigator'}

DEFAULT_SETTINGS = {'urlbase': "null"}

ONENOTE_PLIST = os.path.expanduser("~/Library/Group Containers/UBF8T346G9.Office/OneNote/ShareExtension/Notebooks.plist")
ICON_APP = "/Applications/Microsoft OneNote.app/Contents/Resources/OneNote.icns"
DATA_DIR = os.path.expanduser("~/Library/Application Support/Alfred/Workflow Data/com.kfunderburg.oneNoteNav/")
DATA_FILE = DATA_DIR + "data.plist"
SETTINGS_PATH = os.path.expanduser(DATA_DIR) + "settings.plist"


def main(wf):
    if not os.path.exists(SETTINGS_PATH):
        log.info("no settings set, creating default settings")
        plistlib.writePlist(DEFAULT_SETTINGS, SETTINGS_PATH)

    settings = plistlib.readPlist(SETTINGS_PATH)

    if wf.update_available:
        # Add a notification to top of Script Filter results
        wf.add_item('New version available',
                    'Action this item to install the update',
                    autocomplete='workflow:update',
                    icon=ICON_INFO)
    # build argument parser to parse script args and collect their
    # values
    parser = argparse.ArgumentParser()
    # add an optional (nargs='?') --seturl argument and save its
    # value to 'urlbase' (dest).
    parser.add_argument('--seturl', dest='urlbase', nargs='?', default=None)
    parser.add_argument('--type', dest='type', nargs='?', default=None)
    parser.add_argument('query', nargs='?', default=None)
    args = parser.parse_args(wf.args)

    ####################################################################
    # Save the provided URL base
    ####################################################################
    log.debug("arg is type: {0}".format(args.type))

    if args.urlbase:  # Script was passed as a URL
        if 'onenote:https' in args.urlbase:
            # extract onenote url
            args.urlbase = re.search('(onenote.*/Documents/).*', args.urlbase).group(1)
            plistlib.writePlist({"urlbase": args.urlbase}, SETTINGS_PATH)
            wf.add_item("url set successfully",
                        valid=False,
                        icon=ICON_INFO)
            return 0
        else:
            wf.add_item("The argument is not a OneNote URL string",
                        "right click a OneNote page/section/notebook and click 'Copy Link to Page' and try again",
                        valid=False,
                        icon=ICON_WARNING)
            wf.send_feedback()
            return 0

    ####################################################################
    # Check that we have a URL saved
    ##################################################################
    if settings['urlbase'] == "null":
        wf.add_item('No URL set yet.',
                    'Please use seturl to set your OneNote url base.',
                    valid=False,
                    icon=ICON_WARNING)
        wf.send_feedback()
        return 0

    if args.type == 'notebook':
        # get plist data from OneNote plist
        onenote_pl = plistlib.readPlist(ONENOTE_PLIST)
        # write all notebook plist data to data.plist for later iterations
        plistlib.writePlist(onenote_pl, DATA_FILE)

        for n in onenote_pl:
            it = wf.add_item(title=n["Name"],
                             subtitle="View " + n["Name"] + "'s sections",
                             arg=n["Name"],
                             autocomplete=n["Name"],
                             valid=True,
                             icon="icon.png",
                             icontype="file",
                             quicklookurl=ICON_APP)
            it.setvar('subPreFix', "")
            it.setvar('notebook', n["Name"])
            it.setvar('theURL', "")
            it.add_modifier('cmd',
                            subtitle="{0}{1}".format(settings['urlbase'], n["Name"]),
                            arg="{0}{1}".format(settings['urlbase'], n["Name"]),
                            valid=True)

        if len(wf._items) == 0:
            wf.add_item('No notebooks found', icon=ICON_WARNING)
            wf.send_feedback()
            return 0

        wf.send_feedback()
        return 0

    if args.type == 'section':
        notebook = os.getenv('notebook')
        q = os.getenv('q')

        if notebook is None:
            notebook = q
        found = False

        pl = plistlib.readPlist(DATA_FILE)
        for p in pl:
            if p["Name"] == q:
                found = True
                break

        if not found:
            wf.add_item('No section ' + q + 'was found', icon=ICON_WARNING)
            wf.send_feedback()
            return 0

        if "Children" in p:
            # write children of current section to data.plist for further iterations
            plistlib.writePlist(p["Children"], DATA_FILE)
            for c in p["Children"]:
                subPreFix = os.getenv("subPreFix")
                theURL = os.getenv("theURL")

                if (subPreFix == "") or (subPreFix is None):
                    subPreFix = "{0} > {1}".format(notebook, c["Name"])
                else:
                    subPreFix = "{0} > {1}".format(subPreFix, c["Name"])

                if (theURL == "") or (theURL is None):
                    theURL = "{0}{1}/{2}".format(settings['urlbase'], notebook, c["Name"])
                else:
                    theURL = "{0}/{1}".format(theURL, c["Name"])

                it = wf.add_item(title=c["Name"],
                                 subtitle=subPreFix,
                                 arg=c["Name"],
                                 autocomplete=c["Name"],
                                 valid=True,
                                 icon="icons/section.png",
                                 icontype="file",
                                 quicklookurl=ICON_APP)
                it.setvar('subPreFix', subPreFix)
                it.setvar('theURL', theURL)
                it.setvar('leaf', "false")
                it.add_modifier('cmd', subtitle=theURL, arg=theURL, valid=True)
        else:
            # section has no children so can't go any deeper
            theURL = os.getenv("theURL")
            theURL += ".one"

            it = wf.add_item(title=p["Name"],
                             subtitle=theURL,
                             arg=theURL,
                             autocomplete=p["Name"],
                             valid=True,
                             icon="icons/page.png",
                             icontype="file",
                             quicklookurl=ICON_APP)
            it.setvar('leaf', "true")

        if len(wf._items) == 0:
            wf.add_item('No sections found', icon=ICON_WARNING)
            wf.send_feedback()
            return 0

        wf.send_feedback()
        return 0

    wf.add_item('No workflow items were made', icon=ICON_WARNING)
    wf.send_feedback()
    return 0


if __name__ == "__main__":
    wf = Workflow3(help_url=HELP_URL)
    log = wf.logger
    sys.exit(wf.run(main))
