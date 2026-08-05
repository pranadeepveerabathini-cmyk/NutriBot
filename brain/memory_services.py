from models import db, UserMemory


class MemoryService:

    @staticmethod
    def save_memory(user_id, category, key, value):
        memory = UserMemory.query.filter_by(
            user_id=user_id,
            category=category,
            key=key
        ).first()

        if memory:
            memory.value = value
        else:
            memory = UserMemory(
                user_id=user_id,
                category=category,
                key=key,
                value=value
            )
            db.session.add(memory)

        db.session.commit()

    @staticmethod
    def get_memories(user_id):
        memories = UserMemory.query.filter_by(user_id=user_id).all()

        return [
            {
                "category": m.category,
                "key": m.key,
                "value": m.value
            }
            for m in memories
        ]

    @staticmethod
    def delete_memory(user_id, category, key):
        memory = UserMemory.query.filter_by(
            user_id=user_id,
            category=category,
            key=key
        ).first()

        if memory:
            db.session.delete(memory)
            db.session.commit()