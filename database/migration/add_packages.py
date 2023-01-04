import datetime
import sqlite3
import logging


SCRIPT_INSERT_RELEASE = '''insert or replace into release (name, language, tag, package, version, date_epoch) values (?, ?, ?, ?, ?, ?)'''


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %X')

    db_path = 'c:/github_lab/azure-rest-api-specs-examples-db/examples.db'

    packages = [
        "azure-resourcemanager-appplatform",
        "azure-resourcemanager-appservice",
        "azure-resourcemanager-authorization",
        "azure-resourcemanager-cdn",
        "azure-resourcemanager-compute",
        "azure-resourcemanager-containerinstance",
        "azure-resourcemanager-containerregistry",
        "azure-resourcemanager-containerservice",
        "azure-resourcemanager-cosmos",
        "azure-resourcemanager-dns",
        "azure-resourcemanager-eventhubs",
        "azure-resourcemanager-keyvault",
        "azure-resourcemanager-monitor",
        "azure-resourcemanager-msi",
        "azure-resourcemanager-network",
        "azure-resourcemanager-privatedns",
        "azure-resourcemanager-redis",
        "azure-resourcemanager-resources",
        "azure-resourcemanager-search",
        "azure-resourcemanager-servicebus",
        "azure-resourcemanager-sql",
        "azure-resourcemanager-storage",
        "azure-resourcemanager-trafficmanager"
    ]

    version = "2.22.0"
    language = "java"

    date_epoch = int(datetime.datetime.now().timestamp())

    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA foreign_keys = 1')

        cursor = conn.cursor()

        for package in packages:
            tag = package + "_" + version
            name = "com.azure.resourcemanager:" + package + ":" + version
            cursor.execute(SCRIPT_INSERT_RELEASE, (name, language, tag, package, version, date_epoch))

        conn.commit()


if __name__ == '__main__':
    main()
