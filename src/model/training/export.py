from src.data_pipeline.dataset import *


def main():
    conn = connect_db()
    build_export_table(conn)
    export_train_df_to_parquet(conn)

if __name__ == "__main__":
    main()
