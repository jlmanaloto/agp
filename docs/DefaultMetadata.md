# DefaultMetadata

This resource specifies the default values to use for deployment. Only **one** ``DefaultMetadata`` must exist per chart.

Below shows the schema for ``DefaultMetadata``.


| Key | Type | Required | Description |
|-----|------|----------|-------------|
| name | string | no | Name of the resource. Defaults to ``DefaultMetadata`` |
| spec | object (dict) | no | Resource specification |
| spec.environment | object | no | Specification for environment values |
| spec.gcp | object | yes | Contains specs for Google Cloud Platform |
| spec.pulumi | object | yes | Contains specs for Pulumi resources |
| spec.algolia | object | yes | Contains specs for Algolia resources |

## Spec

### Environment

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| spec.environment.updateExtensions | boolean | no | set to ``true`` to update extensions env files. Defaults to ``true`` |
| spec.environment.updateCollections | boolean | no | set to ``true`` to update firebase config file extensions. Defaults to ``false`` |

### GCP

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| project | string | yes | Name of the GCP Project |
| region | string | no | GCP region. Defaults to ``us-west2`` |
| forceDataSync | boolean | no | Set to true to force data sync. Defaults to ``false`` |

### Pulumi

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| namespace | string | no | Stack resource namespace. Defaults to ``""`` |
| prefix | string | no | Prefix used for creating project names. Defaults to ``""`` |
| stack | string | yes | Stack name used for deploying resources |

## Algolia

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| apiKeyName | string | yes | Name of the secret from GCP Secret Manager. Equivalent to ``projects/${param:PROJECT_NUMBER}/secrets/``{apiKeyName}``/versions/latest`` |
| appId | string | yes | Algolia application ID |

Full ``DefaultMetadata`` resource example:

   kind: DefaultMetadata
   spec:
     environment:
       updateExtensions: true
       updateCollections: false
     gcp:
       project: my-gcp-project
       region: us-west2
       forceDataSync: false
     pulumi:
       namespace: my-ns
       prefix: my-organization
       stack: alpha
     algolia:
       apiKeyName: api-key-name
       appId: my-algolia-app-id
