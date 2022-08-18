#!/usr/bin/env python3

import argparse
import contextlib
import json
import logging
import os
from pathlib import Path
import subprocess

import yaml

import pulumi
from pulumi import automation as auto
from sw_pulumi_algolia import ApiKey, Index
from pulumi_gcp import secretmanager as sm


SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.yaml")
HOME_DIR = str(Path.home())
AGP_DIR = os.path.join(HOME_DIR, ".agp")
AGP_SECRETS = os.path.join(AGP_DIR, "secrets")
EXTENSIONS_DIR = os.path.join(SCRIPT_DIR, "..", "..", "extensions")
FIREBASE_CONFIG_FILE = os.path.join(SCRIPT_DIR, "..", "..", "firebase.json")

#logging.basicConfig(level=logging.INFO)


def get_gcloud_config():
    """Fetch Google Cloud Config."""
    gcloud_config = subprocess.run(
        [
            "gcloud",
            "info",
            "--format",
            "json",
        ],
        stdout=subprocess.PIPE,
        check=True,
    )
    config = gcloud_config.stdout.decode('utf-8')
    return config


def create_or_update_algolia_indexes(idxs: list[str]) -> None:
    """Create or update index resource of Algolia.

    Parameter:
        idxs: List of indexes.

    Returns:
        None
    """
    for idx in idxs:
        Index(f"algolia-index-{idx}", name=idx)


def create_or_update_algolia_api_keys(api_keys: list[any]) -> None:
    """Create or update api key resource of Algolia.

    Parameter:
        api_keys: List of API keys.

    Returns:
        None
    """
    for api_key in api_keys:
        name = api_key.get("name")
        acls = api_key.get("acls")
        indexes = api_key.get("indexes", [])
        description = api_key.get("description", f"API Key for {name}")
        max_api_call = int(api_key.get("maxApiCall", 15000))
        max_hits_per_query = int(api_key.get("maxHitsPerQuery", 0))
        referers = api_key.get("referers", [])
        validity = int(api_key.get("validity", 0))

        key = ApiKey(
            f"algolia-api-key-{name}",
            acls=acls,
            description=description,
            indexes=indexes,
            max_hits_per_query=max_hits_per_query,
            max_queries_per_ip_per_hour=max_api_call,
            referers=referers,
            validity=validity,
        )
        pulumi.export(f"algolia-api-key-{name}", key.key)


def create_pulumi_file(project_name) -> None:
    """Create a temporary Pulumi.yaml file for executing pulumi cli.

    Parameter:
        project_name: Pulumi project name.

    Returns:
        None
    """

    data = f"""name: {project_name}
runtime:
  name: python
  options:
    virtualenv: venv
description: A minimal Python Pulumi Program
"""

    pulumi_file = os.path.join(SCRIPT_DIR, "Pulumi.yaml")
    write_to_file(pulumi_file, data)


