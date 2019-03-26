from oplus import CONF


def correct_idd(idd):
    # MaterialProperty:GlazingSpectralData extensible info
    # begin-extensible should appear at field 1 but it appears a lot later
    td = idd.table_descriptors["materialproperty_glazingspectraldata"]
    fd = td.get_field_descriptor(1)
    fd.append_tag("begin-extensible")

    # Table:MultiVariableLookup extensible info
    # extensible cycle_len should be 1 (not 20), cycle_start should be 20 (not 22)
    td = idd.table_descriptors["table_multivariablelookup"]
    del td.tags["extensible:20"]
    td.add_tag("extensible:1")
    fd = td.get_field_descriptor(20)
    fd.append_tag("begin-extensible")

    # EnergyManagementSystem:Sensor add retain case
    fd = idd.table_descriptors["energymanagementsystem_sensor"].get_field_descriptor(2)
    fd.append_tag("retaincase")

    # Output:Variable add retain case
    fd = idd.table_descriptors["output_variable"].get_field_descriptor(1)
    fd.append_tag("retaincase")

    if CONF.eplus_version >= (9, 0, 1):
        # Fan:SystemModel add reference
        fd = idd.table_descriptors["fan_systemmodel"].get_field_descriptor(0)
        fd.append_tag("reference", "FansCVandVAV")
