import cli.process_args as cli
from log import log_config

def main():
    log_config.log_config('./log/log_file.log')
    cli.process()


if __name__ == "__main__":
    main()