import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.cloud.aws_runtime import destroy_s3_stack, load_env_file


def main():
    load_env_file()
    destroy_s3_stack()


if __name__ == "__main__":
    main()
