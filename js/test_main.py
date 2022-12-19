import unittest
from main import get_js_example_method, get_sample_version, get_module_relative_path, break_down_aggregated_js_example, create_js_examples, Release


class TestMain(unittest.TestCase):

    def test_get_sample_version(self):
        self.assertEqual('v3', get_sample_version('3.0.0'))
        self.assertEqual('v3-beta', get_sample_version('3.0.0-beta.3'))

    def test_get_js_example_method(self):
        code = '''const { StorSimpleManagementClient } = require("@azure/arm-storsimple1200series");
const { DefaultAzureCredential } = require("@azure/identity");

/**
 * This sample demonstrates how to Upload Vault Cred Certificate.
Returns UploadCertificateResponse
 *
 * @summary Upload Vault Cred Certificate.
Returns UploadCertificateResponse
 * x-ms-original-file: specification/storSimple1200Series/resource-manager/Microsoft.StorSimple/stable/2016-10-01/examples/ManagersUploadRegistrationCertificate.json
 */
async function managersUploadRegistrationCertificate() {
  const subscriptionId = "4385cf00-2d3a-425a-832f-f4285b1c9dce";
  const certificateName = "windows";
  const resourceGroupName = "ResourceGroupForSDKTest";
  const managerName = "ManagerForSDKTest2";
  const uploadCertificateRequestrequest = {
    authType: "AzureActiveDirectory",
    certificate:
      "MIIC3TCCAcWgAwIBAgIQEr0bAWD6wJtA4LIbZ9NtgzANBgkqhkiG9w0BAQUFADAeMRwwGgYDVQQDExNXaW5kb3dzIEF6dXJlIFRvb2xzMB4XDTE4MDkxMDE1MzY0MFoXDTE4MDkxMzE1NDY0MFowHjEcMBoGA1UEAxMTV2luZG93cyBBenVyZSBUb29sczCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANUsKkz2Z4fECKMyNeLb9v3pr1XF4dVe+MITDtgphjl81ng190Y0IHgCVnh4YjfplUSpMk/1xii0rI5AAPwoz3ze2qRPtnwCiTaoVLkUe6knNRPzrRvVXHB81J0/14MO0lwdByHhdccRcVJZPLt5724t4aQny82v2AayJdDDkBBWNlpcqPy6n3sygP00THMPP0O3sFqy924eHqoDj3qSw79/meaZBJt9S5odPuFoskxjHuI4lM6BmK1Ql7p8Wo9/GhTOIoMz81orKPHRDleLjutwL4mb6NnhI5rfT/MxnHD6m82c4YYqiZC3XiTyJWVCkWkp7PK92OdRp6FA87rdKDMCAwEAAaMXMBUwEwYDVR0lBAwwCgYIKwYBBQUHAwIwDQYJKoZIhvcNAQEFBQADggEBAIYlezVU68TuEblkn06vM5dfzSmHKJOQgW61nDlLnyKrmSJtzKZLCAswTE2VyJHwKNdZgW15coJFINjWBLWcLr0/GjNV4u3Z+UL3NhBFQd5xuMtKsIhuoscKtyk0JHQXpBvHNmOUCobfQfOBQfTVC7kmyWdtlGztFUVxD28s6S5gMb1FEWWN68NOOJ3/ZhaTbUEM54yw8Hk8/f0L/Zn/7BYHUyWWA3KStAaYn89C/ZFF+952ark2VaKGIjBRQzgrJEIR8dI4r46I3DoEfzGPESKvQPvVLhOX84RG0PLPOtnRbHBVew1Nh3HE9kgCubkPKK+NPWE9IHZPoRmOTWBe+zU=",
    contractVersion: "V2012_12",
  };
  const credential = new DefaultAzureCredential();
  const client = new StorSimpleManagementClient(credential, subscriptionId);
  const result = await client.managers.uploadRegistrationCertificate(
    certificateName,
    resourceGroupName,
    managerName,
    uploadCertificateRequestrequest
  );
  console.log(result);
}

managersUploadRegistrationCertificate().catch(console.error);
'''

        lines = code.splitlines(keepends=True)

        js_example_method = get_js_example_method(lines, 0)
        self.assertEqual(3, js_example_method.line_start)
        self.assertIsNotNone(js_example_method.line_end)

    def test_break_down_aggregated_js_example(self):
        code = '''const { StorageManagementClient } = require("@azure/arm-storage");
const { DefaultAzureCredential } = require("@azure/identity");

/**
 * This sample demonstrates how to Gets properties of a specified container.
 *
 * @summary Gets properties of a specified container.
 * x-ms-original-file: specification/storage/resource-manager/Microsoft.Storage/stable/2022-09-01/examples/BlobContainersGetWithAllowProtectedAppendWritesAll.json
 */
async function getBlobContainersGetWithAllowProtectedAppendWritesAll() {
  const subscriptionId = "{subscription-id}";
  const resourceGroupName = "res9871";
  const accountName = "sto6217";
  const containerName = "container1634";
  const credential = new DefaultAzureCredential();
  const client = new StorageManagementClient(credential, subscriptionId);
  const result = await client.blobContainers.get(resourceGroupName, accountName, containerName);
  console.log(result);
}

getBlobContainersGetWithAllowProtectedAppendWritesAll().catch(console.error);

/**
 * This sample demonstrates how to Gets properties of a specified container.
 *
 * @summary Gets properties of a specified container.
 * x-ms-original-file: specification/storage/resource-manager/Microsoft.Storage/stable/2022-09-01/examples/BlobContainersGet.json
 */
async function getContainers() {
  const subscriptionId = "{subscription-id}";
  const resourceGroupName = "res9871";
  const accountName = "sto6217";
  const containerName = "container1634";
  const credential = new DefaultAzureCredential();
  const client = new StorageManagementClient(credential, subscriptionId);
  const result = await client.blobContainers.get(resourceGroupName, accountName, containerName);
  console.log(result);
}

getContainers().catch(console.error);
'''

        lines = code.splitlines(keepends=True)

        aggregated_js_example = break_down_aggregated_js_example(lines)
        self.assertEqual(2, len(aggregated_js_example.methods))

        self.assertEqual('* This sample demonstrates how to Gets properties of a specified container.', aggregated_js_example.methods[0].content[1].strip())
        self.assertEqual('async function getBlobContainersGetWithAllowProtectedAppendWritesAll() {', aggregated_js_example.methods[0].content[6].strip())
        self.assertEqual('getBlobContainersGetWithAllowProtectedAppendWritesAll().catch(console.error);', aggregated_js_example.methods[0].content[-1].strip())

        self.assertEqual('async function getContainers() {', aggregated_js_example.methods[1].content[6].strip())
        self.assertEqual('getContainers().catch(console.error);', aggregated_js_example.methods[1].content[-1].strip())

    @unittest.skip
    def test_get_module_relative_path(self):
        sdk_path = 'c:/github/azure-sdk-for-js'
        sdk_name = 'mysql-flexible'
        module_relative_path = get_module_relative_path(sdk_name, sdk_path)
        self.assertEqual('sdk/mysql/azure-mysql-flexible', module_relative_path)

    @unittest.skip
    def test_create_js_examples(self):
        release = Release('@azure/arm-policyinsights_6.0.0-beta.1',
                          '@azure/arm-policyinsights',
                          '6.0.0-beta.1',
                          'policyinsights')
        js_module = f'{release.package}@{release.version}'
        sdk_examples_path = 'c:/github/azure-rest-api-specs-examples'
        js_examples_path = 'c:/github/azure-sdk-for-js/sdk/policyinsights/arm-policyinsights/samples/v6-beta/javascript'
        succeeded, files = create_js_examples(release, js_module, sdk_examples_path, js_examples_path)
        self.assertTrue(succeeded)
