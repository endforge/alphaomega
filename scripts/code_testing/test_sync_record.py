from scripts.sync.sync_record import SyncRecord


def main():

    record = SyncRecord()

    print(type(record))
    print(record._sections)


if __name__ == "__main__":
    main()