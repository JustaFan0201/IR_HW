# V2Api.FileStoreApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**deleteFile**](FileStoreApi.md#deleteFile) | **DELETE** /cluster/filestore/files{path} | Delete a file or directory from the filestore.
[**deleteFileDeprecated**](FileStoreApi.md#deleteFileDeprecated) | **DELETE** /cluster/files{path} | Delete a file or directory from the filestore. Deprecated: Use &#39;deleteFile&#39; instead
[**fetchFile**](FileStoreApi.md#fetchFile) | **POST** /cluster/filestore/commands/fetch{path} | Fetches a filestore entry from other nodes in the cluster.
[**getFile**](FileStoreApi.md#getFile) | **GET** /cluster/filestore/files{filePath} | Retrieve raw contents of a file in the filestore.
[**getFile1**](FileStoreApi.md#getFile1) | **GET** /node/files{path} | Retrieve file contents or metadata from the filestore.
[**getMetadata**](FileStoreApi.md#getMetadata) | **GET** /cluster/filestore/metadata{path} | Retrieve metadata about a file or directory in the filestore.
[**syncFile**](FileStoreApi.md#syncFile) | **POST** /cluster/filestore/commands/sync{path} | Syncs a file by pushing it to other nodes in the cluster.
[**uploadFile**](FileStoreApi.md#uploadFile) | **PUT** /cluster/filestore/files{filePath} | Upload a file to the filestore.
[**uploadFileDeprecated**](FileStoreApi.md#uploadFileDeprecated) | **PUT** /cluster/files{filePath} | Upload a file to the filestore.  Deprecated: Use &#39;uploadFile&#39; instead



## deleteFile

> SolrJerseyResponse deleteFile(path, opts)

Delete a file or directory from the filestore.

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let path = "path_example"; // String | Path to a file or directory within the filestore
let opts = {
  'localDelete': true // Boolean | Indicates whether the deletion should only be done on the receiving node.  For internal use only
};
apiInstance.deleteFile(path, opts, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **String**| Path to a file or directory within the filestore | 
 **localDelete** | **Boolean**| Indicates whether the deletion should only be done on the receiving node.  For internal use only | [optional] 

### Return type

[**SolrJerseyResponse**](SolrJerseyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## deleteFileDeprecated

> SolrJerseyResponse deleteFileDeprecated(path, opts)

Delete a file or directory from the filestore. Deprecated: Use &#39;deleteFile&#39; instead

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let path = "path_example"; // String | Path to a file or directory within the filestore
let opts = {
  'localDelete': true // Boolean | Indicates whether the deletion should only be done on the receiving node.  For internal use only
};
apiInstance.deleteFileDeprecated(path, opts, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **String**| Path to a file or directory within the filestore | 
 **localDelete** | **Boolean**| Indicates whether the deletion should only be done on the receiving node.  For internal use only | [optional] 

### Return type

[**SolrJerseyResponse**](SolrJerseyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## fetchFile

> SolrJerseyResponse fetchFile(path, opts)

Fetches a filestore entry from other nodes in the cluster.

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let path = "path_example"; // String | Path to a file or directory within the filestore
let opts = {
  'getFrom': "getFrom_example" // String | An optional Solr node name to fetch the file from
};
apiInstance.fetchFile(path, opts, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **String**| Path to a file or directory within the filestore | 
 **getFrom** | **String**| An optional Solr node name to fetch the file from | [optional] 

### Return type

[**SolrJerseyResponse**](SolrJerseyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getFile

> SolrJerseyResponse getFile(filePath)

Retrieve raw contents of a file in the filestore.

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let filePath = "filePath_example"; // String | Path to a file or directory within the filestore
apiInstance.getFile(filePath, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filePath** | **String**| Path to a file or directory within the filestore | 

### Return type

[**SolrJerseyResponse**](SolrJerseyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getFile1

> SolrJerseyResponse getFile1(path, opts)

Retrieve file contents or metadata from the filestore.

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let path = "path_example"; // String | Path to a file or directory within the filestore
let opts = {
  'sync': true, // Boolean | If true, triggers syncing for this file across all nodes in the filestore
  'getFrom': "getFrom_example", // String | An optional Solr node name to fetch the file from
  'meta': true // Boolean | Indicates that (only) file metadata should be fetched
};
apiInstance.getFile1(path, opts, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **String**| Path to a file or directory within the filestore | 
 **sync** | **Boolean**| If true, triggers syncing for this file across all nodes in the filestore | [optional] 
 **getFrom** | **String**| An optional Solr node name to fetch the file from | [optional] 
 **meta** | **Boolean**| Indicates that (only) file metadata should be fetched | [optional] 

### Return type

[**SolrJerseyResponse**](SolrJerseyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getMetadata

> FileStoreDirectoryListingResponse getMetadata(path)

Retrieve metadata about a file or directory in the filestore.

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let path = "path_example"; // String | Path to a file or directory within the filestore
apiInstance.getMetadata(path, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **String**| Path to a file or directory within the filestore | 

### Return type

[**FileStoreDirectoryListingResponse**](FileStoreDirectoryListingResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## syncFile

> SolrJerseyResponse syncFile(path)

Syncs a file by pushing it to other nodes in the cluster.

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let path = "path_example"; // String | Path to a file or directory within the filestore
apiInstance.syncFile(path, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **path** | **String**| Path to a file or directory within the filestore | 

### Return type

[**SolrJerseyResponse**](SolrJerseyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## uploadFile

> UploadToFileStoreResponse uploadFile(filePath, body, opts)

Upload a file to the filestore.

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let filePath = "filePath_example"; // String | File store path
let body = {key: null}; // Object | 
let opts = {
  'sig': ["null"] // [String] | Signature(s) for the file being uploaded
};
apiInstance.uploadFile(filePath, body, opts, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filePath** | **String**| File store path | 
 **body** | **Object**|  | 
 **sig** | [**[String]**](String.md)| Signature(s) for the file being uploaded | [optional] 

### Return type

[**UploadToFileStoreResponse**](UploadToFileStoreResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## uploadFileDeprecated

> UploadToFileStoreResponse uploadFileDeprecated(filePath, body, opts)

Upload a file to the filestore.  Deprecated: Use &#39;uploadFile&#39; instead

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.FileStoreApi();
let filePath = "filePath_example"; // String | File store path
let body = {key: null}; // Object | 
let opts = {
  'sig': ["null"] // [String] | Signature(s) for the file being uploaded
};
apiInstance.uploadFileDeprecated(filePath, body, opts, (error, data, response) => {
  if (error) {
    console.error(error);
  } else {
    console.log('API called successfully. Returned data: ' + data);
  }
});
```

### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **filePath** | **String**| File store path | 
 **body** | **Object**|  | 
 **sig** | [**[String]**](String.md)| Signature(s) for the file being uploaded | [optional] 

### Return type

[**UploadToFileStoreResponse**](UploadToFileStoreResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*

