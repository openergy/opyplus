import os
import shutil

import oplus as op

if __name__ == "__main__":
    eplus_path = os.path.join(
        op.CONF.eplus_base_dir_path,
        "ExampleFiles",
        "1ZoneEvapCooler.idf"
    )

    # idf = op.Epm(check_required=False)
    # bsd = idf.BuildingSurface_Detailed.add(name="toto")
    # bsd.view_factor_to_ground = .5
    # print(bsd)

    local_eplus_path = "eplus.idf"
    shutil.copy2(eplus_path, local_eplus_path)
    epm = op.Epm(local_eplus_path)

    path = "temp.idf"
    epm.to_idf(path)
    epm = op.Epm(path)
    print(epm.to_idf())


    # for i in range(3):
    #     with open(path, "w") as f:
    #         f.write(epm.to_idf())
    #         epm = op.Epm(path)
    # print(epm.to_idf())
    # epm = op.Epm()

    # print([epm])
    # print(epm)
    # print(epm.get_info())

    # bsd_table = epm.BuildingSurface_Detailed
    # print([bsd_table])
    # print(bsd_table)
    # print(bsd_table.get_info())

    # bsd = bsd_table.select()[0]
    # print([bsd])
    # print(bsd)
    # print(bsd.get_info())

    # zone = epm.Zone.add(name="Test")
    # print(epm.to_idf())
    #
    # epm.set_defaults()
    # print(epm.to_idf())
    # print(zone._data)

    #
    # #print(zone.get_info())
    #
    # sch = epm.Schedule_Compact.add(name="sch")
    # #print(sch.get_info())
    #
    # zl = epm.ZoneList.add(name="zl")
    # #print(zl)
    # #print(zl.get_info())
    #
    # eq = epm.ZoneHVAC_EquipmentList.add(name="eq")
    # eq2 = epm.ZoneHVAC_EquipmentList.add(name="eq")
    # print(eq.get_info())
