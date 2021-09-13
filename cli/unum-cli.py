#!/usr/bin/env python
import json, os, sys, subprocess, time
import argparse
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from cfn_tools import load_yaml, dump_yaml


def generate_sam_template(unum_template):
    ''' Given an unum template, return an AWS SAM template as a python dict

        @param unum_template python dict

        @return sam_template python dict
    '''

    # boilerplate SAM template fields
    sam_template = {"AWSTemplateFormatVersion": '2010-09-09',
                    "Transform": "AWS::Serverless-2016-10-31"}

    # save workflow-wide configurations as environment variables.
    # Globals:
    #   Function:
    #       Environment:
    #           Variables:
    # These variables will be accessible by Lambda code as environment variables.
    sam_template["Globals"] = {
            "Function": {
                "Environment": {
                    "Variables":{
                        "UNUM_INTERMEDIARY_DATASTORE_TYPE": unum_template["Globals"]["UnumIntermediaryDataStoreType"],
                        "UNUM_INTERMEDIARY_DATASTORE_NAME": unum_template["Globals"]["UnumIntermediaryDataStoreName"],
                        "CHECKPOINT":unum_template["Globals"]["Checkpoint"]
                    }
                }
            }
        }
    # Set all Lambda timeouts to 900 sec
    sam_template["Globals"]["Function"]["Timeout"] = 900

    # For each unum function, create a AWS::Serverless::Function resource in
    # the SAM template under the "Resources" field.
    # All unum functions "Handler" is unum.lambda_handler
    # Copy over "CodeUri", "Runtime"
    # Add 
    #   + "AmazonDynamoDBFullAccess"
    #   + "AmazonS3FullAccess"
    #   + "AWSLambdaRole"
    #   + "AWSLambdaBasicExecutionRole"
    # if any is not listed already in the unum template
    unum_function_needed_policies = ["AmazonDynamoDBFullAccess","AmazonS3FullAccess","AWSLambdaRole","AWSLambdaBasicExecutionRole"]
    sam_template["Resources"]={}
    sam_template["Outputs"] = {}

    for f in unum_template["Functions"]:
        unum_function_policies = []
        if "Policies" in unum_template["Functions"][f]["Properties"]:
            unum_function_policies = unum_template["Functions"][f]["Properties"]["Policies"]

        sam_template["Resources"][f'{f}Function'] = {
                "Type":"AWS::Serverless::Function",
                "Properties": {
                    "Handler":"unum.lambda_handler",
                    "Runtime": unum_template["Functions"][f]["Properties"]["Runtime"],
                    "CodeUri": unum_template["Functions"][f]["Properties"]["CodeUri"],
                    "Policies": list(set(unum_function_needed_policies) | set(unum_function_policies))
                }
            }
        arn = f"!GetAtt {f}Function.Arn"
        sam_template["Outputs"][f'{f}Function'] = {"Value": f"!GetAtt {f}Function.Arn"}

    return sam_template

def sam_build_clean(args):

    if args.platform_template == None:
        # default AWS SAM template filename to template.yaml
        args.platform_template = 'template.yaml'

    try:
        with open(args.platform_template) as f:
            platform_template = load_yaml(f.read())
    except Exception as e:
        print(f'\033[31m\n Build Clean Failed!\n\n Make sure a platform template file exists\033[0m')
        raise e

    # remove unum runtime files from each function's directory
    runtime_file_basename = os.listdir("common")
    for f in platform_template["Resources"]:
        app_dir = platform_template["Resources"][f]["Properties"]["CodeUri"]
        runtime_files = [app_dir+e for e in runtime_file_basename]
        try:
            subprocess.run(['rm', '-f']+runtime_files, check=True)
        except Exception as e:
            raise e

    # remove the .aws-sam build directory
    try:
        ret = subprocess.run(["rm", "-rf", ".aws-sam"], check = True, capture_output=True)
    except Exception as e:
        raise e

    return

