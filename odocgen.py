import io as __io
import sys as __sys
import textwrap as __textwrap


__default_file_name = "doc"
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
                __file_content += __textwrap.indent(__s.text, "\t") + "\n"

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

# class Documentation:
#     def __init__(self):
#         self._steps = [] # step: {category: "header", options:},
#
#     def add_header(self, level, name):
#         self._steps.append(dict(
#             category="header",
#             name=name,
#             level=level
#         ))
#
#     def __call__(self, run=True, with_output=True, globalize=True):
#         if with_output and not run:
#             raise ValueError("can't ask with_output without run")
#
#         def wrapper(fct):
#             self._steps.append(dict(
#                 category="function",
#                 fct=fct,
#                 run=run,
#                 with_output=with_output,
#                 globalize=globalize
#             ))
#         return wrapper
#
#     def generate(self):
#         content = ""
#         for step in self._steps:
#             if step["category"] == "header":
#                 content += "#"*step["level"] + " " + step["name"] + "\n\n"
#
#             elif step["category"] == "function":
#                 # get source
#                 fct_content = inspect.getsource(step["fct"])
#
#                 # check no return
#                 assert "return" not in fct_content
#
#                 # append return locals()
#                 fct_content += "    return locals()\n"
#
#                 # strip decorator
#                 fct_content = "\n".join(fct_content.strip("\n")[1:])
#
#                 # run if asked
#                 output_content = ""
#                 stdout = sys.stdout
#                 out = io.StringIO()
#                 sys.stdout = out
#
#                 try:
#                     print(fct_content)
#                     r = exec(fct_content)()
#                     output_content += out.getvalue()
#                 finally:
#                     sys.stdout = stdout
#
#                 # globalize if asked
#                 if step["globalize"]:
#                     # todo: check no clash with globals
#                     for k, v in r.items():
#                         globals()[k] = v
#
#                 # split to rows
#                 fct_content_l = fct_content.split("\n")
#
#                 # strip rows and concat
#                 fct_content = "\n".join(fct_content_l[2:-2])
#
#                 # append
#                 content += fct_content + "\n\n"
#
#                 # add output if asked
#                 if step["with_output"] and len(output_content) > 0:
#                     content += "**Out:**\n"
#                     content += textwrap.indent(output_content, "\t")
#                     content += "\n\n"
#
#             else:
#                 raise KeyError
#         return content

