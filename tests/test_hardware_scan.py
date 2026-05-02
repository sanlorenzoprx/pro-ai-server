from pro_ai_server.hardware import (
    assess_device_profile,
    parse_battery_dump,
    parse_data_free_storage_gb,
    parse_meminfo_ram_gb,
)


def test_parse_meminfo_ram_gb_reads_memtotal():
    meminfo = """
MemFree:          123456 kB
MemTotal:        8142344 kB
Buffers:          123456 kB
"""

    assert parse_meminfo_ram_gb(meminfo) == 8142344 / 1024 / 1024


def test_parse_data_free_storage_gb_reads_available_column_for_data():
    df_output = """
Filesystem     1K-blocks     Used Available Use% Mounted on
/dev/block/dm-2 113646584 8423032 105223552   8% /data
"""

    assert parse_data_free_storage_gb(df_output) == 105223552 / 1024 / 1024


def test_parse_battery_dump_reads_level_temperature_and_charging():
    dumpsys_battery = """
Current Battery Service state:
  AC powered: false
  USB powered: true
  level: 87
  status: 2
  temperature: 317
"""

    battery = parse_battery_dump(dumpsys_battery)

    assert battery["battery_level"] == 87
    assert battery["battery_temperature_c"] == 31.7
    assert battery["is_charging"] is True


def test_assess_device_profile_combines_parsed_values_without_adb():
    battery = parse_battery_dump("level: 55\ntemperature: 300\nplugged: 0\nstatus: 3")
    profile = assess_device_profile(
        serial="ABC123",
        manufacturer="Google",
        model="Pixel Test",
        android_version="15",
        abi="arm64-v8a",
        ram_gb=parse_meminfo_ram_gb("MemTotal: 6291456 kB"),
        free_storage_gb=parse_data_free_storage_gb(
            "Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-2 100 1 7340032 1% /data"
        ),
        battery_level=battery["battery_level"],
        battery_temperature_c=battery["battery_temperature_c"],
        is_charging=battery["is_charging"],
    )

    assert profile.serial == "ABC123"
    assert profile.ram_gb == 6
    assert profile.free_storage_gb == 7
    assert profile.battery_level == 55
    assert profile.battery_temperature_c == 30
    assert profile.is_charging is False
    assert profile.recommended_profile is not None
    assert profile.recommended_profile.name == "professional"
    assert profile.warnings == ("Free storage is under 8 GB; warn before downloading models.",)