def sam_build(platform_template, args):

    if args.clean:
        sam_build_clean(platform_template)
        return

    # copy files from common to each functions directory
    for f in platform_template["Resources"]:
        app_dir = platform_template["Resources"][f]["Properties"]["CodeUri"]
        subprocess.run(f'cp common/* {app_dir}', shell=True, check=True)

    try:
        ret = subprocess.run(["sam", "build"], capture_output=True, check= True)
        print(f'\033[32mBuild Succeeded\033[0m\n')
        print(f'\033[33mBuilt Artifacts  : .aws-sam/build\033[0m')
        print(f'\033[33mBuilt Template   : .aws-sam/build/template.yaml\033[0m\n')
        print(f'\033[33mCommands you can use next\n=========================\033[0m')
        print(f'\033[33m[*] Deploy: unum-cli deploy\033[0m\n')
    except Exception as e:
        print(f'\033[31m \n Build Failed!\n\n AWS SAM failed to build due to:')
        raise e
    

def build(args):

    if args.clean:
        if args.platform == 'aws':
            sam_build_clean(args)
        elif args.platform == None:
            sam_build_clean(args)
        elif args.platform == 'azure':
            pass
        else:
            pass
        return

    if args.generate:
        print("\033[33mGenerating platform template...........\033[0m\n")
        template(args)

    if args.platform == None:
        print(f'No target platform specified.\nDefault to \033[33m\033[1mAWS\033[0m.')
        print(f'If AWS is not the desirable target, specify a target platform with -p or --platform.\nSee unum-cli build -h for details.\n')
        args.platform='aws'

    if args.platform == 'aws':
        # Default to AWS
        if args.platform_template == None:
            print(f'No platform template file specified.\nDefault to\033[33m\033[1m template.yaml \033[0m')
            print(f'You can specify a platform template file with -s or --platform_template.\nSee unum-cli build -h for details.\n')
            args.platform_template = "template.yaml"

        try:
            with open(args.platform_template) as f:
                platform_template = load_yaml(f.read())
        except Exception as e:
            print(f'\033[31m \n Build Failed!\n\n Make sure the platform template file exists\033[0m')
            print(f'\033[31m You can specify a platform template file with -s/--platform_template\033[0m')
            print(f'\033[31m Or generate a platform template from your unum template with "unum-cli template" or "unum-cli build -g"\033[0m')
            print(f'\033[31m See unum-cli -h for more details\033[0m\n')
            raise e

        sam_build(platform_template, args)
    else:
        pass

