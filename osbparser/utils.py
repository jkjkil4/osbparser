from typing import TypeVar

T = TypeVar('T')


def get_first_part(text: str) -> str:
    '''
    Get the first part of ``text.split(',')``.

    Assuming the first part does't contain the quote symbol ``"``.
    '''
    comma_idx = text.find(',')
    return text if comma_idx == -1 else text[:comma_idx]


def split_parts(text: str) -> list[str]:
    '''
    Split by ``,``.

    Can quote characters inside the pair of quote symbol ``"``.
    '''
    split_by_quotes = text.split('"')
    result = []
    for i, part in enumerate(split_by_quotes):
        if i % 2 == 0:
            split_by_comma = part.split(',')

            if i != 0:
                split_by_comma = split_by_comma[1:]
            if i != len(split_by_quotes) - 1:
                split_by_comma = split_by_comma[:-1]

            result.extend(split_by_comma)
        else:
            result.append(part)

    return result


def get_default(lst: list[T], at: int, default=None) -> T | None:
    if 0 <= at < len(lst):
        return lst[at]
    return default
