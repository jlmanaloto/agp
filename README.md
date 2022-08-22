# agp

Algolia GCP Pulumi Stack

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Requirements

- [Python](https://www.python.org/downloads) >= 3.9
- [Pulumi](https://www.pulumi.com/docs/get-started/install) >= 3.38.0

## Getting Started

Make sure that you have a Pulumi account already setup before proceeding. Pulumi has a
[Before You Begin](https://www.pulumi.com/docs/get-started/gcp/begin/) page for getting started with
Pulumi and GCP.

1. **Initialize agp**:

   ```bash
   $ ./agp init
   ```

2. **Set agp configuration values**:

   AGP Configuration is in the format:

   ``namespace-environment:key=value``
   See **Configuration** for more information.

   ```bash
   $ ./agp set dev-env:apiKey=my-apikey
   ```

3. Deploy resources:

   ```bash
   $ ./agp up 
   ```
   By default, agp will deploy the resources of **all** environments specified in ``config.yaml``.
   To deploy the resources of a specific environment:

   ```bash
   $ ./agp up my-env
   ```

   This will deploy the resources of the environment ``my-env`` from ``config.yaml`` containing the following values:

   ```
   global:
     environments:
       my-env:
         # this contains environment-specific values which overrides the global values
         ...
         ...
   ```

4. Delete resources:

   ```bash
   $ ./agp rm
   ```

   By default, agp will delete the resources of **all** environments specified in ``config.yaml``.
   To delete the resources of a specific environment:

   ```bash
   $ ./agp rm my-env
   ```

5. Delete Pulumi stack:

   ```bash
   $ ./agp rm-stack
   ```

   By default, agp will delete the stacks of **all** environment specified in ``config.yaml``.
   To delete the stacks of a specific environment:

   ```bash
   $ ./agp rm-stack my-env
   ```

After deploying using ``./agp up``, AGP will update the ``.env`` files in the ``extensions/`` folder and the ``firebase.json``
file. The conditions of AGP when updating the files are:

- Update only when there are changes
- Update only when using ``./agp up``
- Create or update ``.env`` files for each deployed environment
- Update ``firebase.json``'s ``.extensions`` list with values from ``.algoliaIndexes`` only from ``config.yaml``.
  ``.algoliaIndexes`` is assumed to be the 'production' values.

When destroying resources and stacks, AGP will **never** remove the created ``.env`` files from the ``extensions/`` folder
and ``firebase.json``'s ``.extensions`` list. This is to have a fallback option when you accidentally removed the resources 
of an environment. If you want to remove an extension, you have to do it manually.

### Environment Variables

When running ``agp``, you can set some values using environment variables.

| Environment Variable | Description |
|----------------------|-------------|
| AGP_SECRETS | Sets the path to AGP secrets conf file |
| AGP_EXTENSIONS_DIR | Sets the path to the extensions directory |
| AGP_FIREBASE_CONFIG_FILE | Sets the path to the ``firebase.json`` config file |

For more options, run ``./agp -h``.

## Configuration

### AGP Configuration file

AGP configuration file is a secret file containing the Algolia admin credentials and GCP Project name.
Set the configuration values using ``./agp set namespace-environment:key=value``.

To set a configuration for environent ``my-env`` in ``dev`` namespace with key ``appId`` and value ``my-id``:

    $ ./agp set dev-my-env:admin_app_id=my-id

The command above yields to a configuration of:

    {
      "dev-my-env": {
        "appId": "my-id"
      }
    }

| Key | Description |
|-----|-------------|
| apiKey | Algolia admin API Key |
| appId | Algolia application ID |
| gcpProject | Name of the project to deploy the resources to |

### Resources Configuration file

To deploy resources, set the values in ``config.yaml``. See the ``config.sample.yaml`` for more information.

## Notes

When setting an environment configuration with existing resources not created by Pulumi (e.g. Algolia Indexes created manually),
those resources will be skipped during deployment. One option is to recreate the resources using ``./agp up`` or just include
the resources in ``config.yaml`` and let AGP skip the existing resources. If you opt to use the latter, you will see some
(low verbosity) errors. You can safely ignore them. Just be sure to look out for AGP logs:

    INFO: root ...
    ERROR: root ...
    WARNING: root ...

## Known Issues

When deploying using ``./agp up``, you will notice a spam of logs from gRPC:

   ```
   E0818 14:10:15.368489156    6420 fork_posix.cc:76]           Other threads are currently calling into gRPC, skipping fork() handlers
   E0818 14:10:25.209867988    6420 fork_posix.cc:76]           Other threads are currently calling into gRPC, skipping fork() handlers
   E0818 14:10:26.729241149    6420 fork_posix.cc:76]           Other threads are currently calling into gRPC, skipping fork() handlers
   E0818 14:10:28.513267149    6420 fork_posix.cc:76]           Other threads are currently calling into gRPC, skipping fork() handlers
   ```

You can safely ignore logs with that format. See [this issue](https://github.com/pulumi/pulumi/issues/9110).
