#!/usr/bin/python

'''
Java Web Plug-In Switcher for OS X

Uses the `jamfHelper` utility to display
notifications to the end user.
'''

import logging
import os
import plistlib
import subprocess

INTERNET_PLUGINS = '/Library/Internet Plug-Ins'
DISABLED_PLUGINS = os.path.join(INTERNET_PLUGINS, 'disabled')
JAVA_WEB_PLUGIN = os.path.join(INTERNET_PLUGINS, 'JavaAppletPlugin.plugin')
SYSTEM_JAVA = '/System/Library/Java/Support/Deploy.bundle/Contents/Resources/JavaPlugin2_NPAPI.plugin'

def get_console_user():
    '''Returns the currently logged-in user as
    a string, even if running as EUID root.'''
    if os.geteuid() == 0:
        console_user = subprocess.check_output(['/usr/bin/stat',
                                                '-f%Su',
                                                '/dev/console']).strip()
    else:
        import getpass
        console_user = getpass.getuser()

    return console_user

def determine_java_vendor(info_plist):
    '''Determine Java vendor. Takes the path to
    a Java Info.plist file and returns a string
    of the Java vendor's name.'''
    try:
        pl = plistlib.readPlist(info_plist)
        java_vendor = pl['CFBundleIdentifier'].split('.')[1]

    except KeyError:
        logger('CFBundleIdentifer does not exist in %s.' % info_plist)

    except IOError:
        logger('%s does not exist!' % info_plist)

    return java_vendor

def logger(msg):
    logging.basicConfig(filename='/Users/%s/Library/Logs/java_switcher.log' % get_console_user(),
                        format='%(asctime)s %(message)s',
                        level=logging.DEBUG)
    logging.debug(msg)

def prompt_user(old_java_vendor, new_java_vendor):
    '''Displays a dialog with jamfHelper about
    the Java Web Plug-In being switched.'''
    response = int(os.popen('"{jamf_helper}" -windowType utility -icon "{icon}" -title "{title}" -heading "{heading}" -description "{description}" -button1 "OK" -button2 "Cancel" -cancelButton "2"'.format(
        description='You are switching from %s\'s Java Plug-In to %s\'s Java Plug-In. Are you sure you want to continue? You\'ll need to restart your Web browser for the changes to take effect.' % (old_java_vendor, new_java_vendor),
        jamf_helper='/Library/Application Support/JAMF/bin/jamfHelper.app/Contents/MacOS/jamfHelper',
        heading='Switch Java Web Plug-In?',
        icon='/Library/Application Support/JAMF/bin/jamfHelper.app/Contents/Resources/Message.png',
        title='Java Web Plug-In Switcher'
    )).read())

    if response == 0:
        pass
    else:
        logger('%s cancelled the operation. Exiting now.' % get_console_user())
        exit(1)

def main():
    if os.path.exists(JAVA_WEB_PLUGIN):
        try:
            if not os.path.isdir(DISABLED_PLUGINS):
                os.makedirs(DISABLED_PLUGINS)

            real_path = os.path.realpath(JAVA_WEB_PLUGIN)
            java_info_plist = os.path.join(real_path, 'Contents/Info.plist')
            java_vendor = determine_java_vendor(java_info_plist)
            disabled_plugin = os.path.join(DISABLED_PLUGINS, 'JavaAppletPlugin.plugin')

            if java_vendor == 'oracle':
                prompt_user(java_vendor.capitalize(), 'Apple')
                os.rename(JAVA_WEB_PLUGIN, disabled_plugin)
                os.symlink(SYSTEM_JAVA, JAVA_WEB_PLUGIN)

                # Enable Java 6 Web Start
                javaws = '/usr/bin/javaws'
                os.symlink('/System/Library/Frameworks/JavaVM.framework/Commands/javaws',
                           javaws)

            elif java_vendor == 'apple':
                prompt_user(java_vendor.capitalize(), 'Oracle')

                if os.path.isdir(disabled_plugin):
                    os.unlink(JAVA_WEB_PLUGIN)
                    os.rename(disabled_plugin, JAVA_WEB_PLUGIN)

                    # Enable Java 7 Web Start
                    javaws = '/usr/bin/javaws'
                    os.symlink('/System/Library/Frameworks/JavaVM.framework/Versions/Current/Commands/javaws',
                               javaws)

                else:
                    logger('Unable to switch Java Web plugin version. '
                           'Could not locate %s.' % disabled_plugin)

            else:
                logger('Unknown Java vendor: %s.' % java_vendor)

        except OSError, e:
            logger('Error: %s' % e)

    else:
        raise Exception('Unable to locate JavaAppletPlugin.plugin'
                        ' in %s.' % INTERNET_PLUGINS)

if __name__ == '__main__':
    main()
