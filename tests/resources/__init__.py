import os

root_path = os.path.dirname(__file__)


def p(name, ext, is_dir=False):
    resource_name = name if is_dir else f"{name}.{ext}"
    return os.path.join(root_path, ext, resource_name)


class Resources:
    class Epw:
        san_fransisco_tmy3 = p("san_fransisco_tmy3", "epw")

    class SimulationsOutputs:
        one_zone_uncontrolled = p("one_zone_uncontrolled", "simulations_outputs", is_dir=True)


if __name__ == "__main__":
    # this code generates automatically Resources class
    def _to_camel(file_name):
        capitalize = True
        camel = ""
        for letter in file_name:
            if letter == "_":
                capitalize = True
                continue
            camel += letter.upper() if capitalize else letter
            capitalize = False

        return camel

    s = "class Resources:\n"
    for _ext in os.listdir(root_path):
        _dir_path = os.path.join(root_path, _ext)
        if os.path.isfile(_dir_path) or _ext == "__pycache__":
            continue

        s += f"    class {_to_camel(_ext)}:\n"
        for _file_name in os.listdir(_dir_path):
            _is_dir = ", is_dir=True" if  os.path.isdir(os.path.join(_dir_path, _file_name)) else ""
            _base, _ = os.path.splitext(_file_name)
            s += f'        {_base} = p("{_base}", "{_ext}"{_is_dir})\n'
        s += "\n"

    print(s)
