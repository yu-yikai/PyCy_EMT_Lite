"""Compare example28 with the sealed, actual R2025a Simscape reference.

Run: uv run python -m validation.cases.grid_connected_vsc_open_loop.compare
The default teaching example does not need these local commercial archives.
This entry only reads archived reference data; it starts no vendor process.
"""

import csv
import json
import platform
import re
import runpy
import shutil
import subprocess
from array import array
from datetime import UTC, datetime
from decimal import Decimal as D
from decimal import localcontext
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pycy_emt_lite import Circuit, Simulator
from validation.common.runner import sha256

from . import binding, metrics, physics

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = Path(__file__).resolve().parent
EXAMPLE = ROOT / 'examples/28_grid_connected_vsc_open_loop.py'
NUMBER = re.compile(r'-?[0-9]\.[0-9]{15}e[+-][0-9]{2,3}')
PINS = {
    'parameters.json': 'f5041eee9296c4088e74168cb444a10b016c10ee787d044629cb9492ab523dc1',
    'reference_protocol.json': 'd87a327ef601200b2ebb360403879206d8817697f78767999143226aecf26630',
    'qualified_reference_report.json': '58718e58e4b32ae930efe7b4244ff4207f8fda048eec65307b80b96b7ece1277',
}


def save_json(path, data):
    def scalar(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    encoded = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False, default=scalar)+'\n'
    path.write_text(encoded, encoding='utf-8')


def _verify(item):
    path = (ROOT / item['path']).resolve(strict=True)
    physics.require(path.is_relative_to(ROOT) and type(item['bytes']) is int
                    and path.stat().st_size == item['bytes'] and sha256(path) == item['sha256'],
                    'Changed or unavailable input: '+item['path'])
    return path


def load_reference():
    """Recheck historical qualification and every sealed raw file, without reruns."""
    bindings = {}

    def admit(item):
        path = _verify(item)
        bindings[path.relative_to(ROOT).as_posix()] = item['sha256']
        return path

    for name, digest in PINS.items():
        path = DIRECTORY / name
        physics.require(sha256(path) == digest, 'Frozen case input changed: '+name)
        bindings[path.relative_to(ROOT).as_posix()] = digest
    summary = json.loads((DIRECTORY / 'qualified_reference_report.json').read_text(encoding='utf-8'))
    qualification = json.loads(admit(summary['qualification']).read_text(encoding='utf-8'))
    physics.require(summary['full_reference_qualified'] is True
                    and qualification['full_reference_qualified'] is True
                    and qualification['candidate_authorized'] is True
                    and qualification['status'] == 'QUALIFIED_ACTUAL_SIMSCAPE_FULL_OPENLOOP_REFERENCE_ONLY',
                    'The full open-loop reference is not qualified')
    for item in qualification['references'].values():
        admit(item)
    paths = {}
    for variant, record in zip(('coarse', 'fine'), summary['variants'], strict=True):
        raw = json.loads(admit(record['ROOT_raw_closed']).read_text(encoding='utf-8'))
        physics.require(raw['actual_MAT_reload_verified'] is True
                        and raw['status'] == 'CLOSED_RAW_EXPORT_PASS_NOT_REFERENCE_QUALIFIED',
                        'Raw archive closure differs')
        for item in raw['raw_files'].values():
            admit(item)
        paths[variant] = ROOT / raw['raw_files']['channels45']['path']
    parameters = json.loads((DIRECTORY / 'parameters.json').read_text(encoding='utf-8'))
    protocol = json.loads((DIRECTORY / 'reference_protocol.json').read_text(encoding='utf-8'))
    return paths, parameters, protocol, bindings


def token_word(value, name):
    """Serialize actual SI binary64 within one full printed place, scaled once."""
    value = float(value)
    physics.require(np.isfinite(value), 'Cannot serialize nonfinite candidate sample')
    exact = name.startswith(('applied_g_', 'R_'))
    actual = D(str(value)) if exact else D.from_float(value)
    factor = D(1000) if physics.unit(name) in {'kV', 'kA'} else D(1)
    with localcontext() as context:
        context.prec = 70
        scaled = actual/factor
        if scaled == 0:
            word = '0.000000000000000e+00'
        else:
            mantissa, exponent = format(scaled, '.15e').split('e')
            word = f'{mantissa}e{int(exponent):+03d}'
        center, q = physics.token(word, name)
        physics.require(NUMBER.fullmatch(word) and q.is_finite() and q > 0 and abs(center-actual) <= q,
                        'Printed candidate interval does not enclose its original value')
        if exact:
            physics.require(center == actual, 'Serialization changed an exact gate/R center')
    return word


