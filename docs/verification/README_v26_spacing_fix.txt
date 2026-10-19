ClubAudioAnalyzer v26 - UI spacing verification

Fix:
- Only the ①：～⑩： row-label block is shifted +42 px (two full-width Japanese characters).
- Minimum-Hz values, Hz labels, ～, editable boxes, right-side Hz labels are not shifted.
- Row labels are removed from QGridLayout before positioning so Qt layout recalculation cannot undo the shift.
- Approved v24 UI images are stored in docs/approved_ui/.

Verification:
- Python syntax compilation passed.
- pytest: 10 passed.
- PySide6 is not installed in this build container, so native Windows GUI execution could not be performed here.
- The verification image in this directory applies the exact +42 px row-label-only correction to the supplied actual screenshot for visual inspection.
