import unittest

from main import process_java_example_content


class TestProcess(unittest.TestCase):

    def test_process_java_example(self):
        java_code = '''
// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.
// Code generated by Microsoft (R) AutoRest Code Generator.

package com.azure.resourcemanager.datafactory.generated;

import com.azure.core.management.serializer.SerializerFactory;
import com.azure.core.util.Context;
import com.azure.core.util.serializer.SerializerEncoding;
import com.azure.resourcemanager.datafactory.models.AzureBlobDataset;
import com.azure.resourcemanager.datafactory.models.DatasetResource;
import com.azure.resourcemanager.datafactory.models.LinkedServiceReference;
import com.azure.resourcemanager.datafactory.models.ParameterSpecification;
import com.azure.resourcemanager.datafactory.models.ParameterType;
import com.azure.resourcemanager.datafactory.models.TextFormat;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/** Samples for Datasets CreateOrUpdate. */
public final class DatasetsCreateOrUpdateSamples {
    /*
     * x-ms-original-file: specification/datafactory/resource-manager/Microsoft.DataFactory/stable/2018-06-01/examples/Datasets_Create.json
     */
    /**
     * Sample code: Datasets_Create.
     *
     * @param manager Entry point to DataFactoryManager.
     */
    public static void datasetsCreate(com.azure.resourcemanager.datafactory.DataFactoryManager manager)
        throws IOException {
        manager
            .datasets()
            .define("exampleDataset")
            .withExistingFactory("exampleResourceGroup", "exampleFactoryName")
            .withProperties(
                new AzureBlobDataset()
                    .withLinkedServiceName(new LinkedServiceReference().withReferenceName("exampleLinkedService"))
                    .withParameters(
                        mapOf(
                            "MyFileName",
                            new ParameterSpecification().withType(ParameterType.STRING),
                            "MyFolderPath",
                            new ParameterSpecification().withType(ParameterType.STRING)))
                    .withFolderPath(
                        SerializerFactory
                            .createDefaultManagementSerializerAdapter()
                            .deserialize(
                                "{\"type\":\"Expression\",\"value\":\"@dataset().MyFolderPath\"}",
                                Object.class,
                                SerializerEncoding.JSON))
                    .withFileName(
                        SerializerFactory
                            .createDefaultManagementSerializerAdapter()
                            .deserialize(
                                "{\"type\":\"Expression\",\"value\":\"@dataset().MyFileName\"}",
                                Object.class,
                                SerializerEncoding.JSON))
                    .withFormat(new TextFormat()))
            .create();
    }

    /*
     * x-ms-original-file: specification/datafactory/resource-manager/Microsoft.DataFactory/stable/2018-06-01/examples/Datasets_Update.json
     */
    /**
     * Sample code: Datasets_Update.
     *
     * @param manager Entry point to DataFactoryManager.
     */
    public static void datasetsUpdate(com.azure.resourcemanager.datafactory.DataFactoryManager manager)
        throws IOException {
        DatasetResource resource =
            manager
                .datasets()
                .getWithResponse("exampleResourceGroup", "exampleFactoryName", "exampleDataset", null, Context.NONE)
                .getValue();
        resource
            .update()
            .withProperties(
                new AzureBlobDataset()
                    .withDescription("Example description")
                    .withLinkedServiceName(new LinkedServiceReference().withReferenceName("exampleLinkedService"))
                    .withParameters(
                        mapOf(
                            "MyFileName",
                            new ParameterSpecification().withType(ParameterType.STRING),
                            "MyFolderPath",
                            new ParameterSpecification().withType(ParameterType.STRING)))
                    .withFolderPath(
                        SerializerFactory
                            .createDefaultManagementSerializerAdapter()
                            .deserialize(
                                "{\"type\":\"Expression\",\"value\":\"@dataset().MyFolderPath\"}",
                                Object.class,
                                SerializerEncoding.JSON))
                    .withFileName(
                        SerializerFactory
                            .createDefaultManagementSerializerAdapter()
                            .deserialize(
                                "{\"type\":\"Expression\",\"value\":\"@dataset().MyFileName\"}",
                                Object.class,
                                SerializerEncoding.JSON))
                    .withFormat(new TextFormat()))
            .apply();
    }

    @SuppressWarnings("unchecked")
    private static <T> Map<String, T> mapOf(Object... inputs) {
        Map<String, T> map = new HashMap<>();
        for (int i = 0; i < inputs.length; i += 2) {
            String key = (String) inputs[i];
            T value = (T) inputs[i + 1];
            map.put(key, value);
        }
        return map;
    }
}
'''
        java_examples = process_java_example_content(java_code.splitlines(keepends=True),
                                                     'DatasetsCreateOrUpdateSamples')

        self.assertEqual(2, len(java_examples))

        self.assertEqual('specification/datafactory/resource-manager/Microsoft.DataFactory/stable/2018-06-01/examples-java', java_examples[0].target_dir)
        self.assertEqual('Datasets_Create', java_examples[0].target_filename)
        self.assertTrue('public final class Main {' in java_examples[0].content)
        self.assertTrue('x-ms-original-file: specification/datafactory/resource-manager/Microsoft.DataFactory/stable/2018-06-01/examples/Datasets_Create.json' in java_examples[0].content)
        self.assertTrue('public static void datasetsCreate(com.azure.resourcemanager.datafactory.DataFactoryManager manager)' in java_examples[0].content)

        self.assertTrue('public final class Main {' in java_examples[1].content)
        self.assertTrue('x-ms-original-file: specification/datafactory/resource-manager/Microsoft.DataFactory/stable/2018-06-01/examples/Datasets_Update.json' in java_examples[1].content)
        self.assertTrue('public static void datasetsUpdate(com.azure.resourcemanager.datafactory.DataFactoryManager manager)' in java_examples[1].content)

    def test_process_java_example_newline(self):
        java_code = '''
// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.
// Code generated by Microsoft (R) AutoRest Code Generator.

package com.azure.resourcemanager.streamanalytics.generated;

import com.azure.resourcemanager.streamanalytics.models.ClusterSku;
import com.azure.resourcemanager.streamanalytics.models.ClusterSkuName;
import java.util.HashMap;
import java.util.Map;

/**
 * Samples for Clusters CreateOrUpdate.
 */
public final class ClustersCreateOrUpdateSamples {
    /*
     * x-ms-original-file:
     * specification/streamanalytics/resource-manager/Microsoft.StreamAnalytics/preview/2020-03-01-preview/examples/
     * Cluster_Create.json
     */
    /**
     * Sample code: Create a new cluster.
     * 
     * @param manager Entry point to StreamAnalyticsManager.
     */
    public static void createANewCluster(com.azure.resourcemanager.streamanalytics.StreamAnalyticsManager manager) {
        manager.clusters().define("An Example Cluster").withRegion("North US").withExistingResourceGroup("sjrg")
            .withTags(mapOf("key", "fakeTokenPlaceholder"))
            .withSku(new ClusterSku().withName(ClusterSkuName.DEFAULT).withCapacity(48)).create();
    }

    // Use "Map.of" if available
    @SuppressWarnings("unchecked")
    private static <T> Map<String, T> mapOf(Object... inputs) {
        Map<String, T> map = new HashMap<>();
        for (int i = 0; i < inputs.length; i += 2) {
            String key = (String) inputs[i];
            T value = (T) inputs[i + 1];
            map.put(key, value);
        }
        return map;
    }
}
'''
        java_examples = process_java_example_content(java_code.splitlines(keepends=True),
                                                     'ClustersCreateOrUpdateSamples')

        self.assertEqual(1, len(java_examples))

        self.assertTrue('public final class Main {' in java_examples[0].content)
        self.assertEqual('specification/streamanalytics/resource-manager/Microsoft.StreamAnalytics/preview/2020-03-01-preview/examples-java', java_examples[0].target_dir)
        self.assertEqual('Cluster_Create', java_examples[0].target_filename)