def write_plant(path, data):
    physics.require(set(data) == set(physics.names()), 'Exactly32 mapped quantities required')
    with path.open('x', encoding='ascii', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(physics.names())
        for row in zip(*(data[name] for name in physics.names()), strict=True):
            writer.writerow([token_word(value, name) for name, value in zip(physics.names(), row, strict=True)])


class PlantRows:
    """Reiterable original-token stream; do not allocate a full Decimal table."""

    def __init__(self, path, count, header):
        self.path, self.count, self.header = path, count, header

    def __len__(self):
        return self.count

    def __iter__(self):
        with self.path.open(encoding='ascii', newline='') as stream:
            reader = csv.reader(stream)
            physics.require(next(reader) == self.header, 'Exact original column header required')
            count = 0
            for words in reader:
                physics.require(len(words) == len(self.header) and all(NUMBER.fullmatch(w) for w in words),
                                'Malformed original row or numeric word')
                physics.require(count < self.count, 'Unexpected extra acquisition row')
                values, radii = {}, {}
                for name, word in zip(physics.names(), words[:32], strict=True):
                    values[name], radii[name] = physics.token(word, name)
                    physics.require(radii[name].is_finite() and radii[name] > 0, 'Full-place q must be positive')
                count += 1
                yield values, radii
            physics.require(count == self.count, 'Incomplete acquisition including tail')


class Projection:
    def __init__(self, rows, index):
        self.rows, self.index = rows, index

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        return (row[self.index] for row in self.rows)


def metric_table(rows):
    """Retain exact TIME/g/R centers; analog arrays are converted only after q parsing."""
    table = {name: [] if name == 'TIME_native_s' or name.startswith(('applied_g_', 'R_'))
             else array('d') for name in physics.names()}
    for values, _ in rows:
        for name, value in values.items():
            table[name].append(value if isinstance(table[name], list) else float(value))
    return table


def _source_bindings():
    paths = [path for tree in ('pycy_emt_lite', 'examples', 'tests', 'validation')
             for path in (ROOT / tree).rglob('*.py')]
    paths += [ROOT / name for name in ('pyproject.toml', 'uv.lock')]
    paths += [DIRECTORY / name for name in ('parameters.json', 'reference_protocol.json',
                                          'qualified_reference_report.json', 'acceptance_plan.md',
                                          'manifest.json', 'README.md')]
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(paths)}


def _plot(destination, candidate, reference):
    figure, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    for phase in 'abc':
        for data, label, style in ((reference, 'Simscape', '-'), (candidate, 'PyCy', '--')):
            time = np.asarray(data['TIME_native_s'], dtype=float)
            axes[0].plot(time, data[f'I_{phase}_ac_to_bridge_kA'], style, label=f'{label} {phase}', linewidth=.8)
    for data, label, style in ((reference, 'Simscape', '-'), (candidate, 'PyCy', '--')):
        time = np.asarray(data['TIME_native_s'], dtype=float)
        for rail in ('p', 'n'):
            axes[1].plot(time, data[f'Vdc_{rail}_kV'], style, label=f'{label} DC{rail}', linewidth=.7)
        axes[2].plot(time, metrics.snapshots(metrics._float_arrays(data))['Pg'], style, label=label, linewidth=.7)
    for axis, ylabel in zip(axes, ('Grid-to-bridge current (A)', 'Floating rails (V)', 'Grid power (W)'), strict=True):
        axis.set_ylabel(ylabel)
        axis.grid(alpha=.3)
        axis.legend(ncol=3)
    axes[-1].set_xlabel('Absolute time (s)')
    figure.tight_layout()
    figure.savefig(destination / 'comparison.png', dpi=150)
    plt.close(figure)


