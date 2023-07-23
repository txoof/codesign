# codesign
Python3 script for signing, packaging, notarizing and stapling Apple command line binaries using `notarytool`. This script only requires Python3 and uses only standard libraries.

This script is specifically targeted at codesigning, notarizing, creating `.pkg` files and stapling the notarization onto **commandline tools** written and compiled outside of Apple Xcode. This was created specifically for notarizing and signing python tools created with PyInstaller. 

As of MacOS Catalina, all distributed binaries must be signed and notarized using an apple developer account. This account costs $99 per year. *Theives*.

Apple's documentation for this process is ***ABSOLUTELY*** terrible. For a guide to doing this manually see [Signing_and_Notarizing_HOWTO](https://github.com/txoof/codesign/blob/main/Signing_and_Notarizing_HOWTO.md)

## NEW in v0.3
As of v0.3, this script uses `notarytool` instead of `altool`. `altool` is being deprecated by Apple and will no longer work after November 2023.

If you are updating from a previous version of `pycodesign`, you will need to create a new keychain profile and update your .ini file.

## Requirements
See [this guide](https://github.com/txoof/codesign/blob/main/Signing_and_Notarizing_HOWTO.md) for help in obtaining these requirements.
* Paid apple developer's account
* Developer ID Application certificate
* Developer ID Installer certificate

## Quick Start
1) Download [pycodesign](https://github.com/txoof/codesign/raw/main/pycodesign.tgz)
2) Unpack and place somehwere in your `$PATH`
3) Create a keychain profile for notarization using `xcrun notarytool store-credentials YOUR_PROFILE_NAME --apple-id YOUR_APPLE_ID --team-id YOUR_TEAM_ID`
    * You will be prompted for your app-specific password.
    * For more information, see [this article](https://developer.apple.com/documentation/technotes/tn3147-migrating-to-the-latest-notarization-tool#Save-credentials-in-the-keychain).
4) Enter directory containing the binaries you wish to sign
5) run: `pycodesign.py -N` to create a template configuration file
6) edit the configuration file (see [below](#configFile) for more details
7) run `pycodesign.py yourconfig.ini` to begin the signing and notarization process
8) Enter your username and password as needed to unlock your keychain
9) Once the package is submitted to Apple, `pycodesign` will wait to see if the process is complete. 
   * Check your email or manually check the notarization status using `xcrun notarytool history --keychain_profile YOUR_PROFILE_NAME`
10) rejoyce in your signed .pkg file

## Manual
Basic Usage:
`$ codesign.py my_config.ini`

```
usage: pycodesign.py [-h] [-v] [-V] [-N] [-s] [-p] [-n] [-t] [-T <INTEGER>]
                     [-C <INTEGER>]
                     [<PYCODESIGN_CONFIG.INI>]

PyCodeSign -- Code Signing and Notarization Assistant

positional arguments:
  <PYCODESIGN_CONFIG.INI>
                        configuration file to use when codesigning

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose
  -V, --version
  -N, --new             create a new sample configuration with name
                        "pycodesign.ini" in current directory
  -s, --sign            sign the executables, but take no further action
                        (can be combined with -p, -n, -t)
  -p, --package         package the executables, but take no further action
                        (can be combined with -s, -n, -t)
  -n, --notarize        notarize the package, but take no further action
                        (can be combined with -s, -p, -t)
  -t, --staple          stape the notarization to the the package, but take
                        no further action (can be combined with -s, -p, -n)
  -O <VERSION STRING>, --pkg_version <VERSION STRING>
                        overide the version number in the .ini file and use 
                        supplied version number.
```

## Codesign Configuration File Structure
<a name="configFile"> </a>
For help creating certificates and app-specific passwords see: [Signing_and_Notarizing_HOWTO](https://github.com/txoof/codesign/blob/main/Signing_and_Notarizing_HOWTO.md)

Use `security find-identity -p basic -v` to view Certificate strings

Use `curl -LJO https://raw.githubusercontent.com/txoof/codesign/main/entitlements.plist` to quickly download the a sample `entitlements.plist`
```
# All [sections] and values are required unless otherwise noted
# whitespace and comments are ignored

# identification details
[identification] 
# unique substring from the Developer ID Application certificate
# such as the HASH or the short team has
application_id = Unique Substring of Developer ID Application Cert
# unique substring from the Developer ID Installer certificate
# such as the HASH or the short team has
installer_id = Unique Substring of Developer ID Installer Cert
# Keychain profile with credentials for app notarization
keychain-profile = Name-of-stored-keychain-profile

[package_details]
# name of finished package such as "pdfsplitter" or "whizbangtool"
package_name = nameofpackage
# unique bundle identifier -- this is typically in reverse DNS
# format such as com.yoursite.pdfsplitter or com.yoursite.whizbangtool
bundle_id = com.developer.packagename
# paths to files to include in the package specified as comma separated list
file_list = include_file1, include_file2
# path where the Apple .pkg installer will install the tools
# such as /Applications or /usr/local/bin
installation_path = /Applications/
# entitlements XML -- binaries with embedded libraries such as those use 'None' to skip
# produced by PyInstlaler require a special entitlements.plist
# see the a sample here https://github.com/txoof/codesign/blob/main/entitlements_sample.plist
entitlements = None
# your version number
version = 0.0.0
```
