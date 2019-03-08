import os

from oplus import Idf, CONF

if __name__ == "__main__":
    idf = Idf(os.path.join(
        CONF.eplus_base_dir_path,
        "ExampleFiles",
        "1ZoneEvapCooler.idf")
    )
    # print(idf.to_str())