def run_comparison(destination, *, execution):
    """Save an isolated run; passing here still requires independent review/acceptance."""
    paths, parameters, protocol, bindings = load_reference()
    bindings.update(_source_bindings())
    destination.mkdir(parents=True, exist_ok=False)
    for relative in bindings:
        target = destination / 'inputs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
        physics.require(sha256(target) == bindings[relative], 'Input snapshot changed: '+relative)
    save_json(destination / 'input_bindings.json', bindings)
    report = {'schema': 'grid_connected_vsc_open_loop_candidate_comparison_v1',
              'status': 'STARTED_NOT_ACCEPTED', 'passed': False, 'candidate_accepted': False,
              'execution': execution, 'python_version': platform.python_version(), 'numpy_version': np.__version__,
              'parameters_sha256': PINS['parameters.json'], 'protocol_sha256': PINS['reference_protocol.json'],
              'variants': {}, 'reference_scope': 'Locally constructed, actual R2025a Simscape open-loop model.'}
    save_json(destination / 'report.json', report)
    with localcontext() as context:
        context.prec = 70
        example = runpy.run_path(str(EXAMPLE))
        tables, references = {}, {}
        for variant, settings in parameters['variants'].items():
            h, count = settings['h_s'], settings['expected_rows']
            case = example['define_case'](time_step=h, stop_time=parameters['acquisition_stop_s'])
            admitted = binding.check_case(example, case, parameters, protocol)
            save_json(destination / f'{variant}_input_admission.json', admitted)
            before = binding.component_binding(case.components)
            result = Simulator(Circuit.from_components(case.name, case.components), case.config,
                               events=case.events, on_step=case.on_step).run()
            physics.require(len(result.rows) == count and not result.event_log, 'Candidate acquisition changed')
            physics.require(before == binding.component_binding(case.components), 'Actual callback/constructor changed')
            result.to_csv(destination / f'{variant}_pycy.csv')
            result.to_npz(destination / f'{variant}_pycy.npz')
            candidate_path = destination / f'{variant}_plant32.csv'
            write_plant(candidate_path, binding.plant_data(result, case.components))
            del result
            rows = PlantRows(candidate_path, count, physics.names())
            physical = physics.evaluate(Projection(rows, 0), Projection(rows, 1), h=D(str(h)), expected_rows=count,
                                        limits=protocol['physical_residual_budgets'],
                                        precision_caps=protocol['printed_precision_caps_SI'])
            save_json(destination / f'{variant}_physical.json', physical)
            tables[variant] = metric_table(rows)
            header = [channel['signal'] for channel in protocol['native_channels']['channels']]
            reference_path = destination / 'inputs' / paths[variant].relative_to(ROOT)
            references[variant] = metric_table(PlantRows(reference_path, count, header))
            same = metrics.compare_same_h(tables[variant], references[variant], protocol, h=h)
            save_json(destination / f'{variant}_same_h.json', same)
            report['variants'][variant] = {'rows': count, 'h_s': h, 'physical_pass': physical['observed_pass'],
                                           'same_h_pass': same['passed'], 'same_h_hard_results': same['hard_results'],
                                           'actual_callback_binding_unchanged': True}
            save_json(destination / 'report.json', report)
        cross = metrics.compare_cross_h(tables['coarse'], references['fine'], protocol)
        save_json(destination / 'cross_h.json', cross)
        report['cross_h_pass'] = cross['passed']
        report['cross_h_hard_results'] = cross['hard_results']
        _plot(destination, tables['coarse'], references['coarse'])
    for relative, digest in bindings.items():
        physics.require(sha256(ROOT / relative) == digest and sha256(destination / 'inputs' / relative) == digest,
                        'Input changed during comparison: '+relative)
    report['passed'] = cross['passed'] and all(v['physical_pass'] and v['same_h_pass'] for v in report['variants'].values())
    report['status'] = 'PRIMARY_PASS_INDEPENDENT_REVIEW_PENDING' if report['passed'] else 'PRIMARY_NUMERIC_FAIL'
    report['all_acquisition_rows_and_tail_retained'] = True
    report['artifacts'] = {path.name: sha256(path) for path in sorted(destination.iterdir())
                           if path.is_file() and path.name != 'report.json'}
    save_json(destination / 'report.json', report)
    return report


def main():
    git = ['git', '-c', f'safe.directory={ROOT.as_posix()}']
    execution = {'head': subprocess.check_output([*git, 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                 'status': subprocess.check_output([*git, 'status', '--porcelain'], cwd=ROOT, text=True).splitlines()}
    run_id = datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    destination = ROOT / 'local_reference/grid_connected_vsc_open_loop/comparison_results' / run_id
    report = run_comparison(destination, execution=execution)
    print(f"grid_connected_vsc_open_loop: {'PASS' if report['passed'] else 'FAIL'}; {destination / 'report.json'}")
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
