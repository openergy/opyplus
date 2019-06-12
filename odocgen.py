"""
#@: will appear in markdown
##: will not appear in markdown

Everything else appears (including prints), except:
 - everything before first markdown comment
 - everything after last markdown comment
"""


import io as __io
import sys as __sys
import textwrap as __textwrap


__default_file_name = "doc-users"
__file_name = __default_file_name if len(__sys.argv) == 1 else __sys.argv[1]


class __Section:
    def __init__(self, category):
        """
        Parameters
        ----------
        category: str,
            code, markdown
        """
        self.category = category
        self.text = ""


__sections = []

with open(__file_name + ".py") as f:
    for __row in f:
        # find category
        if __row.strip()[:2] == "#@":  # markdown
            current_category = "markdown"
            current_text = __row.strip(" ")[2:]
        elif __row.strip()[:2] == "##":  # neutral
            continue
        else:
            current_category = "code"
            current_text = __row

        # create section if needed (initialization or category change)
        if (len(__sections) == 0) or (__sections[-1].category != current_category):
            __sections.append(__Section(current_category))

        # complete last section
        __sections[-1].text += current_text

__file_content = ""
__sections__nb = len(__sections)
__run_tear_down = False

try:
    try:
        for __i, __s in enumerate(__sections):
            if __s.category == "code":    # code
                # quit if last section and code
                if (__i == (__sections__nb-1)) and (__s.category == "code"):
                    __run_tear_down = True
                    break

                # prepare run
                __output_content = ""
                __stdout = __sys.stdout
                __out = __io.StringIO()
                __sys.stdout = __out

                try:
                    # run
                    __r = exec(__s.text)
                    __output_content += __out.getvalue()
                finally:
                    __sys.stdout = __stdout

                # continue if first section and code
                if __i == 0 and __s.category == "code":
                    continue

                # write code
                __file_content += "\n" + __textwrap.indent(__s.text, "\t") + "\n"

                # write output
                __output_content = __out.getvalue()
                if len(__output_content) > 0:
                    __file_content += "*out:*\n\n"
                    __file_content += __textwrap.indent(__output_content, "\t") + "\n"

            else:  # markdown
                __file_content += __s.text
    finally:
        # run tear down if needed
        if __run_tear_down:
            exec(__sections[-1].text)

finally:
    with open(__file_name + ".md", "w") as __f:
        __f.write(__file_content)
