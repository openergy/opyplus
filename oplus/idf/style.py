class IdfStyle:
    head_key = None
    chapter_key = None
    record_key = None
    tail_record_key = None
    tail_type = None

    def get_chapter_title(self, content):
        # default: oplus
        length = 100
        s = self.get_chapter_comment("#" * length)
        first_length = length // 2 - len(content) // 2 - 1
        middle_string = "#" * first_length
        middle_string += " " + content.upper() + " "
        middle_string += "#" * (length - first_length - len(content) - 2)
        s += self.get_chapter_comment(middle_string)
        s += self.get_chapter_comment("#" * length)
        return s

    def get_record_comment(self, comment, line_jump=True):
        prefix = "!" + self.record_key
        if self.record_key != " ":
            prefix += " "
        s = prefix + comment
        if line_jump:
            s += "\n"
        return s

    def get_tail_record_comment(self, comment, line_jump=True):
        prefix = "!" + self.tail_record_key
        if self.tail_record_key != " ":
            prefix += " "
        s = prefix + comment
        if line_jump:
            s += "\n"
        return s

    def get_head_comment(self, comment, line_jump=True):
        prefix = "!" + self.head_key
        if self.head_key != " ":
            prefix += " "
        s = prefix + comment
        if line_jump:
            s += "\n"
        return s

    def get_chapter_comment(self, comment, line_jump=True):
        prefix = "!" + self.chapter_key
        if self.chapter_key != " ":
            prefix += " "
        s = prefix + comment
        if line_jump:
            s += "\n"
        return s


class OplusIdfStyle(IdfStyle):
    head_key = " "
    chapter_key = "#"
    record_key = "-"
    tail_record_key = "-"
    tail_type = "after"


class DefaultWriteIdfStyle(IdfStyle):
    head_key = " "
    chapter_key = " "
    record_key = " "
    tail_record_key = " "
    tail_type = "after"


class DesignBuilderIdfStyle(IdfStyle):
    head_key = " "
    chapter_key = "#"
    record_key = "-"
    tail_record_key = " "
    tail_type = "before"


class AshraeIdfStyle(IdfStyle):
    head_key = " "
    chapter_key = " -"
    record_key = "  -"
    tail_record_key = " "
    tail_type = "before"

    def get_chapter_title(self, content):
        s = " "*2 + "="*11 + " "*2
        s += "ALL OBJECTS IN CLASS: " + content.upper()
        s += " " + "="*11

        return self.get_chapter_comment(s)


style_library = {
    None: None,
    "oplus": OplusIdfStyle(),
    "ASHRAE": AshraeIdfStyle(),
    "default write": DefaultWriteIdfStyle(),
    "design builder": DesignBuilderIdfStyle(),
}