def deploy_sam_first():
    # Deploy the functions as is, get each function's arn, update each
    # function's unum_config.json with the arn, store function name to arn
    # mapping in function-arn.yaml

    # First deployment. Deploy functions as is
    with open("unum-template.yaml") as f:
        app_template = yaml.load(f.read(),Loader=Loader)

    app_name = app_template["Globals"]["ApplicationName"]

    try:
        ret = subprocess.run(["sam", "deploy",
                          "--stack-name", app_name,
                          "--region", "us-west-1",
                          "--no-fail-on-empty-changeset",
                          "--no-confirm-changeset",
                          "--resolve-s3",
                          "--capabilities",
                          "CAPABILITY_IAM"],
                          capture_output=True)
    except Exception as e:
        raise e

    # grep for the functions' arn
    stdout = ret.stdout.decode("utf-8")
    print(stdout)
    print(ret.stderr.decode("utf-8"))
    try:
        deploy_output = stdout.split("Outputs")[1]
    except:
        raise IOError(f'SAM stack with the same name already exists')
    
    deploy_output = deploy_output.split('-------------------------------------------------------------------------------------------------')[1]
    
    deploy_output = deploy_output.split()
    function_to_arn_mapping = {}

    i = 0
    while True:
        while deploy_output[i] != "Key":
            i = i+1

        function_name = deploy_output[i+1].replace("Function","")

        while deploy_output[i] != "Value":
            i = i+1
        function_arn = deploy_output[i+1] + deploy_output[i+2]
        function_to_arn_mapping[function_name] = function_arn

        if len(app_template["Functions"]) == len(function_to_arn_mapping.keys()):
            break

    # store function name to arn mapping in function-arn.yaml
    with open("function-arn.yaml", 'w') as f:
        d = yaml.dump(function_to_arn_mapping, Dumper=Dumper)
        f.write(d)

    print(f'function-arn.yaml created')

    # update each function's unum_config.json by replacing function names with
    # arns in the continuation
    for f in app_template["Functions"]:
        app_dir = app_template["Functions"][f]["Properties"]["CodeUri"]
        print(f'Updating function {f} in {app_dir}')

        with open(f'{app_dir}unum_config.json', 'r+') as c:
            config = json.loads(c.read())
            print(f'Overwriting {app_dir}unum_config.json')
            if "Next" in config:
                if isinstance(config["Next"],dict):
                    config["Next"]["Name"] = function_to_arn_mapping[config["Next"]["Name"]]
                if isinstance(config["Next"], list):
                    for cnt in config["Next"]:
                        cnt["Name"] = function_to_arn_mapping[cnt["Name"]]
                c.seek(0)
                c.write(json.dumps(config))
                c.truncate()
                print(f'{app_dir}unum_config.json Updated')


def deploy_sam(args):
    # check if AWS_PROFILE is set
    if os.getenv("AWS_PROFILE") == None:
        raise OSError(f'Environment variable $AWS_PROFILE must exist')

    if os.path.isfile('function-arn.yaml') == False:
        # This is the first time to deploy this app. Need to do a trial
        # deployment to create the Lambda resources and get their arn. With
        # the arns, replace the `Name` field of the continuation of each
        # unum-config.json with the arn of the deployed Lambda, rebuild the
        # functions and then deploy again.
        deploy_sam_first()
        args.template=False
        args.clean=False
        build(args)

    # second deployment
    with open("unum-template.yaml") as f:
        app_template = yaml.load(f.read(),Loader=Loader)

    app_name = app_template["Globals"]["ApplicationName"]

    ret = subprocess.run(["sam", "deploy",
                          "--stack-name", app_name,
                          "--region", "us-west-1",
                          "--no-fail-on-empty-changeset",
                          "--no-confirm-changeset",
                          "--resolve-s3",
                          "--capabilities",
                          "CAPABILITY_IAM"],
                          capture_output=True)
    stdout = ret.stdout.decode("utf-8")
    print(stdout)

def deploy(args):
    if args.build:
        args.template=False
        args.clean=False
        build(args)

    # if args.platform == "aws":
    #     deploy_sam(args)
    # elif args.platform =="azure":
    #     return_code
    # elif args.platform == None:
    #     deploy_sam(args)

    # TODO: add azure
    platform_template_fn = "template.yaml"
    try:
        with open(platform_template_fn) as f:
            # platform_template = yaml.load(f.read(), Loader=Loader)
            platform_template = load_yaml(f.read())
    except Exception as e:
        raise IOError(f'Make sure {platform_template_fn} exists in the current directory')

    if "AWSTemplateFormatVersion" in platform_template:
        deploy_sam(args)
    elif "AZure" in platform_template:
        return
    else:
        raise

