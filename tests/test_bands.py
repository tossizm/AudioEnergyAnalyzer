from app.analysis.spectrum import BANDS, DEFAULT_BANDS, set_band_maxima, reset_bands


def test_default_bands_are_10_ranges():
    reset_bands()
    assert BANDS == DEFAULT_BANDS
    assert BANDS[0][:2] == (20, 60)
    assert BANDS[-1][:2] == (16000, 20000)


def test_custom_band_maxima_updates_all_ranges():
    set_band_maxima([70, 140, 280, 560, 1100, 2200, 4400, 8800, 17000])
    assert BANDS[0][:2] == (20, 70)
    assert BANDS[1][:2] == (70, 140)
    assert BANDS[8][:2] == (8800, 17000)
    assert BANDS[9][:2] == (17000, 20000)
    reset_bands()


def test_invalid_band_maxima_rejected():
    for values in ([60, 120, 120, 500, 1000, 2000, 4000, 8000, 16000],
                   [60, 120, 19, 500, 1000, 2000, 4000, 8000, 16000],
                   [60, 120, 250, 500, 1000, 2000, 4000, 8000, 20000]):
        try:
            set_band_maxima(values)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid band maxima accepted")


def test_band_settings_payload_uses_entered_values_exactly():
    from app.analysis.spectrum import build_band_settings_payload
    payload=build_band_settings_payload([70,140,280,560,1120,2240,4480,8960,17000])
    assert payload["bands"][0] == {"min_hz":20,"max_hz":70}
    assert payload["bands"][4] == {"min_hz":560,"max_hz":1120}
    assert payload["bands"][8] == {"min_hz":8960,"max_hz":17000}
    assert payload["bands"][9] == {"min_hz":17000,"max_hz":20000}
