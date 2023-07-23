#!/usr/bin/env python3
# coding: utf-8






version = '0.3'

import logging
import configparser
import argparse
# from distutils import util
import subprocess
import shlex
import tempfile
from pathlib import Path
from time import sleep
import sys
from shutil import rmtree






def strtobool (val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else. 
    
    courtesy of 
    https://github.com/python/cpython/blob/main/Lib/distutils/util.py
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))






def get_config(args, default_config=None, filename='pycodesign.ini'):
    file = args.config
    config = configparser.ConfigParser()
    
    if file:
        print (f'using configuration file: {file}')
        config.read(file)
    elif default_config and args.new_config:
        config.read_dict(default_config)
        print(f'writing default config file: {filename}')
        try:
            with open(filename, 'w') as blank_config:
                config.write(blank_config)
        except OSError as e:
            print(f'could not create {filename} due to error: {e}')
        return {}
    else:
        return {}

    return {s:dict(config.items(s)) for s in config.sections()}






def get_args():

    saved =[]
    for k in sys.argv:
        saved.append(k)

    if '-f' in saved:
        logging.info('working in interactive jupyter environ')
        try:
            sys.argv = sys.argv[:sys.argv.index('-f')]
        except ValueError as e:
            pass
    
    
    
    parser = argparse.ArgumentParser(description='PyCodeSign -- Code Signing and Notarization Assistant')
    
    parser.add_argument('-v', '--verbose', action='count', default=1)
    
    parser.add_argument('-V', '--version', dest='version',
                       action='store_true', default=False)
    
    parser.add_argument('-N', '--new', dest='new_config', 
                        action='store_true', default=False,
                       help='create a new sample configuration with name "pycodesign.ini" in current directory')
    
    parser.add_argument('config', nargs='?', type=str, default=None,
                       help='configuration file to use when codesigning',
                       metavar='<PYCODESIGN_CONFIG.INI>')
    
    parser.add_argument('-s', '--sign', dest='sign_only',
                       action='store_true', default=None,
                       help='sign the executables, but take no further action (can be combined with -p, -n, -t)')
    
    parser.add_argument('-p', '--package', dest='package_only',
                       action='store_true', default=None,
                       help='package the executables, but take no further action (can be combined with -s, -n, -t)')
    
    parser.add_argument('-P', '--package_debug', dest='package_debug', 
                        action='store_true', default=None,
                        help='package but leave temporary files in place for debugging')
    
    parser.add_argument('-n', '--notarize', dest='notarize_only',
                       action='store_true', default=None,
                       help='notarize the package, but take no further action (can be combined with -s, -p, -t)')

    parser.add_argument('-t', '--staple', dest='staple_only',
                       action='store_true', default=None,
                       help='stape the notarization to the the package, but take no further action (can be combined with -s, -p, -n)')
    
    #parser.add_argument('-T', '--notarize_timer', type=int, default=60,
    #                   metavar="<INTEGER>",
    #                   help='base time in seconds to wait between checking notarization status with apple (default 60)')
    
    #parser.add_argument('-C', '--num_checks', type=int, default=5, 
    #                   metavar="<INTEGER>",
    #                   help='number of times to check notarization status with apple (default 5) -- each check doubles notarize_timer')

    parser.add_argument('-O', '--pkg_version', type=str, 
                        default=None, 
                        metavar="<VERSION STRING>",
                        help='overide the version number in the .ini file and use supplied version number.')    
    
#     known_args, unknown_args = parser.parse_known_args()
    args = parser.parse_args()
#     return(known_args, unknown_args)
    return args






def validate_config(config, expected_keys):
    missing = {}
    for section, keys in expected_keys.items():
        if not section in config.keys():
            missing[section] = expected_keys[section]
            continue
        for key in keys:
            if not key in config[section].keys():
                if not section in missing:
                    missing[section] = {}
                missing[section][key] = keys[key]
                
    if missing:
        print('Config file is missing values:')
        for section, values in missing.items():
            print(f'[{section}]')
            for k, v in values.items():
                print(f'\t{k}: {v}')
                    
    return missing






