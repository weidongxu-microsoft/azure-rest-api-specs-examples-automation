import unittest
import os
from os import path
import shutil

from package import MavenPackage


class TestMavenPackage(unittest.TestCase):

    def test_correct_sample(self):
        maven_path = path.abspath('./maven')
        try:
            os.makedirs(maven_path, exist_ok=True)
            maven_package = MavenPackage(maven_path, 'azure-resourcemanager-postgresqlflexibleserver', '1.0.0-beta.3')
            code = '''import com.azure.core.util.Context;
import com.azure.resourcemanager.postgresqlflexibleserver.models.NameAvailabilityRequest;
/** Samples for CheckNameAvailability Execute. */
public final class Main {
    /**
     * Sample code: NameAvailability.
     *
     * @param manager Entry point to PostgreSqlManager.
     */
    public static void nameAvailability(com.azure.resourcemanager.postgresqlflexibleserver.PostgreSqlManager manager) {
        manager
            .checkNameAvailabilities()
            .executeWithResponse(
                new NameAvailabilityRequest().withName("name1").withType("Microsoft.DBforPostgreSQL/flexibleServers"),
                Context.NONE);
    }
}'''
            result = maven_package.test_example(code)
            self.assertEqual(0, result.returncode)
        finally:
            shutil.rmtree(maven_path, ignore_errors=True)

    def test_incorrect_sample(self):
        maven_path = path.abspath('./maven')
        try:
            os.makedirs(maven_path, exist_ok=True)
            maven_package = MavenPackage(maven_path, 'azure-resourcemanager-postgresqlflexibleserver', '1.0.0-beta.3')
            # code missing "import"
            code = '''/** Samples for CheckNameAvailability Execute. */
public final class Main {
    /**
     * Sample code: NameAvailability.
     *
     * @param manager Entry point to PostgreSqlManager.
     */
    public static void nameAvailability(com.azure.resourcemanager.postgresqlflexibleserver.PostgreSqlManager manager) {
        manager
            .checkNameAvailabilities()
            .executeWithResponse(
                new NameAvailabilityRequest().withName("name1").withType("Microsoft.DBforPostgreSQL/flexibleServers"),
                Context.NONE);
    }
}'''
            result = maven_package.test_example(code)
            self.assertNotEqual(0, result.returncode)
        finally:
            shutil.rmtree(maven_path, ignore_errors=True)
