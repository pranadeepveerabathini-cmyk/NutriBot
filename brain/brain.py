from .memory_service import MemoryService
from .extractor import MemoryExtractor


class Brain:

    def __init__(self):
        self.memory = MemoryService()
        self.extractor = MemoryExtractor()

    def load_user_memory(self, user_id):
        return self.memory.get_memories(user_id)

    def build_memory_prompt(self, user_id):

        memories = self.load_user_memory(user_id)

        if not memories:
            return ""

        text = "### Long-Term User Memory\n"

        for m in memories:
            text += f"- {m['category']} | {m['key']} : {m['value']}\n"

        return text