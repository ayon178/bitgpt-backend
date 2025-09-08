from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime, timedelta

from .model import RecycleQueue, RecyclePlacement, RecycleSettings, RecycleLog
from ..matrix.model import MatrixTree


class RecycleService:
    """Matrix Recycle business logic"""

    def __init__(self) -> None:
        pass

    def queue_recycle(self, user_id: str, parent_id: str, matrix_level: int, slot_no: int,
                      recycle_reason: str, preferred_position: str = 'center', recycle_amount: float = 0) -> Dict[str, Any]:
        item = RecycleQueue(
            user_id=ObjectId(user_id),
            parent_id=ObjectId(parent_id),
            matrix_level=matrix_level,
            slot_no=slot_no,
            recycle_reason=recycle_reason,
            preferred_position=preferred_position,
            recycle_amount=recycle_amount,
            status='queued'
        )
        item.save()
        self._log(item.user_id, 'queued', 'Recycle queued', related_queue_id=item.id)
        return {"queue_id": str(item.id), "status": item.status}

    def process_queue_batch(self, batch_size: int = 100) -> Dict[str, Any]:
        pending = RecycleQueue.objects(status='queued').order_by('created_at').limit(batch_size)
        processed, failed = 0, 0
        for item in pending:
            try:
                self._attempt_place(item)
                processed += 1
            except Exception as e:
                failed += 1
                item.status = 'failed'
                item.failure_reason = str(e)
                item.last_attempt_at = datetime.utcnow()
                item.attempts += 1
                item.save()
                self._log(item.user_id, 'failed', f'Recycle placement failed: {e}', related_queue_id=item.id)
        return {"processed": processed, "failed": failed}

    def _attempt_place(self, item: RecycleQueue) -> None:
        item.status = 'processing'
        item.last_attempt_at = datetime.utcnow()
        item.attempts += 1
        item.save()

        # Find a new parent in matrix tree (simple strategy: keep same parent if space, else parent's parent)
        parent_tree = MatrixTree.objects(user_id=item.parent_id).first()
        if not parent_tree:
            raise ValueError('Parent matrix tree not found')

        # Determine available position
        target_position = self._find_available_position(parent_tree, preferred=item.preferred_position)
        if not target_position:
            # fallback: try parent's parent
            grand_parent_tree = MatrixTree.objects(user_id=parent_tree.parent_id).first()
            if not grand_parent_tree:
                raise ValueError('No available position for recycle')
            target_position = self._find_available_position(grand_parent_tree, preferred=item.preferred_position)
            if not target_position:
                raise ValueError('No available position for recycle (grandparent)')
            new_parent_id = grand_parent_tree.user_id
        else:
            new_parent_id = parent_tree.user_id

        # Record placement (actual MatrixTree modification would be handled elsewhere/integration)
        placement = RecyclePlacement(
            user_id=item.user_id,
            old_parent_id=item.parent_id,
            new_parent_id=new_parent_id,
            matrix_level=item.matrix_level,
            slot_no=item.slot_no,
            position=target_position,
            recycle_amount=item.recycle_amount,
            queue_id=item.id,
            trigger='auto',
            processed_at=datetime.utcnow()
        )
        placement.save()

        item.status = 'completed'
        item.processed_at = datetime.utcnow()
        item.save()
        self._log(item.user_id, 'placed', 'Recycle placed', related_queue_id=item.id, related_placement_id=placement.id)

    def _find_available_position(self, tree: MatrixTree, preferred: str = 'center') -> Optional[str]:
        occupied = {p.position for p in (tree.positions or []) if p.is_active}
        order = [preferred, 'left', 'center', 'right']
        for pos in order:
            if pos in {'left', 'center', 'right'} and pos not in occupied:
                return pos
        return None

    def _log(self, user_id: ObjectId, action: str, desc: str, **kwargs) -> None:
        RecycleLog(user_id=user_id, action_type=action, description=desc, **kwargs).save()


