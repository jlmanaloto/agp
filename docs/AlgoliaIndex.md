# AlgoliaIndex

This resource specifies the metadata and specifications of Algolia indexes and API Keys.
At least 1 instance of this resource must exist in a chart otherwise, no resources will be
deployed.

Below shows the schema for ``AlgoliaIndex``.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| **name** | string | yes | ``AlgoliaIndex`` resource name |
| **collectionPrefix** | string | no | Prefix to use when creating an extension env file. Defaults to ``search`` |
| **environment** | string | no | The environment scope of the ``AlgoliaIndex`` resource. The resource will only be deployed to the specified environment. Defaults to ``default`` - deploy to all environments |
| **metadata** | object | no | ``AlgoliaIndex`` metadata |
| **spec** | object | yes | ``AlgoliaIndex`` specification |

## Metadata

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| collection | string | no | Collection path key in an extension env file. Defaults to the name of the ``AlgoliaIndex`` resource |
| searchExtension | string | no | Default search extension to use. Defaults to ``algolia/firestore-algolia-search@0.5.13`` |


## Spec

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| secretNamePrefix | string | no | Prefix to use for GCP secret name. Defaults to ``algolia-api-key`` |
| searchableAttributes | list | no | Contains all searchable attributes of an index. Defaults to ``[]`` |
| apiKey | object | no | Contains Algolia API Key resource specification |

### Searchable Attributes

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| name | string | yes | Attribute name |
| ordered | boolean | no | Specifies if an attribute is ordered or not. Defaults to ``true`` |

### API Key

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| description | string | no | Description for the API Key. Defaults to ``API Key for {{ name of index }}`` |
| acls | list | no | List of Algolia Index ACLs. Defaults to ``[]`` |
| indexes | list | no | List of indexes the API Key has permission to operate. Defaults to ``[]`` |
| maxApiCall | integer | no | Maximum API Call allowed from an IP address per hour. Defaults to ``15000`` |
| maxHitsPerQuer | integer | no | Maximum hits the API Key can retrieve in one call. Defaults to ``0`` |
| referers | list | no | List of query parameters. Defaults to ``[]`` |
| validity | integer | no | How long the API Key is valid. Defaults to ``0`` - does not expire |

Full ``AlgoliaIndex`` resource configuration example:

   ```
   kind: AlgoliaIndex
   name: test-index
   collectionPrefix: search
   environment: testing # Specify environment to deploy to 'testing' environment only.
   metadata:
     collection: test # The 'COLLECTION_PATH' for the extension env file of the index. Defaults to index name.
     searchExtension: "algolia/firestore-algolia-search@0.5.13"
   spec:
     secretNamePrefix: algolia-api-key
     searchableAttributes:
       - name: username
         ordered: true
       - name: some_attribute
         ordered: false
     apiKey:
       description: API Key for testing
       acls:
         - search
       indexes:
         - test-index
       maxApiCall: 15000
       maxHitsPerQuery: 0
       referers: []
       validity: 0
   ```
