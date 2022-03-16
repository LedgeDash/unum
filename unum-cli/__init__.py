"""Unum command line interface

Unum command line for compiling, building and deploying applications.
"""

import json
import os
import sys
import subprocess
import time
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from cfn_tools import load_yaml, dump_yaml


def download_github_directory(repo, github_dir, local_dir):
    '''Download the directory `github_dir` from `repo` into a local directory
    `local_dir`.

    If `github_dir` contains other directories, this function recursively
    downloads all child directories.

    Side effects: adding files and directories to the directory named
    `local_dir`
    '''
    import base64
    directory_contents = repo.get_contents(github_dir)

    for f in directory_contents:
        local_file_name = "/".join(f.path.split('/')[1:])

        if f.type == 'dir':
            os.makedirs(f'{local_dir}/{local_file_name}')
            download_github_directory(repo, f.path, local_dir)
        else:
            with open(f'{local_dir}/{local_file_name}', "wb") as file_out:
                file_text = base64.b64decode(f.content)
                file_out.write(file_text)


def get_github_directory_list(repo):
    '''Return a list of strings that are the names of directories in a github
    repository `repo`.

    No side effects
    '''
    contents = repo.get_contents("")
    app_list = [f.path for f in contents if f.type =="dir" ]

    return app_list


def unum_compile(args):
    pass

