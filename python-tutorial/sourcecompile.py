
import sourcecodegen

def compile_via_source(tree, code_filename, mode):
    assert mode == "exec", mode
    sources = sourcecodegen.generate_code(tree)
    return compile(sources, code_filename, mode)
