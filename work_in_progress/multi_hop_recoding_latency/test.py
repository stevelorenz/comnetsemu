import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "--recode_node",
        type=int,
        nargs="+",
        default= [0,0,0],
        choices=[0,1],
        help="choice which node to run recode, if not recodes,type 0, if wants to recode, type 1"
    )

    args=parser.parse_args()
    print(args.recode_node)