def main():
    import shutil
    import base64
    
    import logging
    logger = logging.getLogger(__name__)

    try:
        import coloredlogs
        coloredlogs.install(level='DEBUG', logger=logger, datefmt = '%H:%M:%S', fmt='[%(asctime)s] %(message)s')
    except:
        logger.warning('`coloredlogs` do not exist. Revert to default logger.')
        pass

    import argparse

    parser = argparse.ArgumentParser(description='Unum CLI for creating, building and deploying Unum applications',
        usage = "unum-cli [options] <command>",
        epilog="To see help text for a specific command, use unum-cli <command> -h")

    subparsers = parser.add_subparsers(title='command', dest="command", required=True)

    # init command parser
    init_parser = subparsers.add_parser("init", description="initialize a Unum application")
    init_parser.add_argument('-n', '--name', required=True, help='application name')
    init_parser.add_argument('-t', '--template', action="store_true", help="initialize with an application template")

    # compile commmand parser
    compile_parser = subparsers.add_parser("compile", description="compile an application to Unum IR")
    compile_parser.add_argument('-t', '--workflow-type', required=False, help="workflow type")
    compile_parser.add_argument('-w', '--workflow-definition', required=False, help="workflow definition")
    compile_parser.add_argument('-u', '--unum-template', required=False, help="Unum template file")
    compile_parser.add_argument('-o', '--optimize', required=False, choices=['trim'], help="optimizations")

    # build command parser
    build_parser = subparsers.add_parser("build", description="build unum application in the current directory")
    build_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=False)
    build_parser.add_argument("-g", "--generate", help="Generate a platform template before buliding",
        required = False, action="store_true")
    build_parser.add_argument('-t', '--template',
        help="unum template file", required=False)
    build_parser.add_argument('-s', '--platform_template',
        help="platform template file", required=False)
    build_parser.add_argument("-c", "--clean", help="Remove build artifacts",
        required=False, action="store_true")

    # template command parser
    template_parser = subparsers.add_parser("template", description="generate platform specific template")
    template_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=False)
    template_parser.add_argument('-t', '--template',
        help="unum template file", required=False)
    template_parser.add_argument("-c", "--clean", help="Remove build artifacts",
        required=False, action="store_true")

    # deploy command parser
    deploy_parser = subparsers.add_parser("deploy", description="deploy unum application")
    deploy_parser.add_argument('-b', '--build', help="build before deploying. Note: does NOT generate new platform template as in unum-cli build -g",
        required=False, action="store_true")
    deploy_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=False)
    deploy_parser.add_argument('-t', '--template',
        help="unum template file", required=False)
    deploy_parser.add_argument('-s', '--platform_template',
        help="platform template file", required=False)

    args = parser.parse_args()

    if args.command =='init':

        try:
            from github import Github
            git = Github()

            unum_repo = git.get_repo("LedgeDash/unum")
            unum_runtime = unum_repo.get_contents("runtime")
        except:
            logger.error(f'Cannot access Unum runtime repo')
            sys.exit(1)

        app_name = args.name

        # create the {app_name} directory under the current directory
        try:
            os.makedirs(app_name)
        except FileExistsError:
            logger.error(f'`{app_name}` directory already exists')
            sys.exit(1)
        except Exception as e:
            logger.error(f'Failed to create `{app_name}` directory due to {e}')
            sys.exit(1)

        # create {app_name}/.unum directory, download the Unum runtime into
        # {app_name}/.unum/runtime from Unum's github repo
        os.makedirs(f'{app_name}/.unum')
        os.makedirs(f'{app_name}/.unum/runtime')

        try:
            for f in unum_runtime:
                logger.info(f'Downloading {f.path} into {app_name}/.unum/{f.path}')
                with open(f'{app_name}/.unum/{f.path}', "wb") as file_out:
                    file_text = base64.b64decode(f.content)
                    file_out.write(file_text)

        except Exception as e:
            logger.error(f'Failed to download Unum runtime')
            logger.error(e)
            shutil.rmtree(f'{app_name}')
            sys.exit(1)


        # download the application starter files into {app_name} directory
        # from the Unum appstore github repo
        try:
            unum_app_repo = git.get_repo("LedgeDash/unum-appstore")
        except:
            logger.error(f'Cannot access Unum appstore')
            logger.error(e)
            logger.warning(f'Continue without starter application files')
            logger.debug(f'{app_name} created')
            sys.exit(1)

        starter_app = "hello-world"
        if args.template:
            try:
                template_list = get_github_directory_list(unum_app_repo)

            except:
                logger.error(f'Failed to get the list of starter apps from Unum appstore')
                logger.error(e)
                logger.warning(f'Continue initialization with the default template')

            else:
                print('Which app template do you want to start with:')
                for i, t in enumerate(template_list):
                    print(f'    {i}. {t}')
                s = int(input('Type your number: '))

                try:
                    starter_app = template_list[s]
                except IndexError as e:
                    logger.error('Invalid number. Continue initialization with the default template')
                    starter_app = "hello-world"

        try:
            logger.info(f'Downloading starter template `{starter_app}`')
            download_github_directory(unum_app_repo, starter_app, app_name)

            logger.debug(f'Template `{starter_app}` downloaded')

            logger.debug(f'{app_name} created')

        except Exception as e:
            logger.error(f'Failed to download {starter_app}')
            logger.error(e)
            logger.warning(f'Continue without starter application files')
            logger.debug(f'{app_name} created')

    elif args.command == 'compile':
        '''Compile from frontend definition to Unum IR

        Supported frontends:
           1. AWS Step Functions (Amazon State Language)

        This function handles creating the related files inside .unum/ while the
        frontend module are purely functional
        '''

        # read from args.unum_template if some options are not specified on
        # the command line.
        if args.unum_template == None or args.workflow_type == None or args.workflow_definition == None:

            if args.unum_template == None:
                logger.warning('"UnumTemplate" not defined. Default to unum-template.yaml')
                args.unum_template = "unum-template.yaml"

            try:
                with open(args.unum_template) as tf:
                    app_template = load_yaml(tf.read())
                    # print(app_template)
            except Exception as e:
                logger.error(f'{args.unum_template} does not exist')
                exit(1)

            try:
                if args.workflow_definition == None:
                    args.workflow_definition = app_template['Globals']['WorkflowDefinition']
            except KeyError as e:
                logger.error('"WorkflowDefinition" not defined')
                exit(1)

            try:
                if args.workflow_type == None:
                    args.workflow_type = app_template['Globals']['WorkflowType']
            except KeyError as e:
                logger.error('"WorkflowType" not defined')
                exit(1)

        # print(args)

        # import the right frontend compiler based on args.workflow_type.
        # pass the content of workflow definition and unum-template as is to the frontend compiler
        if args.workflow_type == 'step-functions':
            from frontend import step_functions as fc

            try:
                with open(args.workflow_definition) as f:
                    state_machine = json.loads(f.read())
            except Exception as e:
                logger.error(f'Could not load Step Functions workflow definition: {args.workflow_definition}')
                raise e

            try:
                with open(args.unum_template) as f:
                    app_template = load_yaml(f.read())
            except Exception as e:
                logger.error(f'Could not load Unum template {args.unum_template}')
                raise e

            ir = fc.compile(state_machine, app_template, args.optimize)
            # print(ir)

            # Save generated IR into .unum/
            update_template = False
            for f in ir['unum IR']:
                if f['Name'] in app_template['Functions']:
                    function_dir = f".unum/{app_template['Functions'][f['Name']]['Properties']['CodeUri']}"
                else:
                    function_dir = f".unum/{f['Name']}"
                    update_template = True

                try:
                    # print(function_dir)
                    os.makedirs(function_dir)
                except FileExistsError as e:
                    pass
                except Exception as e:
                    logger.error(f'Could not create {function_dir}')

                try:
                    with open(os.path.join(function_dir, 'unum_config.json'), 'w') as cf:
                        cf.write(json.dumps(f, indent=4))
                except Exception as e:
                    raise e
            
            # if additional functions were generated, update the unum-template file
            if update_template:
                pass

            # save the template file after IR compilation into .unum/ always

            logger.debug('Unum IR generated from Step Functions')


        elif args.workflow_type == 'azure':
            pass
        else:
            raise IOError(f'Unknown WorkflowType: {args.workflow_type}')

    elif args.command == 'build':
        build(args)
    elif args.command == 'deploy':
        deploy(args)
    else:
        raise IOError(f'Unknown command: {args.command}')

    return


  
if __name__ == '__main__':
    rc = 1
    try:
        main()
        rc = 0
    except Exception as e:
        print('Error: %s' % e, file=sys.stderr)
    sys.exit(rc)