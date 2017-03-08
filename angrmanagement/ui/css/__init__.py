

class CSS(object):

    css = """
QLabel[class=insn] {
    font: 10pt courier new;
    color: #000080;
}

QLabel[class=reg_viewer_label] {
    font: 10pt courier new;
    background-color: #ffffff;
}

QLabel[class=status_valid] {
    color: green;
}

QLabel[class=status_invalid] {
    color: red;
}

QFrame[class=insn_selected] {
    font: 10pt courier new;
    color: #000000;
    background-color: #efbfba;
}

QBlock {
    border: 1px solid black;
}

QBlockLabel {
    color: #0000ff;
}

QLabel[class=insn_addr] {
    font: 10pt courier new;
    color: black;
}

QLabel[class=insn_string] {
    font: 10pt courier new;
    color: gray;
    font-weight: bold;
}
"""

    @staticmethod
    def global_css():
        return CSS.css