def run_command(command_list):
    cmd = subprocess.Popen(shlex.split(' '.join(command_list)), 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
    stderr, stdout = cmd.communicate()
    return cmd.returncode, stderr, stdout






def sign(config):
    
    try:
        entitlements = strtobool(config['package_details']['entitlements'])
    except (AttributeError, ValueError):
        entitlements = config['package_details']['entitlements']
    
    if (not entitlements) or (entitlements == 'None'):
        entitlements = None
        
    config['package_details']['entitlements'] = entitlements

    args = {
        'command': 'codesign',
        'args': '--deep --force --timestamp --options=runtime',
        'entitlements': f'--entitlements {config["package_details"]["entitlements"]}' if config["package_details"]["entitlements"] else None,
        'signature': f'--sign {config["identification"]["application_id"]}',
        'files': ' '.join(config['package_details']['file_list'])
    }
        
    final_list = [i if i is not None else '' for k, i in args.items()]
    logging.debug('running command:')
    logging.debug(' '.join(final_list))

    print(f'signing files: {args["files"]}')
    
    return_code, stdout, stderr = run_command(final_list)
    logging.debug(f'return code: {return_code}')
    logging.debug(f'stdout: {stdout}')
    logging.debug(f'stderr: {stderr}')
    
    return return_code, stdout, stderr
    






def package(config, package_debug=False):
    pkg_temp = Path(tempfile.mkdtemp()).resolve()
    
    install_path = Path(config['package_details']['installation_path']).resolve()
    
    temp_path = Path(f'{pkg_temp}/{install_path}')
    
#     return pkg_temp, install_path
    
    logging.debug(f'pkg_temp: {pkg_temp}')
    logging.debug(f'install_path: {install_path}')
    logging.debug(f'temp_path: {temp_path}')
    
    for file in config['package_details']['file_list']:
        my_file = Path(file).resolve()
        file_name = my_file.name
        
        command = f'ditto {my_file} {temp_path/file_name}'
        logging.debug(f'running command: {command}')
        r, o, e = run_command(shlex.split(command))
        if not process_return(r, o, e):
            logging.warning('could not ditto file into temp path')
            if not package_debug:
                rmtree(pkg_temp)
            return r, o, e
    
    args = {
        'command': 'productbuild',
        'identifier': f'--identifier {config["package_details"]["bundle_id"]}.pkg',
        'signature': f'--sign {config["identification"]["installer_id"]}',
        'args': '--timestamp',
        'version': f'--version {config["package_details"]["version"]}',
        'root': f'--root {pkg_temp} / ./{config["package_details"]["package_name"]}.pkg'
        
    }
    
    print(f'packaging {config["package_details"]["package_name"]}.pkg')
    final_list = [i if i is not None else '' for k, i in args.items()]
    
    logging.debug('running command:')
    logging.debug(' '.join(final_list))    
    
    r, o, e = run_command(final_list)
    
    
#     logging.debug(f'return code: {return_code}')
#     logging.debug(f'stdout: {stdout}')
#     logging.debug(f'stderr: {stderr}')
    
    if not package_debug:
        rmtree(pkg_temp, ignore_errors=True)
    else:
        print(f'Package debugging active:')
        print(f'Temp files: {pkg_temp}')
    return r, o, e       
        
    






# def package(config, package_debug=False):
#     pkg_temp = tempfile.mkdtemp()
#     pkg_temp_path = Path(pkg_temp).resolve()
#     install_path = Path(config['package_details']['installation_path']).resolve()
#     logging.debug(f'using pkg_temp_path: {pkg_temp_path}')
#     logging.debug(f'install_path: {install_path}')
#     for file in config['package_details']['file_list']:
#         my_file = Path(file).resolve()
#         file_name = my_file.name
#         logging.debug(f'copying file: {file}')
#         command = f'ditto {file} {pkg_temp_path/install_path/file_name}'
#         logging.debug(f'run command:\n {command}')
#         return_code, stderr, stdout = run_command(shlex.split(command))
#         if return_code > 0:
#             pkg_temp.cleanup()
#             return return_code, stderr, stdout
    
#     args = {
#         'command': 'productbuild',
#         'identifier': f'--identifier {config["package_details"]["bundle_id"]}.pkg',
#         'signature': f'--sign {config["identification"]["installer_id"]}',
#         'args': '--timestamp',
#         'version': f'--version {config["package_details"]["version"]}',
#         'root': f'--root {pkg_temp_path} / ./{config["package_details"]["package_name"]}.pkg'
        
#     }
    
#     print(f'packaging {config["package_details"]["package_name"]}.pkg')
#     final_list = [i if i is not None else '' for k, i in args.items()]
    
#     logging.debug('running command:')
#     logging.debug(' '.join(final_list))    
    
#     return_code, stdout, stderr = run_command(final_list)
    
#     logging.debug(f'return code: {return_code}')
#     logging.debug(f'stdout: {stdout}')
#     logging.debug(f'stderr: {stderr}')
    
#     if not package_debug:
#         rmtree(pkg_temp_path, ignore_errors=True)
#     else:
#         print(f'Package debugging active:')
#         print(f'Temp files: {pkg_temp_path}')
#     return return_code, stdout, stderr






def notarize(config):
    notarize_args = {
        'command': 'xcrun notarytool',
        'args': 'submit --wait',
        #'bundle_id': f'--primary-bundle-id {config["package_details"]["bundle_id"]}',
        #'username': f'--username={config["identification"]["apple_id"]}',
        #'password': f'--password {config["identification"]["password"]}',
        'keychain-profile': f'--keychain-profile {config["identification"]["keychain-profile"]}',
        'file': f'{config["package_details"]["package_name"]}.pkg'
    }
    
 
    
    final_list = [i for k, i, in notarize_args.items()]
    logging.debug('running command:')
    logging.debug(' '.join(final_list))    
    
    return_code, stdout, stderr = run_command(final_list)
    
    logging.debug(f'return code: {return_code}')
    logging.debug(f'stdout: {stdout}')
    logging.debug(f'stderr: {stderr}')           
   
    return return_code, stdout, stderr






def check_notarization(stdout, config):
    notarize_max_check = config['main']['notrarize_max_check']
    notarize_check = 0
    notarized = False
    
    
    uuids = []
    for line in str(stdout, 'utf-8').splitlines():
        if 'requestuuid' in line.lower():
            my_id = line.split('=')
            uuids.append(my_id[1].strip())    
    logging.debug('uuids found: ')
    logging.debug(uuids)

    check_args = {
        'command': 'xcrun altool',
        'info': f'--notarization-info {uuids[0]}',
        'username': f'--username {config["identification"]["apple_id"]}',
        'password': f'--password {config["identification"]["password"]}'
    }
    final_list = [i for k, i in check_args.items()]    
    
    
    while not notarized:
        status = {}
        success = None
        print('checking notarization status')
        notarize_check += 1
        print(f'check: {notarize_check} of {notarize_max_check}')

        logging.debug('running command:')
        logging.debug(' '.join(final_list))    

        return_code, stdout, stderr = run_command(final_list)

        logging.debug(f'return code: {return_code}')
        logging.debug(f'stdout: {stdout}')
        logging.debug(f'stderr: {stderr}')

        if stdout:
            lines = str(stdout, 'utf-8').splitlines()

            for l in lines:
                if 'status' in l.lower():
                    vals = l.split(':')
                    status[vals[0].strip().lower()] = vals[1].strip()
                        
            try:
                if status['status'] == 'success':
                    success = True
                if status['status'] == 'invalid':
                    success = False
            except KeyError as e:
                logging.debug(f'inconclusive notarization status data returned: {status}')


            logging.debug('status: ')
            logging.debug(status)

            if success is True:
                logging.debug('successfully notarized')
                notarized=True
            elif success is False:
                logging.debug('notarization failed')
                break
            else:
                print(f'notarization not complete: {status}')
                if notarize_check >= notarize_max_check-1:
                    print('notarization failed')
                    break
                sleep_timer = config['main']['notarize_timer']*notarize_check
                print(f'sleeping for {sleep_timer} seconds')
                logging.debug(f'notarization not complete; sleeping for {sleep_timer}')
                sleep(sleep_timer)
    return notarized






def staple(config):
    args = {
        'command': 'xcrun stapler',
        'args': 'staple',
        'package': f'{config["package_details"]["package_name"]}.pkg'
    }
    
    final_list = [i for k, i in args.items()]
    
    logging.debug('running command:')
    logging.debug(' '.join(final_list))    

    
    return_code, stdout, stderr = run_command(final_list)

    logging.debug(f'return code: {return_code}')
    logging.debug(f'stdout: {stdout}')
    logging.debug(f'stderr: {stderr}')

    
    return return_code, stdout, stderr






def process_return(return_value, stdout, stderr):
    def byte_print(byte_str):
        if isinstance(byte_str, bytes):
            for line in str(byte_str, 'utf-8').splitlines():
                print(line)
        else:
            print(byte_str)
            

    if len(stdout) > 0:
        print('OUTPUT: ')
        byte_print(stdout)
    if len(stderr) > 0:
        print('ERRORS:')
        byte_print(stderr)
        
    if return_value > 0:
        retval = False
        print('failed\n\n')
    else:
        retval = True
        print('success\n\n')

    return retval
    






## Testing code
#sys.argv = sys.argv[:1]

# sys.argv.extend(['-O', '9.9.9'])
# sys.argv.append('insert_files_codesign.ini')


# expected_config_keys = {
#         'identification': {
#             'application_id': 'Unique Substring of Developer ID Application Cert',
#             'installer_id': 'Unique Substring of Developer ID Installer Cert',
#             'apple_id': 'developer@domain.com',
#             'password': '@keychain:App-Specific-Password-Name-In-Keychain',
#         },
#         'package_details': {
#             'package_name': 'nameofpackage',
#             'bundle_id': 'com.developer.packagename',
#             'file_list': "include_file1, include_file2",
#             'installation_path': '/Applications/',
#             'entitlements': 'None',
#             'version': '0.0.0'
#         }
#     }

# logging.root.setLevel("DEBUG")
# args = get_args()
# config = get_config(args=args, default_config=expected_config_keys)

# config.update({'main': {
#         'notarize_timer': args.notarize_timer,
#         'notrarize_max_check': args.num_checks,
#         'new_config': args.new_config}
#                   })

# if args.pkg_version:
#     config['package_details']['version'] = args.pkg_version

# validate_config(config, expected_config_keys)






def main():
    logger = logging.getLogger(__name__)

    expected_config_keys = {
        'identification': {
            'application_id': 'Unique Substring of Developer ID Application Cert',
            'installer_id': 'Unique Substring of Developer ID Installer Cert',
            'keychain-profile': 'Name-of-stored-keychain-profile'
        },
        'package_details': {
            'package_name': 'nameofpackage',
            'bundle_id': 'com.developer.packagename',
            'file_list': "include_file1, include_file2",
            'installation_path': '/Applications/',
            'entitlements': 'None',
            'version': '0.0.0'
        }
    }
    run_all = True
    
#     notarize_timer = 60
#     notrarize_max_check = 5
    halt = False
    
    args = get_args()

    verbose = 50 - (args.verbose*10) 
    if verbose < 10:
        verbose = 10
    logging.root.setLevel(verbose)
    
    if args.version:
        print(f'{sys.argv[0]} V{version}')
        return
    
    config = get_config(args=args, default_config=expected_config_keys)
    if not config:
        print('no configuration file provided')
        print(f'try:\n$ {sys.argv[0]} -h')
        return
    
    #config.update({'main': {
    #    'notarize_timer': args.notarize_timer,
    #    'notrarize_max_check': args.num_checks,
    #    'new_config': args.new_config}
    #              })
    
    if args.pkg_version:
        config['package_details']['version'] = args.pkg_version
    
    logging.debug('using config:')
    logging.debug(config)
    
    if validate_config(config, expected_config_keys):
        print('exiting')
        return
        
    # split the file list into an actual list
    try:
        file_list = config['package_details']['file_list'].split(',')
        config['package_details']['file_list'] = file_list
    except KeyError:
        pass
    
    
    check_args =[args.notarize_only,
                 args.package_only,
                 args.sign_only,
                 args.staple_only,
                 args.package_debug ]
        
    for each in check_args:
        if each:
            run_all = False
    
#     if args.notarize_only or args.package_only or args.sign_only or args.staple_only or args.package_debug:
#         run_all = False
        
    if args.sign_only or run_all:
        print('signing...')
        r, o, e = sign(config)
        process_return(r, o, e)
        if r > 0:
            halt = True
        
    if args.package_only or args.package_debug or run_all and not halt:
        print('packaging...')
        r, o, e = package(config, args.package_debug)
        process_return(r, o, e)
        if r > 0:
            halt = True
    
    if args.notarize_only or run_all and not halt:
        print('notarizing...')
        r, o, e = notarize(config)
        process_return(r, o, e)
        if r == 0:
            print('notaization process at Apple completed')
        else:
            print('notariztion process did not complete or was inconclusive')
            print(f'check manually with: ')
            print(f'xcrun notarytool history --keychain-profile {config["identification"]["keychain-profile"]}')
            halt = True
    
    if args.staple_only or run_all and not halt:
        print('stapling...')
        r, o, e = staple(config)
        process_return(r, o, e)
        if r > 0:
            halt = True

    
    return config        
    






if __name__ == '__main__':
    c = main()









