from agent import NutritionAgent
from brain.extractor import MemoryExtractor

agent = NutritionAgent()

gemini = agent._get_gemini()

extractor = MemoryExtractor()

result = extractor.extract(
    gemini,
    "Hi, I'm Pranadeep. I'm vegetarian, allergic to peanuts and my goal is to lose 8 kg."
)

print(result)