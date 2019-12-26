def correct_idd(idd):
    # MaterialProperty:GlazingSpectralData extensible info
    # begin-extensible should appear at field 1 but it appears a lot later
    td = idd.table_descriptors["materialproperty_glazingspectraldata"]
    fd = td.get_field_descriptor(1)
    fd.append_tag("begin-extensible")

    if idd.version < (9, 2, 0):
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

    # Meter:Custom add retain case
    fd = idd.table_descriptors["meter_custom"].get_field_descriptor(2)
    fd.append_tag("retaincase")

    if idd.version == (9, 0, 1):  # was corrected in 9.1.0
        # Fan:SystemModel add reference
        fd = idd.table_descriptors["fan_systemmodel"].get_field_descriptor(0)
        fd.append_tag("reference", "FansCVandVAV")

    if idd.version >= (8, 6, 0):
        # ZoneHvac:CoolingPanel:RadiantConvective:Water
        fd = idd.table_descriptors["zonehvac_coolingpanel_radiantconvective_water"].get_field_descriptor(0)
        fd.append_tag("reference-class-name", "validBranchEquipmentTypes")
        fd.append_tag("reference", "validBranchEquipmentNames")
