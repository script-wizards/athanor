from athanor import status


def supply(root, name, **files):
    d = root / name
    d.mkdir()
    for key, value in files.items():
        (d / key).write_text(f"{value}\n")


def test_battery_with_wear(tmp_path):
    supply(tmp_path, "AC", type="Mains", online=1)
    supply(
        tmp_path,
        "BAT0",
        type="Battery",
        present=1,
        capacity=87,
        status="Discharging",
        energy_full=48000000,
        energy_full_design=50000000,
    )
    assert status.battery(tmp_path) == status.Battery(87, 96, False)


def test_no_battery(tmp_path):
    supply(tmp_path, "AC", type="Mains")
    assert status.battery(tmp_path) is None


def test_cpu_delta(tmp_path):
    stat = tmp_path / "stat"
    cpu = status.Cpu(stat)
    stat.write_text("cpu  100 0 100 800 0 0 0 0 0 0\n")
    assert cpu.percent() is None
    stat.write_text("cpu  150 0 150 900 0 0 0 0 0 0\n")
    assert cpu.percent() == 50


def test_line():
    r = status.Reading(
        workspace=3,
        disk_free=212 * 2**30,
        battery=status.Battery(87, 96, False),
        cpu=14,
        mem_used=int(6.1 * 2**30),
        minutes=48213,
    )
    assert status.line(r) == "Dlvl:3  $:212G  Hp:87(96)  Str:14%  Mem:6.1G  T:48213"


def test_low_battery_is_hurt():
    base = dict(workspace=1, disk_free=0, cpu=0, mem_used=0, minutes=0)
    assert status.classes(status.Reading(battery=status.Battery(15, 100, False), **base)) == [
        "hurt"
    ]
    assert status.classes(status.Reading(battery=status.Battery(15, 100, True), **base)) == []
    assert status.classes(status.Reading(battery=None, **base)) == []


def test_workspace_events_trigger_a_redraw():
    from athanor import status

    assert status.wants_redraw(b"activewindow>>foot,zsh\nworkspace>>3\n")
    assert status.wants_redraw(b"workspacev2>>3,3\n")
    assert not status.wants_redraw(b"activewindow>>foot,zsh\nwindowtitle>>56056e\n")
