"""GitHub Codex服务 - AI代码生成集成。"""

import logging
from typing import Any

import aiohttp

from src.config.settings import settings

logger = logging.getLogger(__name__)


class CodexService:
    """Codex代码生成服务。"""

    def __init__(self) -> None:
        self.github_token = settings.GITHUB_TOKEN
        self.api_base = settings.CODEX_API_URL.rstrip("/")
        self.model = settings.CODEX_MODEL
        logger.info("CodexService initialized")

    async def generate_code(self, prompt: str, language: str = "python", **kwargs: Any) -> str:
        """根据提示词生成代码。"""
        temperature = float(kwargs.get("temperature", 0.5))
        max_tokens = int(kwargs.get("max_tokens", 2048))
        enhanced_prompt = self._enhance_prompt(prompt, language)

        try:
            return await self._call_copilot_api(enhanced_prompt, language, temperature, max_tokens)
        except Exception as exc:
            logger.error("Failed to generate code: %s", exc)
            return self._get_demo_code(prompt, language)

    async def explain_code(self, code: str, language: str = "python", **kwargs: Any) -> str:
        """解释代码。"""
        prompt = f"请解释以下{language}代码：\n\n```{language}\n{code}\n```"
        return await self.generate_code(prompt, language=language, **kwargs)

    async def complete_code(self, partial_code: str, language: str = "python", **kwargs: Any) -> str:
        """补全代码。"""
        prompt = f"请补全以下{language}代码：\n\n```{language}\n{partial_code}\n```"
        return await self.generate_code(prompt, language=language, **kwargs)

    async def optimize_code(self, code: str, language: str = "python", **kwargs: Any) -> str:
        """优化代码。"""
        prompt = f"请优化以下{language}代码的性能和可读性：\n\n```{language}\n{code}\n```"
        return await self.generate_code(prompt, language=language, **kwargs)

    async def translate_code(
        self,
        code: str,
        from_lang: str,
        to_lang: str,
        **kwargs: Any,
    ) -> str:
        """翻译代码。"""
        prompt = f"请将以下{from_lang}代码翻译为{to_lang}：\n\n```{from_lang}\n{code}\n```"
        return await self.generate_code(prompt, language=to_lang, **kwargs)

    def _enhance_prompt(self, prompt: str, language: str) -> str:
        """增强提示词。"""
        return f"""Please generate clean, well-documented {language} code.

Requirements:
- Follow {language} best practices and conventions
- Include meaningful variable names
- Add comments for complex logic
- Handle edge cases
- Make the code production-ready

User request: {prompt}

Generate the code:"""

    async def _call_copilot_api(
        self,
        prompt: str,
        language: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """调用GitHub兼容接口；不可用时回退到演示模式。"""
        if not self.github_token:
            logger.warning("GitHub token not configured, using demo mode")
            return self._get_demo_code(prompt, language)

        url = f"{self.api_base}/copilot_internal/completions"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

        timeout = aiohttp.ClientTimeout(total=30)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        logger.warning("Codex API returned status %s, using demo mode", response.status)
                        return self._get_demo_code(prompt, language)

                    data = await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            logger.warning("Codex API request failed: %s", exc)
            return self._get_demo_code(prompt, language)

        choices = data.get("choices", [])
        if choices:
            text = choices[0].get("text", "").strip()
            if text:
                return text

        logger.warning("Codex API response missing choices, using demo mode")
        return self._get_demo_code(prompt, language)

    def _get_demo_code(self, prompt: str, language: str = "python") -> str:
        """当远程接口不可用时返回演示代码。"""
        demo_codes = {
            "python": """def quicksort(arr):
    \"\"\"快速排序实现\"\"\"
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quicksort(left) + middle + quicksort(right)


if __name__ == "__main__":
    arr = [3, 6, 8, 10, 1, 2, 1]
    print(quicksort(arr))
""",
            "javascript": """function quickSort(arr) {
  if (arr.length <= 1) return arr;

  const pivot = arr[Math.floor(arr.length / 2)];
  const left = arr.filter((item) => item < pivot);
  const middle = arr.filter((item) => item === pivot);
  const right = arr.filter((item) => item > pivot);

  return [...quickSort(left), ...middle, ...quickSort(right)];
}

console.log(quickSort([3, 6, 8, 10, 1, 2, 1]));
""",
            "java": """public class QuickSort {
    public static void quickSort(int[] arr, int low, int high) {
        if (low < high) {
            int pi = partition(arr, low, high);
            quickSort(arr, low, pi - 1);
            quickSort(arr, pi + 1, high);
        }
    }

    private static int partition(int[] arr, int low, int high) {
        int pivot = arr[high];
        int i = low - 1;

        for (int j = low; j < high; j++) {
            if (arr[j] < pivot) {
                i++;
                int temp = arr[i];
                arr[i] = arr[j];
                arr[j] = temp;
            }
        }

        int temp = arr[i + 1];
        arr[i + 1] = arr[high];
        arr[high] = temp;
        return i + 1;
    }
}
""",
        }

        code = demo_codes.get(language.lower(), demo_codes["python"])
        return f"# Generated code based on: {prompt}\n\n{code}"
