# Assessment release map

| Assessment | Git tag | Commit lineage | Main repository evidence |
|---|---|---|---|
| ISE-A1 | `ise-a1-v1.0` | Original opportunity/evidence package | `report/ISE-A1_Problem_and_Stakeholder_Evidence_Brief.docx`, evidence ledger, source notes and notebook |
| ISE-A2 | `ise-a2-v1.0` | Domain model and testable specification | `src/clinic_model.py`, `tests/test_clinic_model.py`, `models/`, `notebook/a2_model_walkthrough.ipynb` |
| ISE-A3 | `ise-a3-v1.0` | Repository investigation of the A2 snapshot | `report/ISE-A3_Repository_Investigation_and_Reproducible_Build.docx`, `docs/a3/`, `results/a3/` |
| ISE-A4 | `ise-a4-v1.0` | End-to-end vertical slice | `app/`, `static/`, `tests/test_vertical_slice.py`, `docs/a4/`, `results/a4/` |

To inspect each release commit:

```bash
git show --no-patch --decorate ise-a1-v1.0
git show --no-patch --decorate ise-a2-v1.0
git show --no-patch --decorate ise-a3-v1.0
git show --no-patch --decorate ise-a4-v1.0
```

The tags identify local repository states. A tag is not proof that a release was pushed to a remote host; a remote GitHub URL must be created by the repository owner.