def template(args):

    # unum-cli template -c/--clean
    if args.clean:
        try:
            subprocess.run(['rm', '-f', 'template.yaml'], check=True)
        except Exception as e:
            raise e
        return

    # if platform is not specified
    if args.platform == None:
        print(f'No target platform specified.\nDefault to \033[33m\033[1mAWS\033[0m.')
        print(f'If AWS is not the desirable target, specify a target platform with -p or --platform.\nSee unum-cli template -h for details.\n')
        args.platform='aws'

    # if a unum-template file is not specified
    if args.template == None:
        print(f'No unum template file specified.\nDefault to\033[33m\033[1m unum-template.yaml \033[0m')
        print(f'You can specify a template file with -t or --template.\nSee unum-cli template -h for details.\n')
        args.template = 'unum-template.yaml'

    try:
        with open(args.template) as f:
            unum_template = yaml.load(f.read(), Loader=Loader)
    except Exception as e:
        print(f'\033[31m \n Build Failed!\n\n Make sure the template file exists\033[0m')
        raise e

    if args.platform == 'aws':
        platform_template = generate_sam_template(unum_template)

        # Save the AWS SAM template as 'template.yaml'
        print(f'\033[32mPlatform Template Generation Succeeded\033[0m\n')
        print(f'\033[33mAWS SAM Template: template.yaml\033[0m\n')
        try:
            with open('template.yaml','w') as f:
                f.write(dump_yaml(platform_template))
        except Exception as e:
            raise e

        # AWS-specific template post-processing
        # YAML dumpper (even the AWS-provided one) doesn't correctly recognize
        # Cloudformation tags and results in !GetAtt being saved as a string.
        with open('template.yaml','r+') as f:
            cnt = f.read()
            # YAML dumpper (even the AWS-provided one) doesn't correctly recognize
            # Cloudformation tags and results in !GetAtt being saved as a string.
            cnt = cnt.replace("Value: '!GetAtt", "Value: !GetAtt").replace("Function.Arn'","Function.Arn")
            f.seek(0)
            f.write(cnt)
            f.truncate()

    elif args.platform == 'azure':
        # platform_template = generate_azure_template(app_template)
        return
    elif args.platform ==None:
        print(f'Failed to generate platform template due to missing target')
        raise ValueError(f'Specify target platform with -p or --platform. See unum-cli template -h for details.')
    else:
        raise ValueError(f'Unknown platform: {args.platform}')



def compile_workflow(args):
    print(args)
    print(args.platform)
    print(type(args))



def main():
    parser = argparse.ArgumentParser(description='unum CLI utility for creating, building and deploying unum applications',
        # usage = "unum-cli [options] <command> <subcommand> [<subcommand> ...] [parameters]",
        epilog="To see help text for a specific command, use unum-cli <command> -h")

    subparsers = parser.add_subparsers(title='command', dest="command", required=True)

    # init command parser
    init_parser = subparsers.add_parser("init", description="create unum application")

    # template command parser
    template_parser = subparsers.add_parser("template", description="generate platform specific template")
    template_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=False)
    template_parser.add_argument('-t', '--template',
        help="unum template file", required=False)
    template_parser.add_argument("-c", "--clean", help="Remove build artifacts",
        required=False, action="store_true")

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

    # deploy command parser
    deploy_parser = subparsers.add_parser("deploy", description="deploy unum application")
    deploy_parser.add_argument('-b', '--build', help="build before deploying",
        required=False, action="store_true")
    deploy_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=False)

    # compile commmand parser
    compile_parser = subparsers.add_parser("compile", description="compile workflow definitions to unum functions")
    compile_parser.add_argument('-p', '--platform', choices=['step-functions'],
        help='workflow definition type', required=True)
    compile_parser.add_argument('-w', '--workflow', required=True, help="workflow file")
    compile_parser.add_argument('-t', '--template', required=True, help="unum template file")
    compile_parser.add_argument('-o', '--optimize', required=False, choices=['trim'], help="optimizations")

    args = parser.parse_args()

    if args.command == 'build':
        build(args)
    elif args.command == 'deploy':
        deploy(args)
    elif args.command == 'template':
        template(args)
    elif args.command =='init':
        init(args)
    elif args.command == 'compile':
        compile_workflow(args)
    else:
        raise IOError(f'Unknown command: {args.command}')
        
if __name__ == '__main__':
    main()