import json
from xml.etree import ElementTree


def write_file(fpath, content):
    with open(fpath, 'w') as f:
        if isinstance(content, dict):
            json.dump(content, f, indent=2)
        elif isinstance(content, list):
            f.writelines(content)
        else:
            f.write(content)


def pretty_xml(root):
    root_str = ElementTree.tostring(root)
    from xml.dom import  minidom
    pretty_str = minidom.parseString(root_str).toprettyxml()
    return pretty_str