def get_secret_values(project_name:str, stack_name: str) -> dict:
    """Fetch the secret value exported to stack output.

    Parameter:

    Returns:
        Decrypted stack output secret.
    """
    create_pulumi_file(project_name)
    subprocess.run(
        [
            "pulumi",
            "stack",
            "select",
            stack_name,
        ],
        check=True,
    )
    out = subprocess.run(
        [
            "pulumi",
            "stack",
            "output",
            "-j",
            "--show-secrets",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    output = json.loads(out.stdout.decode("utf-8"))

    return output


def create_or_update_gcp_secret(username: str, secrets: dict) -> None:
    """Create or update GCP Secret resource.

    Parameters:
        username: Google account username for labels.

    Returns:
        None
    """
    print("@ create or update secret")
    print(f"secrets: {secrets}")
    for k in secrets:
        secret_data = secrets[k]
        name = k.removeprefix("algolia-api-key-")

        print(f"secret is {secret_data} and name is {name}")

        secret = sm.Secret(
            f"secret-{name}", # pulumi unique resource name
            labels={
                "created-by": username,
            },
            replication={
                "automatic": "true",
            },
            secret_id=f"lester-test-algolia-secret-{name}",
        )


        sm.SecretVersion(
            f"secret-version-{name}", # Automatically updates secret version
            secret=secret.id,
            secret_data=secret_data,
        )


def get_config_from_yaml_file(config_file: str) -> dict:
    """Read configuration values from a YAML config file.

    Parameters:
        config_file: Path to the config file.

    Returns:
        cfg: A dictionary of configuration values.
    """
    with open(config_file) as cf:
        try:
            cfg = yaml.safe_load(cf)
            return cfg
        except yaml.YAMLError as e:
            logging.error(f" An error occured:\n    {e}")
            exit(1)


def get_config_from_json_file(config_file: str) -> dict:
    """Read configuration values from a JSON config file.

    Parameter:
        config_file: Path to the config file.

    Returns:
        cfg: A dictionary of configuration values.
    """
    with open(config_file) as cf:
        try:
            cfg = json.load(cf)
            return cfg
        except Exception as e:
            logging.error(f" An exception occured while reading file {config_file}.\n   {e}")
            exit(1)


def execute_pulumi_verb(stack, verb: str, stack_name: str):
    """Execute specified Pulumi operation.

    Parameters:
        stack: Pulumi stack object.
        verb: Puluim operation.

    Returns:
        resp: Pulumi operation response.
    """
    if verb == "preview":
        resp = stack.preview()
        logging.info(f" Preview:\n{resp.stdout}stderr: {resp.stderr}\nchange summary: {resp.change_summary}")
        exit(0)
    elif verb == "rm" or verb == "rm-stack":
        logging.info(f" Removing resources of stack: {stack_name}")
        resp = stack.destroy()
        if verb == "rm-stack":
            logging.info(f" Removing stack: {stack_name}")
            resp = stack.workspace.remove_stack(stack_name)
    elif verb == "up":
        logging.info(f" Updating stack: {stack_name}")
        with contextlib.redirect_stdout(open(os.devnull, 'w')):
            print("github!!!!")
            resp = stack.up(parallel=1)
        print("github v2 !!!!")
    else:
        logging.error(f" Unknown verb {verb}! Valid operations are: [preview, rm, rm-stack, up].")
        exit(1)

    return resp


def get_environments_to_deploy(env: str) -> list[str]:
    """Fetch environments to deploy.

    Parameter:
        env: Environments fromm user input.

    Returns:
        environments: A list of environments to deploy.
    """
    environments = env.split(",")
    try:
        environments.remove("all")
    except ValueError:
        pass

    return environments


def get_env_config(cfg: dict):
    """Fetch the configuration values of an environment.

    Parameters:
        cfg: A dictionary containing the mapping of environments and their config values.
        env: Name of the environment.
    """
    try:
        global_cfg = cfg.get("global")
        algolia_api_key_name = global_cfg.get("algoliaApiKeyName")
        force_data_sync = global_cfg.get("forceDataSync", "no")
        location = global_cfg.get("location", "us-west2")
        environments = global_cfg.get("environments")
        firebase_search_extension = global_cfg.get("searchExtension", "algolia/firestore-algolia-search@0.5.13")

        algolia_indexes = cfg.get("algoliaIndexes")

        algolia_api_keys = cfg.get("algoliaApiKeys")

        return (
            algolia_api_key_name,
            force_data_sync,
            location,
            environments,
            algolia_indexes,
            algolia_api_keys,
            firebase_search_extension,
        )
    except Exception as e:
        logging.error(f" Exception occured:\n    {e}")
        exit(1)


def write_to_file(filename: str, data: str) -> None:
    """Writes data to file.

    Parameters:
        filename: Path to the file.
        data: Data to write.

    Returns:
        None
    """
    try:
        with open(filename, "w") as f:
            f.write(data)
    except Exception as e:
        logging.error(f" Exception occured while writing to file {filename}.\n    {e}")


def create_or_update_cfg_files(update_dictionary: dict) -> None:
    """Create or update configuration files or environments.

    Parameters:
        update_dictionary: Dictionary containing all update values.
    """

    # unpack
    skip_update_extensions = update_dictionary.get("skip_update_extensions")
    skip_update_firebase_config = update_dictionary.get("skip_update_firebase_config")
    environment = update_dictionary.get("environment")
    environment_config = update_dictionary.get("environment_config")
    algolia_indexes = update_dictionary.get("algolia_indexes")
    firebase_search_extension = update_dictionary.get("firebase_search_extension")
    algolia_api_key_name = update_dictionary.get("algolia_api_key_name")
    admmin_app_id = update_dictionary.get("admin_app_id")
    force_data_sync = update_dictionary.get("force_data_sync")
    location = update_dictionary.get("location")
    extensions_dir = update_dictionary.get("extensions_dir")
    firebase_config_file = update_dictionary.get("firebase_config_file")

    print("Here at create or update cfg files")
    print(f"skip ext: {skip_update_extensions} and skip firebase: {skip_update_firebase_config}")

    for index in algolia_indexes:
        extension_file_name = "search-" + index.replace(".", "-") + ".env." + environment

        print(f"for loop {extension_file_name}")

        if not skip_update_extensions:
            print("not skipping extension update")
            env_algolia_api_key_name = environment_config.get("algoliaApiKeyName", algolia_api_key_name)
            env_algolia_app_id = environment_config.get("algoliaAppId", admin_app_id)
            env_force_data_sync = environment_config.get("forceDataSync", force_data_sync)
            env_location = environment_config.get("location", location)
            data = f"""ALGOLIA_API_KEY={env_algolia_api_key_name}
ALGOLIA_APP_ID={env_algolia_app_id}
ALGOLIA_INDEX_NAME={index}
COLLECTION_PATH={index}
FORCE_DATA_SYNC={env_force_data_sync}
LOCATION={env_location}
"""

            extension_file_path = os.path.join(extensions_dir, extension_file_name)
            write_to_file(extension_file_path, data)

        if not skip_update_firebase_config:
            print("not skipping firebase update")
            firebase_cfg = get_config_from_json_file(firebase_config_file)

            firebase_extensions = firebase_cfg.get("extensions")

            extension = extension_file_name.split(".env")[0]

            firebase_extensions[extension] = firebase_search_extension

            write_to_file(firebase_config_file, json.dumps(firebase_cfg, indent=2))


def get_agp_admin_config(config_file: str, env: str) -> (str, str, str):
    """Fetch secret configuration values.

    Parameters:
        config_file: Configuration file path.
        env: Environment name from the configuration file.

    Returns:
        admin_api_key: Algolia admin API Key.
        admin_app_id: Algolia application ID,
        gcp_project: Google Project Name.
    """
    try:
        cfg = get_config_from_json_file(config_file)

        admin_api_key = cfg[env]["apiKey"]
        admin_app_id = cfg[env]["appId"]
        gcp_project = cfg[env]["gcpProject"]

    except KeyError:
        logging.warning(f" Environment {env} missing from config file {config_file}. Skipping.")
        admin_api_key = ""
        admin_app_id = ""
        gcp_project = ""

    except Exception as e:
        logging.error(f" An exception occured:\n    {e}")
        exit(1)

    return (admin_api_key, admin_app_id, gcp_project)


def skip_file_update(resp, verb):
    """Checks whether to skip a file update or not."""
    # Always make sure that by default, we skip file updates.
    skip = True
    resource_changes = {}
    if verb == "up":
        try:
            resource_changes = resp.summary.resource_changes
            del resource_changes["same"]
            if len(resource_changes) == 0:
                skip = True
            else:
                skip = False
        except:
            pass

    return skip


def run(args):
    byte_config = get_gcloud_config()
    config = json.loads(byte_config)
    account = config["config"]["account"]
    username = account.split("@")[0]

    algolia_admin_config_file = args.agp_secrets

    cfg = get_config_from_yaml_file(args.config_file)

    (
        algolia_api_key_name,
        force_data_sync,
        location,
        envs,
        algolia_indexes_gen,
        algolia_api_keys_gen,
        firebase_search_extension,
    ) = get_env_config(cfg)

    environments = get_environments_to_deploy(args.environment)
    if len(environments) == 0:
        environments = [ e for e in envs ]

    for env in environments:
        env_conf = envs.get(env)
        env_prefix = env_conf.get("prefix")
        env_ns = env_conf.get("namespace")

        (
            admin_api_key,
            admin_app_id,
            gcp_project,
        ) = get_agp_admin_config(algolia_admin_config_file, f"{env_ns}-{env}")

        project_name = f"{env_prefix}--{env_ns}-{env}"

        deploy_indexes = args.indexes_only
        deploy_api_keys = args.api_keys_only
        skip_update_extensions = args.skip_update_extensions
        skip_update_firebase_config = args.skip_update_firebase_config

        if not args.indexes_only and not args.api_keys_only:
            # deploy both indexes and api keys
            deploy_indexes = True
            deploy_api_keys = True

        algolia_indexes = []
        algolia_api_keys = []

        if (
            len(admin_api_key) == 0
            or len(admin_app_id) == 0
            or len(gcp_project) == 0
        ):
            deploy_indexes = False
            deploy_api_keys = False
            skip_update_extensions = True
            skip_update_firebase_config = True

        if deploy_indexes:
            print("deploy indexes!")
            stack_name_indexes = project_name + "-indexes"
            algolia_indexes = algolia_indexes_gen + env_conf.get("algoliaIndexes", [])
            try:
                def pulumi_program_indexes():
                    return create_or_update_algolia_indexes(algolia_indexes)


                stack_indexes = auto.create_or_select_stack(
                    stack_name=stack_name_indexes,
                    project_name=project_name,
                    program=pulumi_program_indexes,
                )

                stack_indexes.set_config("algolia:apiKey", auto.ConfigValue(value=admin_api_key, secret=True))
                stack_indexes.set_config("algolia:applicationId", auto.ConfigValue(value=admin_app_id))

                resp = execute_pulumi_verb(stack_indexes, args.verb, stack_name_indexes)
                skip_update_extensions = skip_file_update(resp, args.verb)
            except:
                skip_update_extensions = True

        if deploy_api_keys:
            print("deploy api keys!")
            stack_name_api_keys = project_name + "-api-keys"
            stack_name_secrets = project_name + "-secrets"
            algolia_api_keys = algolia_api_keys_gen + env_conf.get("algoliaApiKeys", [])
            try:
                def pulumi_program_api_keys():
                    return create_or_update_algolia_api_keys(algolia_api_keys)


                stack_api_keys = auto.create_or_select_stack(
                    stack_name=stack_name_api_keys,
                    project_name=project_name,
                    program=pulumi_program_api_keys,
                )

                stack_api_keys.set_config("algolia:apiKey", auto.ConfigValue(value=admin_api_key, secret=True))
                stack_api_keys.set_config("algolia:applicationId", auto.ConfigValue(value=admin_app_id))

                resp = execute_pulumi_verb(stack_api_keys, args.verb, stack_name_api_keys)
                skip_update_firebase_config = skip_file_update(resp, args.verb)

                secrets = get_secret_values(project_name, stack_name_api_keys)
                print(f"secrets: {secrets}")

                def pulumi_program_secrets():
                    return create_or_update_gcp_secret(username, secrets)


                stack_gcp_secrets = auto.create_or_select_stack(
                    stack_name=stack_name_secrets,
                    project_name=project_name,
                    program=pulumi_program_secrets,
                )
                stack_gcp_secrets.set_config("gcp:project", auto.ConfigValue(value=gcp_project))
                resp = execute_pulumi_verb(stack_gcp_secrets, args.verb, stack_name_secrets)

            except Exception as e:
                logging.error(f"  Exception: {e}")
                skip_update_firebase_config = True

            finally:
                pulumi_file = f"{SCRIPT_DIR}/Pulumi.yaml"
                pulumi_file = os.path.join(SCRIPT_DIR, "Pulumi.yaml")
                Path(pulumi_file).unlink(missing_ok=True)

        update_dictionary = dict(
            skip_update_extensions=skip_update_extensions,
            skip_update_firebase_config=skip_update_firebase_config,
            environment=env,
            environment_config=env_conf,
            algolia_indexes=algolia_indexes,
            firebase_search_extension=firebase_search_extension,
            algolia_api_key_name=algolia_api_key_name,
            admin_app_id=admin_app_id,
            force_data_sync=force_data_sync,
            location=location,
            extensions_dir=args.extensions_dir,
            firebase_config_file=args.firebase_config,
        )

        create_or_update_cfg_files(update_dictionary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "verb",
        action="store",
        default=None,
        choices=["preview", "rm", "rm-stack", "up"],
        help="Execute an operation to environment resources"
    )
    parser.add_argument(
        "environment",
        action="store",
        default="all",
        nargs="?",
        help="Environments to deploy. Use ',' when deploying multiple environments. Deploys all environments by default.",
    )
    parser.add_argument(
        "collection",
        action="store",
        default="all",
        nargs="?",
        help="Collections to deploy. Multiple collections should be separated by ','. Defaults to 'all': deploy all collections.",
    )
    parser.add_argument(
        "--config-file",
        action="store",
        default=CONFIG_FILE,
        help=f"Configuration file in YAML format. Defaults to {CONFIG_FILE}."
    )
    parser.add_argument(
        "--indexes-only",
        action="store_true",
        help="Deploy indexes only when flag is set. When both '--indexes-only' and '--api-keys-only' are set, both flags will be unset.",
    )
    parser.add_argument(
        "--api-keys-only",
        action="store_true",
        help="Deploy API keys only when flag is set. When both '--indexes-only' and '--api-keys-only' are set, both flags will be unset.",
    )
    parser.add_argument(
        "--skip-update-extensions",
        action="store_true",
        help="Skips updates of '.env' files in extensions folder.",
    )
    parser.add_argument(
        "--skip-update-firebase-config",
        action="store_true",
        help="Skips updates of 'firebase.json' config file.",
    )
    parser.add_argument(
        "--agp-secrets",
        action="store",
        default=AGP_SECRETS,
        help="Secrets file containing algolia admin keys.",
    )
    parser.add_argument(
        "--extensions-dir",
        action="store",
        default=EXTENSIONS_DIR,
        help=f"Extensions env file directory. Defaults to {EXTENSIONS_DIR}",
    )
    parser.add_argument(
        "--firebase-config",
        action="store",
        default=FIREBASE_CONFIG_FILE,
        help=f"Path to 'firebase.json' config file. Defaults to {FIREBASE_CONFIG_FILE}",
    )

#    print(os.environ["GRPC_ENABLE_FORK_SUPPORT"])
#    print(os.environ["GRPC_POLL_STRATEGY"])

    os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "true"
    os.environ["GRPC_POLL_STRATEGY"] = "poll"

    print(os.environ["GRPC_ENABLE_FORK_SUPPORT"])
    print(os.environ["GRPC_POLL_STRATEGY"])

    args = parser.parse_args()
    run(args)

    #logging.info(f" env: {args.environment} and verb: {args.verb} and text: {args.collection} and config: {args.config_file}")