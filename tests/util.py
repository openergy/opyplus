from opyplus import CONF

TESTED_EPLUS_VERSIONS = [
    # (8, 5, 0),
    # (8, 6, 0),
    # (9, 0, 1)  # todo: manage 9.2.0
    (9, 2, 0),  # todo: manage 9.2.0
    # (22, 1, 0),
]


def iter_eplus_versions(test_case):
    for eplus_version in TESTED_EPLUS_VERSIONS:
        with test_case.subTest(eplus_version=eplus_version):
            CONF.eplus_version = eplus_version
            yield eplus_version


def assert_epw_equal(expected_content, given_content):
    expected_content_l2 = [[cell.strip() for cell in row.split(",")] for row in expected_content.split("\n")]
    given_content_l2 = [[cell.strip() for cell in row.split(",")] for row in given_content.split("\n")]

    for r, expected_row in enumerate(expected_content_l2):
        for c, expected_cell in enumerate(expected_row):
            try:
                assert float(expected_cell) == float(given_content_l2[r][c])
            except ValueError:
                assert expected_cell == given_content_l2[r][c], f"Cells differ -> row: {r}, column: {c}"
