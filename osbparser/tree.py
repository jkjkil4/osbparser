from typing import Iterable, Generator

from osbparser.exception import IndentError

Tree = tuple[tuple[int, str], list['Tree']]


def lines2tree(root_name: str, lines: Iterable[str]) -> Tree:
    root = ((0, root_name), [])
    stack: list[Tree] = [root]
    for lineno, line in enumerate(lines, start=1):
        line_wo_lspace = line.lstrip(' ')
        if not line_wo_lspace or line_wo_lspace.startswith('//'):
            continue
        spaces = len(line) - len(line_wo_lspace)
        if line_wo_lspace.startswith('['):
            spaces -= 1

        child = ((lineno, line_wo_lspace), [])

        pop_times = len(stack) - 2 - spaces
        if pop_times < 0:
            raise IndentError(f'{spaces} space(s) at line {lineno}.')

        # Equivalent to:
        # if spaces == len(stack) - 4:    # step out
        #     stack.pop()
        #     stack.pop()
        # elif spaces == len(stack) - 3:  # next
        #     stack.pop()
        # elif spaces == len(stack) - 2:  # step in
        #     pass
        for _ in range(pop_times):
            stack.pop()

        stack[-1][1].append(child)
        stack.append(child)

    return root


def file2tree(file_path: str, root_name: str | None = None) -> Tree:
    def gen_lines() -> Generator[str, None, None]:
        with open(file_path) as file:
            while line := file.readline():
                yield line.rstrip('\n')

    if root_name is None:
        root_name = file_path

    return lines2tree(root_name, gen_lines())


def str2tree(text: str, root_name: str = '') -> Tree:
    return lines2tree(root_name, text.split('\n'))
