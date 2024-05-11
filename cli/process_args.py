import argparse
import sys
import os
from dotenv import load_dotenv
from crawler import base_crawler
from crawler import extended_crawler
from crawler import citations_crawler
from auxiliar import file


def process():
    """Function that processes the arguments passed to the crawler.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--c', type=str, nargs='+', help='List of the conference we want to get the papers from', required=True)
    parser.add_argument('--y', type=int, nargs='+', help='List of the years we want to get (from - to)', required=True)
    parser.add_argument('--extended', nargs='?', const='default_value', help='Flag to indicate if we want to use the basic crawler')
    parser.add_argument('--t', type=int, nargs='?', const='default_value', help='To change the number of threads used in the crawler')
    parser.add_argument('--no_key', nargs='?', const='default_value', help='Flag to indicate if we want to use the crawler without a Semantic Scholar API key')
    parser.add_argument('--citations', nargs='?', const='default_value', help='Flag to indicate if we want to use the citations crawler')
    parser.add_argument('--o', type=str, nargs='?', const='default_value', help='Output directory for the data')

    args = parser.parse_args()

    # --years
    if len(args.y) > 2 or len(args.y) < 1:
        sys.exit("Error: The --years argument must have one or 2 values")
    if len(args.y) > 1 and args.y[0] > args.y[1]:
        sys.exit("Error: The first value of --years must be lower than the second value")
    if len(args.y) == 1:
        args.y.append(args.y[0])

    # --c
    if len(args.c) < 1:
        sys.exit("Error: The --c argument must have at least one value")
    
    # --t
    if args.t is None:
        num_threads = 1
    else:
        num_threads = args.t

    # --no_key
    if args.no_key:
        api_key = None
        num_threads = 1
    else:
        api_key = file.api_key_in_env()


    if args.extended:
        if api_key is None and not args.no_key:
            sys.exit("Error: You must provide a Semantic Scholar API key to use the extended crawler or use the --no_key flag to use the crawler without an API key")
        if args.o:
            output_dir = args.o
        else:
            output_dir = './data/extended_crawler_data/'
        extended = extended_crawler.ExtendedCrawler(args.c, args.y, num_threads=num_threads, output_dir=output_dir)
        extended.crawl()
    elif args.citations:
        if args.o:
            output_dir = args.o
        else:
            output_dir = './data/citations_crawler_data/'
        citations = citations_crawler.CitationsCrawler(args.c, args.y, num_threads=num_threads, output_dir=output_dir)
        citations.crawl()
    else:
        if args.o:
            output_dir = args.o
        else:
            output_dir = './data/base_crawler_data/'
        base = base_crawler.BaseCrawler(args.c, args.y, num_threads=num_threads, output_dir=output_dir)
        base.crawl()