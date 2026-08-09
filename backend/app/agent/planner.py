"""
TripPlannerAgent: 行程规划 Agent 核心

封装行程规划 Agent 的核心决策逻辑——理解用户意图、构建 Prompt、调用 LLM、解析行程结果、处理用户反馈。
"""
from openai.types.shared_params import response_format_text
from redis.asyncio import Redis


from backend.app.services.prompt_builder import PromptBuilder
from backend.app.agent.conversation import ConversationManager
from backend.app.services.llm_client import LLMClient
from backend.app.crud.trip import find_trip_by_id, update_trip
from backend.app.tools import get_tool_schema, execute_tool
import json
import re
from backend.app.config import settings
from backend.app.memory.preferences import load_preferences, extract_preferences, save_preferences

MAX_TOOL_ROUND = 10


class TripPlannerAgent:
    """行程规划 Agent 核心"""

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm_client = LLMClient()

    async def handle_message(self, user_input: str, conversation: ConversationManager, r: Redis):
        """Agent 主入口：接收用户消息，返回 Agent 回复（流式）"""
        conversation.pref = await load_preferences(r, conversation.user_id)

        # 1. 保存用户消息
        await conversation.add_message("user", user_input)

        # 2. 意图判断及分支选择
        intent = await self.llm_classify_intent(user_input, conversation)

        if intent == "new_trip":
            stream = self._generate_plan(conversation)
        elif intent == "modify_trip":
            # 找到对应行程才能修改
            trip = await find_trip_by_id(conversation.db, conversation.trip_id)
            if trip is None:
                yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
                return
            if trip.plan_data is None:
                yield {"type": "token", "content": "当前还没有行程方案，我先帮你规划一个吧！\n"}
                stream = self._generate_plan(conversation)
            else:
                stream = self._apply_feedback(user_input, trip.plan_data, conversation)
        elif intent == "ask_question":
            async for chunk in self.gossip(conversation):
                yield chunk
            return
        else:
            yield {"type": "token", "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"}
            yield {"type": "done", "data": {}}
            return

        # 3. 消费流式生成器，按事件类型分流：
        #    - token 事件 → 拼进 full_text，同时转发给前端（打字机）
        #    - thinking/tool 事件 → 原样透传，不进入消息文本
        full_text = ""
        async for chunk in stream:
            if chunk["type"] == "token":
                full_text += chunk["content"]
                yield {"type": "token", "content": chunk["content"]}
            else:
                yield chunk

        # 4. 从回复中分离自然语言文本与结构化 JSON
        display_text, plan_data = self._extract_plan_json(full_text)


        # 4.5 Critic 质量审查（v0.8.0）—— 判定树
        # 审查条件（两个都要满足）：
        #   1. settings.CRITIC_ENABLED —— 总开关开启（测试环境用 env 关掉，避免真打 DeepSeek）
        #   2. plan_data is not None   —— 有方案才审（没解析出合法 JSON 则无可审对象）
        if plan_data is not None and settings.CRITIC_ENABLED:
            yield {"type": "thinking", "content": "正在对行程方案做质量审查…"}
            critic_result = await self._ask_critic(user_input=user_input, conversation=conversation, plan_data_json=plan_data)

            # 进入重生成的条件（缺一不可）：
            #   1. critic_result 非空 —— 审查成功（失败降级返回 None，直接用原方案，不阻断主流程）
            #   2. not passed —— 审查不达标
            #   3. issues 非空 —— 审查员给出了可执行的修正项（只有明确了问题才值得再花一次生成）
            if critic_result and not critic_result["passed"] and critic_result["issues"]:
                yield {"type": "thinking", "content": "审查发现部分安排需要优化，正在重新生成方案"}
                # 重生成循环：最多 CRITIC_MAX_REGENERATE 次（默认 1 次），防无限循环烧 token。
                # 每次产出合法 JSON 即采纳；全失败则保持 v1 原方案，流程继续。
                for _ in range(settings.CRITIC_MAX_REGENERATE):
                    new_text = await self._regenerate_plan(
                        plan_data=plan_data,
                        user_input=user_input,
                        issues=critic_result["issues"],
                        conversation=conversation,
                    )
                    new_display, new_plan = self._extract_plan_json(new_text)
                    if new_plan is not None:
                        display_text, plan_data = new_display, new_plan
                        break


        # 5. 保存解析出的行程数据
        if plan_data is not None:
            try:
                await update_trip(conversation.db, conversation.trip_id, plan_data=plan_data)

            except Exception as e:
                print(f"[ERROR] 保存行程失败: {e}")

        # 6. 保存 AI 回复（自然语言部分，不含 JSON 代码块）
        await conversation.add_message("assistant", display_text)
        new_pref = extract_preferences(user_input)
        if new_pref:
            await save_preferences(r, conversation.user_id, new_pref)

        # 7. 结束 — 把 trip_id 带回前端，让前端知道"刚聊的是哪个行程"
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}

    def _extract_plan_json(self, full_text: str) -> tuple[str, dict | None]:
        """从 LLM 回复中分离自然语言文本与 ```json 代码块。

        返回 (display_text, plan_data)。display_text 是展示给用户的自然语言，
        plan_data 是解析后的行程 JSON；如果未找到 JSON 块，则 plan_data 为 None，
        display_text 为原始文本。
        """
        plan_data = None

        # 优先：按 ```json / ``` 标记拆分
        parts = full_text.split("```json", 1)
        if len(parts) == 2:
            display_text = parts[0].strip()
            json_part = parts[1]
            end = json_part.rfind("```")
            if end != -1:
                json_str = json_part[:end].strip()
            else:
                json_str = json_part.strip()

            if json_str:
                try:
                    plan_data = json.loads(json_str)
                except (json.JSONDecodeError, TypeError):
                    pass

            if plan_data is not None:
                return display_text, plan_data

        # 回退 1：尝试按普通的 ``` 标记提取 JSON
        triple_parts = full_text.split("```", 1)
        if len(triple_parts) == 2:
            # 第一个 ``` 之后、最后一个 ``` 之前的内容
            rem = triple_parts[1]
            end2 = rem.rfind("```")
            candidate = (rem[:end2] if end2 != -1 else rem).strip()
            # 去掉可能的前导 "json" 标记
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            try:
                plan_data = json.loads(candidate)
                display_text = full_text.split("```")[0].strip()
                return display_text, plan_data
            except (json.JSONDecodeError, TypeError):
                pass

        # 回退 2：兼容没有 ```json 标记的纯 JSON 输出
        match = re.search(r'\{.*}', full_text, re.DOTALL)
        if match:
            try:
                plan_data = json.loads(match.group())
                display_text = full_text.replace(match.group(), "").strip()
                return display_text, plan_data
            except (json.JSONDecodeError, TypeError):
                pass

        print(f"[WARN] 未在回复中找到有效 JSON，原始输出前200字: {full_text[:200]}")
        return full_text, None

    async def llm_classify_intent(self, user_input: str, conversation):
        """LLM轻量意图识别"""
        intent_classifier_prompt = self.prompt_builder.build_intent_classifier_prompt()

        # 构建 messages
        message = [{
            "role": "system",
            "content": intent_classifier_prompt
        }]

        # 检查对话历史
        context_hint = ""
        if conversation.trip_id != 0:
            context_hint = (
                f"当前对话有一个已存在的行程（ID={conversation.trip_id}），"
                f"状态为 {conversation.state.value}。"
                f"如果用户提到修改、调整、更换等，应归类为 modify_trip。"
            )

        # 将上下文历史加入 messages
        if context_hint != "":
            message.append({
                "role": "system",
                "content": context_hint
            })
        message.append({
            "role": "user",
            "content": user_input
        })

        try:
            resp = await self.llm_client.client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=message,
                stream=False,
                timeout=settings.LLM_REQUEST_TIMEOUT,
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(resp.choices[0].message.content)
            intent = result.get("intent", "unclear")
            if intent not in ("new_trip", "modify_trip", "ask_question", "unclear"):
                intent = "unclear"
            return intent
        except Exception as e:
            print(f"[WARN] LLM 意图分类失败，回退关键词: {e}")
            # 4. fallback 到关键词匹配
            return self._keyword_classify(user_input)

    def _keyword_classify(self, user_input: str):
        """老方法：关键词匹配"""
        text = user_input.strip()

        # 修改意图的关键词
        modified_keywords = ["修改", "调整", "换", "去掉", "增加", "改成", "不要", "换个"]
        if any(kw in text for kw in modified_keywords):
            return "modify_trip"

        # 新行程的关键词
        new_keywords = ["规划", "想去", "安排", "帮我", "推荐", "三日", "几日", "旅游", "旅行"]
        if any(kw in text for kw in new_keywords):
            return "new_trip"

        # 提问类
        question_keywords = ["?", "？", "怎么样", "如何", "什么是", "介绍一下"]
        if any(kw in text for kw in question_keywords):
            return "ask_question"

        return "unclear"

    async def _ask_critic(self, plan_data_json : dict, user_input: str, conversation):
        """构造 Prompt 调用 LLM 开始审查 Json"""
        extra_system = self.prompt_builder.build_critic_prompt()

        """ 拼接 message """
        messages = [
            {"role": "system", "content": extra_system}
        ]

        messages.append(
            {"role": "user", "content": (
                f"用户需求：{user_input}\n"
                f"{self.prompt_builder.render_preferences(conversation.pref)}\n"
                f"请审查以下行程 JSON：\n"
                f"{json.dumps(plan_data_json, ensure_ascii=False, indent=2)}"
            )}
        )

        """非流式调用LLM + 解析审查结果"""
        # 整个审查调用都可能失败（网络错误 / 返回非 JSON / 字段缺失），
        # 必须 try 包住，失败返回 None → 上层判定树降级用原方案，不阻断主流程
        try:
            response = await self.llm_client.client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                timeout=settings.LLM_REQUEST_TIMEOUT,
                temperature=0,
                messages=messages,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            passed = result.get("passed")
            scores = result.get("scores", {})
            issues = result.get("issues", [])
            # 防御：LLM 可能自相矛盾（passed=True 但给了修正项），保守按不达标处理，
            # 保证「有 issues 就触发重生成」这一判定树规则不被绕过
            if issues and passed is True:
                passed = False
            if not isinstance(issues, list):
                issues = []
            issues = [str(i) for i in issues][:3]
        except Exception as e:
            print(f"[WARN] 审查结果解析失败: {e}")
            return None

        return{"passed": passed, "scores": scores, "issues": issues}






    async def _generate_plan(self, conversation, tool_defs=None):
        """构造 Prompt 调用 LLM 生成行程"""
        context = await conversation.get_context(max_tokens=30000, token_counter=self.llm_client.count_tokens)

        if not context:
            yield {"type": "token", "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"}
            return

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref
        )

        if tool_defs is None:
            tool_defs = get_tool_schema()

        thoughts : list[str] = []

        # 非流式调用LLM
        message = await self.llm_client.chat(messages, tool_defs)
        if not message.tool_calls:
            # 没有工具调用的需求，则yield流式输出
            async for chunk in self.llm_client.chat_stream(messages):
                yield {"type": "token", "content": chunk}
            return
        tool_round = 0
        while tool_round < MAX_TOOL_ROUND:
            tool_round += 1

            messages.append({
                "role": "assistant",
                "content": message.content,  # 可能为 None
                "tool_calls": message.tool_calls  # tool_calls 列表
            })



            tool_names = ", ".join(tool_call.function.name for tool_call in message.tool_calls)

            yield {"type": "thinking", "content": f"我现在要使用 {tool_names} 工具以确认安排"}

            observations = []

            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                result = await execute_tool(fn_name, **fn_args)

                observations.append(f"{fn_name}({fn_args}) → {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            # 在 observations 循环结束、调用下一轮 LLM 之前
            summary = "; ".join(obs[:120] for obs in observations)
            thoughts.append(f"第{tool_round}轮：调用了 {tool_names}，结果：{summary[:150]}")

            messages.append({
                "role": "assistant",
                "content": (
                        "[内部推理] 我目前已掌握的信息：\n"
                        + "\n".join(f"- {t}" for t in thoughts[-3:])
                        + "\n\n请基于以上信息评估：是否已满足用户需求？"
                          "若已满足，直接组织最终行程回答，不要调用工具；"
                          "若关键信息仍有缺失，再调用工具补充。"
                ),
            })

            message = await self.llm_client.chat(messages, tool_defs)

            if not message.tool_calls:
                async for chunk in self.llm_client.chat_stream(messages):
                    yield {"type": "token", "content": chunk}
                return

        # 调用上限后的兜底处理
        # ← 走到这里说明 10 轮工具调用后 LLM 还在要工具
        print(f"[WARN] 工具调用超过 {MAX_TOOL_ROUND} 轮，强制结束")
        # 兜底：把当前上下文流式输出
        async for chunk in self.llm_client.chat_stream(messages):
            yield {"type": "token", "content": chunk}

    async def _regenerate_plan(self, plan_data: dict, user_input: str, issues: list, conversation):
        """根据审查反馈重生成一版行程方案（轻量单轮流式，服务端累积，不 yield 给前端）。

        输入：
            plan_data   : v1 的行程 JSON dict（审查不达标的那版）
            user_input  : 用户原始需求（重生成时带回去，避免丢初始约束）
            issues      : 审查员给出的修正项列表（如 ["预算超支", "第2天太赶"]）
            conversation: 会话管理器（取 history_cache / pref 拼 prompt）

        返回：
            str —— 重生成的完整文本（含自然语言 + ```json 代码块，调用方再 _extract_plan_json 解析）

        设计要点（对齐 _apply_feedback 范式）：
            - 把「v1 行程 JSON + 用户需求 + 逐条 issues」拼进 extra_system
            - 复用 build_messages 拼 messages：带 user_input（初始约束）+ pref（偏好）+ extra_system（修正指令）
            - 走 chat_stream 流式，但只在服务端累积返回，不 yield —— 见 handle_message 说明
        """
        # 1. 把审查反馈（issues 列表）逐条转成 "- 问题" 行，用换行拼接。
        #    f"- {issue}" 逐条加前缀；issues 非空由调用方判定树保证，这里无需判空
        issue_lines = "\n".join(f"- {issue}" for issue in issues)

        # 2. 拼接修正指令：v1 JSON + 用户需求 + 审查问题 + 输出规范（照抄 _apply_feedback 的写法）
        regenerate_prompt = f"""以下是刚生成的行程 JSON：
        {json.dumps(plan_data, ensure_ascii=False, indent=2)}

        用户原始需求：{user_input}

        质量审查发现以下问题，请逐条修正：
        {issue_lines}

        请保持用户原始需求与行程主体不变，只在问题范围内做局部调整。
        先用自然语言简要说明你做了哪些优化，然后在回复末尾用 ```json 代码块返回修正后的完整行程 JSON，字段结构与原 JSON 保持一致，不要省略任何字段。"""

        # 3. 复用 build_messages 拼 messages：
        #    user_input 当 user 消息（初始约束不丢）+ pref 偏好段 + extra_system 修正指令
        messages = self.prompt_builder.build_messages(
            history=conversation.history_cache,
            user_input=user_input,
            pref=conversation.pref,
            extra_system=regenerate_prompt,
        )

        # 4. 服务端累积流式输出，返回完整文本（不 yield 给前端，理由见 handle_message）
        full_text = ""
        async for chunk in self.llm_client.chat_stream(messages):
            full_text += chunk
        return full_text






    async def _apply_feedback(self, feedback: str, current_plan: dict, conversation):
        """根据用户反馈调整现有行程"""
        modify_prompt = f"""以下是当前行程的完整 JSON：
        {json.dumps(current_plan, ensure_ascii=False, indent=2)}
        
        用户要求：{feedback}
        
        请在现有行程基础上做局部调整。只修改用户提到的部分，其余保持不变。
        先用自然语言说明你做了哪些调整，然后在回复末尾用 ```json 代码块返回修改后的完整行程 JSON。"""
        # 保留原始 system prompt 的角色定义，再追加修改指令

        messages = self.prompt_builder.build_messages(
            history=conversation.history_cache,
            user_input=feedback,
            pref=conversation.pref,
            extra_system=modify_prompt,
        )

        async for chunk in self.llm_client.chat_stream(messages):
            yield {"type": "token", "content": chunk}

    async def gossip(self, conversation):
        context = await conversation.get_context(max_tokens=30000, token_counter=self.llm_client.count_tokens)

        if not context:
            yield {"type": "token", "content": "能再详细说说您的旅行需求吗？比如目的地、天数、预算？"}
            return

        # context 按时间升序排列，最后一条是当前用户消息
        # 拆开：前面的当历史上下文，最后一条单独当 user_input，避免重复
        history = context[:-1]
        user_input = context[-1]["content"]

        messages = self.prompt_builder.build_messages(
            history=history,
            user_input=user_input,
            pref=conversation.pref
        )

        full_text = ""

        async for chunk in self.llm_client.chat_stream(messages):
            full_text += chunk
            yield {"type": "token", "content": chunk}

        await conversation.add_message("assistant", full_text)
        yield {"type": "done", "data": {"trip_id": conversation.trip_id}}
