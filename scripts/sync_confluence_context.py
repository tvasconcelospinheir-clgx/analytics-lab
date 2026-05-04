from pathlib import Path

from src.connectors.confluence import ConfluenceClient, write_context_files


def main() -> None:
    client = ConfluenceClient()
    pages = client.fetch_pages()

    output_dir = Path(__file__).resolve().parent.parent / "references" / "confluence"
    result = write_context_files(pages, output_dir)

    print("Confluence context sync complete")
    print(f"  pages: {result['page_count']}")
    print(f"  output: {result['output_dir']}")


if __name__ == "__main__":
    main()
