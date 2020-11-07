# How to Sign and Notarize a Command Line Tool Manually
Apple requires that all distributed binaries are signed and notarized using a paid Apple Developer account. This can be done using commandline tools for binaries created with tools such as PyInstaller, or compiled using gcc.

## Setup
If you already have a developer account with `Developer ID Application` and `Developer ID Installer` certificates configured in XCode, skip this step

* Create a developer account with Apple
  - https://developer.apple.com and shell out $99 for a developer account. *Theives*
* Download and install X-Code from the Apple App Store 
* Open and run X-Code app and install whatever extras it requires
* Open the preferences pane (cmd+,) and choose *Accounts*(
  - click the `+` in the lower left corner
  - choose `Apple ID`
  - enter your apple ID and password
  - Previously created keys can be downloaded and installed from https://developer.apple.com
* Select the developer account you wish to use
* Choose *Manage Certificates...*
* Click the `+` in the lower left corner and choose *Developer ID Application*
* Click the `+` in the lower left corner and choose *Developer ID Installer*

## Create an App-Specific password for altool to use
* [Instructions from Apple](https://support.apple.com/en-us/HT204397)
* Open `KeyChain Access`
* Create a "New Password Item"
  - Keychain Item Name: Developer-altool
  - Account Name: your developer account email
  - Password: the application-specific password you just created

## Create an executable binary with Pyinstaller or other tool
**NB!** Additional args such as `--add-data` may be needed to build a functional binary
* Create a onefile binary
  - `pyinstaller --onefile myapp.py`
  
## Sign the executable
* Add the entitements.plist to the directory (see below)
* List the available keys and locate a Developer ID Application certificate:
  - `security find-identity -p basic -v`
  ```
  1) ABC123 "Apple Development: aaronciuffonl@gmail.com ()"
  2) XYZ234 "Developer ID Installer: Aaron Ciuffo ()"
  3) QRS333 "Developer ID Application: Aaron Ciuffo ()"
  4) LMN343 "Developer ID Application: Aaron Ciuffo ()"
  5) ZPQ234 "Apple Development: aaron.ciuffo@gmail.com ()"
  6) ASD234 "Developer ID Application: Aaron Ciuffo ()"
  7) 01010A "Developer ID Application: Aaron Ciuffo ()"
     7 valid identities found
  ```
* `codesign --deep --force --options=runtime --entitlements ./entitlements.plist --sign "HASH_OF_DEVELOPER_ID APPLICATION" --timestamp ./dist/foo.app`

## Package as a pkg for installation
* Create a temp directory to build the package:
  - `mkdir /tmp/myapp`
* Use ditto to build the pkg installer structure
  - `ditto /path/to/myapp /tmp/myapp/path/to/install/location`
  - repeat for all files that should be packaged
* build the pkackage 
 - `productbuild --identifier "com.your.pkgname.pkg" --sign "HASH_OF_INSTALLER_ID" --timestamp --root /tmp/myapp / myapp.pkg`

## Notarize
* `xcrun altool --notarize-app --primary-bundle-id "com.foobar.fooapp" --username="developer@foo.com" --password "@keychain:Developer-altool" --file ./myapp.pkg`
* Check email for successful notarization
  - Alternatively check status using:
    * `xcrun altool --notarization-history 0 -u "developer@***" -p "@keychain:Developer-altool"`
* If notarization fails use the following to review a detailed log:
```
  xcrun altool --notarization-info "Your-Request-UUID" \
             --username "username@example.com" \                                    
             --password "@keychain:Developer-altool"   
```

## Staple notarization to pkg
* add the notariztaion to the pkg
  - `xcrun stapler staple ghostscript64.pkg`


# Useful Resources
* [Norarize a Commandline utility](https://scriptingosx.com/2019/09/notarize-a-command-line-tool/)
  - This blog details setting up:
    - a developer profile & certificates
    - one time passwords
    - creating keychain entries to allow the `-p "@keychain:Key"` switch to work
    - Signing and Notarizing
    - Satpling
* [Adding an `entitlements.plist` to the signing process](https://github.com/pyinstaller/pyinstaller/issues/4629#issuecomment-574375331) 
  - ensure that embedded python libraries can be access appropriately
* [Signing and Notarizing tools compiled outside of XCode](https://developer.apple.com/forums/thread/130379)
  - covers:
    - signing
    - packaging
    - notarizing
    - stapling



# Alternative workflows that may have issues:
## Create a bundled app with pyinstaller
* Only ".app" bundles appear to work using this procedure
  - `pyinstaller --windowed --onefile foo.py`
  - edit the spec file `app = BUNDLE` section to include a bundle_identifier
  ```
  app = BUNDLE(exe,
             name='helloworld.app',
             icon=None,
             bundle_identifier='com.txoof.helloworld'
             )
  ```
 * **NOTE!** Appbundles will not execute properly -- they must be run by execuing the `bundle.app/Contents/MacOS/myapp` 

## package as a dmg
**NB! This may not work for single file executables -- use the PKG method above**
* Create a `.dmg`:
  - clean any uneeded files out of `./dist`; only the .app should remain
  - `hdiutil create ./myapp.dmg -ov -volname "MyApp" -fs HFS+ -srcfolder "./dist"`
* Shrink and make read-only:
  - `$hdiutil convert ./myapp.dmg -format UDZO -o myapp.dmg`
