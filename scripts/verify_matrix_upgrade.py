import json
import os
from bson import ObjectId

from core.db import connect_to_db
from modules.slot import SlotActivation
from modules.matrix.model import MatrixActivation, MatrixTree
from modules.auto_upgrade.model import MatrixAutoUpgrade


def main(parent_id: str | None):
    connect_to_db()
    if not parent_id:
        # Try reading the last generated parent id from script
        try:
            with open("scripts/.last_parent_id", "r", encoding="utf-8") as f:
                parent_id = f.read().strip()
        except Exception:
            pass
    if not parent_id:
        print(json.dumps({"error": "missing_parent_id"}))
        return

    activations = SlotActivation.objects(user_id=ObjectId(parent_id), program="matrix").order_by("slot_no")
    out_slot_activation = [
        {
            "slot_no": sa.slot_no,
            "program": sa.program,
            "status": getattr(sa, "status", None),
            "tx_hash": getattr(sa, "tx_hash", None),
            "amount_paid": str(getattr(sa, "amount_paid", "")),
            "is_auto_upgrade": getattr(sa, "is_auto_upgrade", False),
        }
        for sa in activations
    ]
    activations_matrix = MatrixActivation.objects(user_id=ObjectId(parent_id)).order_by("slot_no")
    out_matrix_activation = [
        {
            "slot_no": ma.slot_no,
            "status": getattr(ma, "status", None),
            "tx_hash": getattr(ma, "tx_hash", None),
            "amount_paid": str(getattr(ma, "amount_paid", "")),
            "is_auto_upgrade": getattr(ma, "is_auto_upgrade", False),
        }
        for ma in activations_matrix
    ]
    tree = MatrixTree.objects(user_id=ObjectId(parent_id)).first()
    auto_status = MatrixAutoUpgrade.objects(user_id=ObjectId(parent_id)).first()
    tree_info = {
        "current_slot": getattr(tree, "current_slot", None),
        "current_level": getattr(tree, "current_level", None),
    } if tree else None
    auto_info = {
        "current_slot_no": getattr(auto_status, "current_slot_no", None),
        "middle_three_available": getattr(auto_status, "middle_three_available", None),
        "next_upgrade_cost": getattr(auto_status, "next_upgrade_cost", None),
    } if auto_status else None
    def _safe(o):
        if isinstance(o, list):
            return [_safe(x) for x in o]
        if isinstance(o, dict):
            return {k: _safe(v) for k, v in o.items()}
        try:
            from decimal import Decimal as _D
            if isinstance(o, _D):
                return str(o)
        except Exception:
            pass
        try:
            import datetime as _dt
            if isinstance(o, (_dt.datetime, _dt.date)):
                return o.isoformat()
        except Exception:
            pass
        return o

    print(json.dumps(_safe({
        "parent_id": parent_id,
        "slot_activation": out_slot_activation,
        "matrix_activation": out_matrix_activation,
        "matrix_tree": tree_info,
        "matrix_auto_upgrade": auto_info
    }), separators=(",", ":")))


if __name__ == "__main__":
    main(None)


