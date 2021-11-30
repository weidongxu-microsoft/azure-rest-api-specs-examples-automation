import unittest
from os import path

from modules import JavaExample
from package import MavenPackage


class TestMavenPackage(unittest.TestCase):

    def test_correct_example(self):
        tmp_path = path.abspath('.')
        maven_package = MavenPackage(tmp_path, 'azure-resourcemanager-postgresqlflexibleserver', '1.0.0-beta.3')
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
        result = maven_package.compile([JavaExample('', '', code)])
        self.assertTrue(result)

    def test_incorrect_example(self):
        tmp_path = path.abspath('.')
        maven_package = MavenPackage(tmp_path, 'azure-resourcemanager-postgresqlflexibleserver', '1.0.0-beta.3')
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
        result = maven_package.compile([JavaExample('', '', code)])
        self.assertFalse(result)
