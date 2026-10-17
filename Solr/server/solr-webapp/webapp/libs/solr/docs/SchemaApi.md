# V2Api.SchemaApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**getDynamicFieldInfo**](SchemaApi.md#getDynamicFieldInfo) | **GET** /{indexType}/{indexName}/schema/dynamicfields/{fieldName} | Get detailed info about a single dynamic field
[**getFieldInfo**](SchemaApi.md#getFieldInfo) | **GET** /{indexType}/{indexName}/schema/fields/{fieldName} | Get detailed info about a single non-dynamic field
[**getFieldTypeInfo**](SchemaApi.md#getFieldTypeInfo) | **GET** /{indexType}/{indexName}/schema/fieldtypes/{fieldTypeName} | Get detailed info about a single field type
[**getSchemaInfo**](SchemaApi.md#getSchemaInfo) | **GET** /{indexType}/{indexName}/schema | Fetch the entire schema of the specified core or collection
[**getSchemaName**](SchemaApi.md#getSchemaName) | **GET** /{indexType}/{indexName}/schema/name | Get the name of the schema used by the specified core or collection
[**getSchemaSimilarity**](SchemaApi.md#getSchemaSimilarity) | **GET** /{indexType}/{indexName}/schema/similarity | Get the default similarity configuration used by the specified core or collection
[**getSchemaUniqueKey**](SchemaApi.md#getSchemaUniqueKey) | **GET** /{indexType}/{indexName}/schema/uniquekey | Fetch the uniquekey of the specified core or collection
[**getSchemaVersion**](SchemaApi.md#getSchemaVersion) | **GET** /{indexType}/{indexName}/schema/version | Fetch the schema version currently used by the specified core or collection
[**getSchemaZkVersion**](SchemaApi.md#getSchemaZkVersion) | **GET** /{indexType}/{indexName}/schema/zkversion | Fetch the schema version currently used by the specified core or collection
[**listCopyFields**](SchemaApi.md#listCopyFields) | **GET** /{indexType}/{indexName}/schema/copyfields | List all copy-fields in the schema of the specified core or collection
[**listDynamicFields**](SchemaApi.md#listDynamicFields) | **GET** /{indexType}/{indexName}/schema/dynamicfields | List all dynamic-fields in the schema of the specified core or collection
[**listSchemaFieldTypes**](SchemaApi.md#listSchemaFieldTypes) | **GET** /{indexType}/{indexName}/schema/fieldtypes | List all field types in the schema used by the specified core or collection
[**listSchemaFields**](SchemaApi.md#listSchemaFields) | **GET** /{indexType}/{indexName}/schema/fields | List all non-dynamic fields in the schema of the specified core or collection



## getDynamicFieldInfo

> SchemaGetDynamicFieldInfoResponse getDynamicFieldInfo(indexType, indexName, fieldName)

Get detailed info about a single dynamic field

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
let fieldName = "fieldName_example"; // String | 
apiInstance.getDynamicFieldInfo(indexType, indexName, fieldName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 
 **fieldName** | **String**|  | 

### Return type

[**SchemaGetDynamicFieldInfoResponse**](SchemaGetDynamicFieldInfoResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getFieldInfo

> SchemaGetFieldInfoResponse getFieldInfo(indexType, indexName, fieldName)

Get detailed info about a single non-dynamic field

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
let fieldName = "fieldName_example"; // String | 
apiInstance.getFieldInfo(indexType, indexName, fieldName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 
 **fieldName** | **String**|  | 

### Return type

[**SchemaGetFieldInfoResponse**](SchemaGetFieldInfoResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getFieldTypeInfo

> SchemaGetFieldTypeInfoResponse getFieldTypeInfo(indexType, indexName, fieldTypeName)

Get detailed info about a single field type

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
let fieldTypeName = "fieldTypeName_example"; // String | 
apiInstance.getFieldTypeInfo(indexType, indexName, fieldTypeName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 
 **fieldTypeName** | **String**|  | 

### Return type

[**SchemaGetFieldTypeInfoResponse**](SchemaGetFieldTypeInfoResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getSchemaInfo

> SchemaInfoResponse getSchemaInfo(indexType, indexName)

Fetch the entire schema of the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.getSchemaInfo(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaInfoResponse**](SchemaInfoResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getSchemaName

> SchemaNameResponse getSchemaName(indexType, indexName)

Get the name of the schema used by the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.getSchemaName(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaNameResponse**](SchemaNameResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getSchemaSimilarity

> SchemaSimilarityResponse getSchemaSimilarity(indexType, indexName)

Get the default similarity configuration used by the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.getSchemaSimilarity(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaSimilarityResponse**](SchemaSimilarityResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getSchemaUniqueKey

> SchemaUniqueKeyResponse getSchemaUniqueKey(indexType, indexName)

Fetch the uniquekey of the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.getSchemaUniqueKey(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaUniqueKeyResponse**](SchemaUniqueKeyResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getSchemaVersion

> SchemaVersionResponse getSchemaVersion(indexType, indexName)

Fetch the schema version currently used by the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.getSchemaVersion(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaVersionResponse**](SchemaVersionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## getSchemaZkVersion

> SchemaZkVersionResponse getSchemaZkVersion(indexType, indexName, opts)

Fetch the schema version currently used by the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
let opts = {
  'refreshIfBelowVersion': -1 // Number | 
};
apiInstance.getSchemaZkVersion(indexType, indexName, opts, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 
 **refreshIfBelowVersion** | **Number**|  | [optional] [default to -1]

### Return type

[**SchemaZkVersionResponse**](SchemaZkVersionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## listCopyFields

> SchemaListCopyFieldsResponse listCopyFields(indexType, indexName)

List all copy-fields in the schema of the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.listCopyFields(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaListCopyFieldsResponse**](SchemaListCopyFieldsResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## listDynamicFields

> SchemaListDynamicFieldsResponse listDynamicFields(indexType, indexName)

List all dynamic-fields in the schema of the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.listDynamicFields(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaListDynamicFieldsResponse**](SchemaListDynamicFieldsResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## listSchemaFieldTypes

> SchemaListFieldTypesResponse listSchemaFieldTypes(indexType, indexName)

List all field types in the schema used by the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.listSchemaFieldTypes(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaListFieldTypesResponse**](SchemaListFieldTypesResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*


## listSchemaFields

> SchemaListFieldsResponse listSchemaFields(indexType, indexName)

List all non-dynamic fields in the schema of the specified core or collection

### Example

```javascript
import V2Api from 'v2_api';

let apiInstance = new V2Api.SchemaApi();
let indexType = new V2Api.IndexType(); // IndexType | 
let indexName = "indexName_example"; // String | 
apiInstance.listSchemaFields(indexType, indexName, (error, data, response) => {
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
 **indexType** | [**IndexType**](.md)|  | 
 **indexName** | **String**|  | 

### Return type

[**SchemaListFieldsResponse**](SchemaListFieldsResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: */*

