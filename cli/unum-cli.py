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
    ''' Given an unum template, return an AWS SAM template

        @param unum_template python dict

        @return sam_template python dict
    '''

    sam_template = {"AWSTemplateFormatVersion": '2010-09-09',
                    "Transform": "AWS::Serverless-2016-10-31"}
    sam_template["Globals"] = {"Function":{"Environment":{"Variables":{
                                                            "UNUM_INTERMEDIARY_DATASTORE_TYPE": unum_template["Globals"]["UnumIntermediaryDataStoreType"],
                                                            "UNUM_INTERMEDIARY_DATASTORE_NAME": unum_template["Globals"]["UnumIntermediaryDataStoreName"],
                                                            "CHECKPOINT":unum_template["Globals"]["Checkpoint"]
                                                         }}}}
    sam_template["Globals"]["Function"]["Timeout"] = 900
    sam_template["Resources"]={}
    sam_template["Outputs"] = {}
    for f in unum_template["Functions"]:
        sam_template["Resources"][f'{f}Function'] = {
                                                         "Type":"AWS::Serverless::Function",
                                                           "Properties": {
                                                               "Handler":"unum.lambda_handler",
                                                               "Runtime": unum_template["Functions"][f]["Properties"]["Runtime"],
                                                               "CodeUri": unum_template["Functions"][f]["Properties"]["CodeUri"],
                                                               "Policies":["AmazonDynamoDBFullAccess","AmazonS3FullAccess","AWSLambdaRole","AWSLambdaBasicExecutionRole"]
                                                           }
                                                       }
        arn = f"!GetAtt {f}Function.Arn"
        sam_template["Outputs"][f'{f}Function'] = {"Value": f"!GetAtt {f}Function.Arn"}

    return sam_template

def sam_build_clean(platform_template):
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
        ret = subprocess.run(["sam", "build"], capture_output=True)
        print(ret.stdout.decode("utf-8"))
    except Exception as e:
        raise OSError(f'{ret.stderr}')
    

def build(args):

    if args.template:
        print("Generating platform template ...........")
        template(args)
        print("Done")

    # TODO: add azure
    platform_template_fn = "template.yaml"

    try:
        with open(platform_template_fn) as f:
            # platform_template = yaml.load(f.read(), Loader=Loader)
            platform_template = load_yaml(f.read())
    except Exception as e:
        print(f'Error: {platform_template_fn} not found.\nMake sure {platform_template_fn} exists in the current directory')
        exit(1)

    if "AWSTemplateFormatVersion" in platform_template:
        sam_build(platform_template, args)
    elif "AZure" in platform_template:
        return
    else:
        raise

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

    if args.clean:
        try:
            subprocess.run(['rm', '-f', 'template.yaml'], check=True)
        except Exception as e:
            raise e
        return

    unum_template_fn = "unum-template.yaml"

    try:
        with open(unum_template_fn) as f:
            app_template = yaml.load(f.read(), Loader=Loader)
    except Exception as e:
        raise IOError(f'no unum-template.yaml found. Make sure to be in an unum application directory')

    if "platform" not in vars(args):
        raise ValueError(f'specify target platform with -p or --platform. See unum-cli template -h for details.')

    if args.platform == 'aws':
        template = generate_sam_template(app_template)
    elif args.platform == 'azure':
        # template = generate_azure_template(app_template)
        return
    elif args.platform ==None:
        print(f'Failed to generate platform template due to missing target')
        raise ValueError(f'specify target platform with -p or --platform. See unum-cli template -h for details.')
    else:
        raise ValueError(f'Unknown platform: {args.platform}')

    with open('template.yaml','w') as f:
        # f.write(yaml.dump(template, Dumper=Dumper))
        f.write(dump_yaml(template))

    with open('template.yaml','r+') as f:
        cnt = f.read()
        cnt = cnt.replace("Value: '!GetAtt", "Value: !GetAtt").replace("Function.Arn'","Function.Arn")
        f.seek(0)
        f.write(cnt)
        f.truncate()



def main():
    parser = argparse.ArgumentParser(description='unum CLI utility for creating, building and deploying unum applications',
        # usage = "unum-cli [options] <command> <subcommand> [<subcommand> ...] [parameters]",
        epilog="To see help text for a specific command, use unum-cli <command> -h")

    subparsers = parser.add_subparsers(title='command', dest="command", required=True)

    # template command parser
    template_parser = subparsers.add_parser("template", description="generate platform specific template")
    template_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=True)
    template_parser.add_argument("-c", "--clean", help="Remove build artifacts",
        required=False, action="store_true")

    # init command parser
    init_parser = subparsers.add_parser("init", description="create unum application")

    # build command parser
    build_parser = subparsers.add_parser("build", description="build unum application in the current directory")
    build_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=False)
    build_parser.add_argument("-t", "--template", help="Generate a platform template before buliding",
        required = False, action="store_true")
    build_parser.add_argument("-c", "--clean", help="Remove build artifacts",
        required=False, action="store_true")


    # deploy command parser
    deploy_parser = subparsers.add_parser("deploy", description="deploy unum application")
    deploy_parser.add_argument('-b', '--build', help="build before deploying",
        required=False, action="store_true")
    deploy_parser.add_argument('-p', '--platform', choices=['aws', 'azure'],
        help="target platform", required=False)

    args = parser.parse_args()

    if args.command == 'build':
        build(args)
    elif args.command == 'deploy':
        deploy(args)
    elif args.command == 'template':
        template(args)
    elif args.command =='init':
        init(args)
    else:
        raise IOError(f'Unknown command: {args.command}')
        
if __name__ == '__main__':
    main()