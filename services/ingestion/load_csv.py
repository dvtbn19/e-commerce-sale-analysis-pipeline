from services.ingestion.loader import ingest_amazon_sales


def main():
    result = ingest_amazon_sales()

    print("\nIngestion result:")
    print(result)


if __name__ == "__main__":
    main()