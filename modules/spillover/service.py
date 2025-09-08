from typing import Dict, Any, Optional
from bson import ObjectId
from datetime import datetime

from .model import SpilloverQueue, SpilloverPlacement, SpilloverSettings, SpilloverLog
from ..tree.model import TreePlacement


class SpilloverService:
    """Binary Spillover logic and queue processing"""

    def queue_spillover(self, user_id: str, original_parent_id: str, intended_parent_id: str,
                        spillover_reason: str, preferred_side: str = 'left') -> Dict[str, Any]:
        item = SpilloverQueue(
            user_id=ObjectId(user_id),
            original_parent_id=ObjectId(original_parent_id),
            intended_parent_id=ObjectId(intended_parent_id),
            spillover_reason=spillover_reason,
            preferred_side=preferred_side,
            status='queued'
        )
        item.save()
        self._log(item.user_id, 'queued', 'Spillover queued', related_queue_id=item.id)
        return {"queue_id": str(item.id), "status": item.status}

    def process_queue_batch(self, batch_size: int = 200) -> Dict[str, Any]:
        settings = SpilloverSettings.objects().first() or SpilloverSettings()
        batch_size = min(batch_size, settings.queue_batch_size)
        pending = SpilloverQueue.objects(status='queued').order_by('created_at').limit(batch_size)
        processed, failed = 0, 0
        for item in pending:
            try:
                self._attempt_place(item, settings)
                processed += 1
            except Exception as e:
                failed += 1
                item.status = 'failed'
                item.failure_reason = str(e)
                item.last_attempt_at = datetime.utcnow()
                item.attempts += 1
                item.save()
                self._log(item.user_id, 'failed', f'Spillover failed: {e}', related_queue_id=item.id)
        return {"processed": processed, "failed": failed}

    def _attempt_place(self, item: SpilloverQueue, settings: SpilloverSettings) -> None:
        item.status = 'processing'
        item.last_attempt_at = datetime.utcnow()
        item.attempts += 1
        item.save()

        # BFS search for nearest vacancy starting from intended_parent
        vacancy = self._find_nearest_vacancy(item.intended_parent_id, settings)
        if vacancy is None:
            raise ValueError('No vacancy found for spillover')

        parent_id, position, level = vacancy

        # Place record (actual binary placement update occurs in TreePlacement integration)
        placement = SpilloverPlacement(
            user_id=item.user_id,
            original_parent_id=item.original_parent_id,
            spillover_parent_id=parent_id,
            position=position,
            spillover_level=level,
            queue_id=item.id,
            trigger='auto',
            processed_at=datetime.utcnow()
        )
        placement.save()

        item.status = 'completed'
        item.processed_at = datetime.utcnow()
        item.save()
        self._log(item.user_id, 'placed', 'Spillover placed', related_queue_id=item.id, related_placement_id=placement.id)

    def _find_nearest_vacancy(self, start_parent_id: ObjectId, settings: SpilloverSettings) -> Optional[tuple]:
        # Breadth-first search of the binary tree to find the nearest available left/right
        from collections import deque
        queue = deque([(start_parent_id, 0)])
        visited = set()
        scanned = 0
        while queue and scanned < settings.bfs_search_limit:
            parent_id, level = queue.popleft()
            if str(parent_id) in visited:
                continue
            visited.add(str(parent_id))
            scanned += 1

            parent_node = TreePlacement.objects(user_id=parent_id).first()
            if not parent_node:
                continue

            if not parent_node.left_child_id:
                return (parent_id, 'left', level + 1)
            if not parent_node.right_child_id:
                return (parent_id, 'right', level + 1)

            # enqueue children
            queue.append((parent_node.left_child_id, level + 1))
            queue.append((parent_node.right_child_id, level + 1))

        return None

    def _log(self, user_id: ObjectId, action: str, desc: str, **kwargs) -> None:
        SpilloverLog(user_id=user_id, action_type=action, description=desc, **kwargs).save()


