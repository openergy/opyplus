import os

from oplus import Epm, CONF

if __name__ == "__main__":
    idf = Epm(os.path.join(
        CONF.eplus_base_dir_path,
        "ExampleFiles",
        "1ZoneEvapCooler.idf")
    )
    print(idf.to_idf())

    pass