"""Controlled public programme labels; never publish arbitrary render metadata."""
import json
from pathlib import Path
import unicodedata


STAGES = {'arrival': 'beginning', 'unfold': 'unfolding', 'bloom': 'in bloom',
          'settle': 'settling', 'release': 'closing'}
PALETTES = {(89, 32, 4): 'Warm keys', (94, 32, 4): 'Halo keys',
            (89, 32, 11): 'Soft bells'}
GENERIC = 'Original ambient music.'


def title_for_analysis(analysis: str | None) -> str:
    if not isinstance(analysis, str) or len(analysis) > 8192:
        return GENERIC
    try:
        value = json.loads(analysis)
    except (ValueError, RecursionError):
        return GENERIC
    plan = value.get('arrangement') if isinstance(value, dict) else None
    if not isinstance(plan, dict):
        return GENERIC
    version, chapter, stage = (plan.get(k) for k in ['version', 'chapter', 'stage'])
    if (type(version) is not int or version not in (1, 2)
            or type(chapter) is not int or not 0 < chapter <= 2**63 - 1
            or not isinstance(stage, str) or stage not in STAGES):
        return GENERIC
    title = f'Chapter {chapter} is {STAGES[stage]}.'
    programs = plan.get('programs')
    if isinstance(programs, (list, tuple)) and len(programs) == 3 and all(type(p) is int for p in programs):
        palette = PALETTES.get(tuple(programs))
        if palette:
            title += f' {palette}.'
    return title


def annotated_request(path: str, analysis: str | None) -> str:
    if (not isinstance(path, str) or not Path(path).is_absolute()
            or any(unicodedata.category(c) == 'Cc' or c in '\u2028\u2029' for c in path)):
        raise ValueError('Expected an absolute, single-line audio path')
    return (f'annotate:title={json.dumps(title_for_analysis(analysis))},'
            f'artist="Generative Radio":{path}')
