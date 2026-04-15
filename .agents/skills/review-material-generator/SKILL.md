---
name: review-material-generator
description: Generate Chinese study notes from lecture slides, transcripts, PDFs, homework statements, or other course materials. Use when the user asks for复习资料, 算法讲解, 逐步推导, 例题演算, 考前总结, 课堂内容讲解, or wants concepts explained first and then worked examples. Do not use for pure translation-only tasks or for writing unrelated documents.
---

# Review Material Generator

## Goal
Turn raw course materials into structured, high-utility study notes that are easy for a student to review before homework, quizzes, or exams.

The default audience is a student who may not be fully comfortable with the topic yet. Explain clearly, but keep the course's original notation, terminology, and formulas whenever possible.

## Inputs this skill can handle
- Lecture slides or PDFs
- Lecture transcript / captions
- Homework statements
- Screenshots of notes or formulas
- Code or pseudocode that implements a course algorithm
- Mixed inputs, such as slides + transcript + user questions

## Core workflow

### Step 1: Read the full material before answering
- Scan all provided files first.
- Identify the main topics, algorithm names, formulas, diagrams, and any teacher emphasis.
- If both slides and transcript exist, use the slides for structure and the transcript for intent, emphasis, and clarification.
- Prefer the teacher's own framing when deciding what matters most.

### Step 2: Build a concept map
Before writing, silently organize the material into:
1. Main problem being solved
2. Key assumptions
3. Core definitions
4. Main algorithms or methods
5. Typical failure cases / edge cases
6. Worked examples available in the material
7. Likely exam points or easy-to-confuse places

### Step 3: Write in the default output order
Unless the user asks for another format, use this order:

1. **Overall intuition / what this chapter is about**
2. **Key definitions and formulas**
3. **Algorithm-by-algorithm explanation**
   - What problem it solves
   - Main idea
   - Input / output
   - Step-by-step process
   - Why it works
   - Time / space intuition if relevant
4. **One worked example for each major algorithm**
   - Use real numbers from the course material when possible
   - Show each computation step
   - Do not skip intermediate arithmetic if the goal is learning
5. **Common mistakes / confusing points**
6. **Quick review summary**
   - Short exam-oriented bullets or checklist

### Step 4: Teaching style rules
- Default language: Chinese, unless the user asks otherwise.
- First explain the intuition, then the math, then the worked example.
- Do not assume the student already knows the algorithm.
- Keep notation consistent with the slides.
- When using formulas, explain what each symbol means.
- When a derivation matters, show the algebra instead of only giving the result.
- When there are multiple related algorithms, compare them explicitly.
- If the transcript reveals what the teacher repeatedly emphasized, surface that clearly.

### Step 4.5: Formula rendering rules for Markdown
- Default to **renderable Markdown math**, not code-style pseudo formulas.
- For inline math, use `$...$`.
- For display equations, use `$$...$$` on separate lines.
- Never put formulas inside fenced code blocks unless the user explicitly asks for raw source.
- Use standard LaTeX math notation instead of plaintext programming notation.
  - Write `\beta` instead of `beta`
  - Write `\frac{1}{n}` instead of `(1/n)`
  - Write `L^{T}` instead of `L^T`
  - Write matrix and vector expressions in math environments when practical
- When showing vectors or matrices, prefer readable LaTeX forms such as:
  - `$$v_0 = \begin{bmatrix} 1/3 \\ 1/3 \\ 1/3 \end{bmatrix}$$`
  - `$$M = \begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix}$$`
- Do not use `*` for multiplication inside formulas unless the user explicitly wants programming-style notation.
- Surround formulas with short explanatory text so the note still reads well if a Markdown viewer has weak math support.
- If the output target is explicitly a plain-text-only Markdown viewer, provide a second fallback line in readable plaintext after the rendered formula when useful.
- Prefer KaTeX-compatible LaTeX.
- Avoid shorthand forms that may fail in some Markdown renderers.
- Always write fractions as \frac{a}{b}, not \fracab.
- Keep display math blocks separated by blank lines.
- In display math, do **not** put `=`, `+`, or `-` on a line by themselves.
- Keep operators on the same line as the expression they belong to, e.g. write `v_1 = A + B = C` inside one math block rather than breaking before `+` or `=`.
- If a derivation needs multiple steps, prefer either:
  - one compact display block with operators kept inline, or
  - multiple shorter display blocks separated by prose such as “也就是：” or “下一步：”
- Avoid display-math layouts that begin a new line with `+ \begin{bmatrix}`, `= \begin{bmatrix}`, etc., because some Markdown renderers may misread them as list items or headings when math parsing fails.

### Step 5: Example selection rules
When picking examples:
- Prefer examples already present in the slides.
- If the slides do not include enough arithmetic detail, reconstruct the missing intermediate steps.
- If no usable example exists, create the smallest clean example that still demonstrates the full algorithm.
- For graph / matrix topics, write out the matrix and each iteration explicitly.
- For ranking / probability topics, verify that the probabilities sum correctly.

### Step 6: Accuracy and honesty rules
- Do not invent slide content.
- If a formula or graph is ambiguous, say what is certain and what is inferred.
- If the material is incomplete, still provide the best possible explanation, but label assumptions.
- If the user's question is narrower than the whole chapter, focus on that part first.

## Output templates

### Template A: Full study note
Use when the user asks for “详细讲”, “复习资料”, “整理一份总结”, “按知识点讲一遍”.

Structure:
- 本章主线
- 涉及的算法 / 方法
- 算法 1 详解
- 算法 1 例题演算
- 算法 2 详解
- 算法 2 例题演算
- 易错点
- 考前速记版

### Template B: One-algorithm deep dive
Use when the user asks only about one method.

Structure:
- 这个算法在解决什么问题
- 核心思想
- 公式和符号解释
- 计算流程
- 完整例子
- 容易错在哪里

### Template C: Exam crammer version
Use when the user asks for “速通”, “考前”, “cheat sheet”, “最后复习”.

Structure:
- 必背定义
- 核心公式
- 3 个最常考理解点
- 1 个典型例题
- 题目中看到什么关键词就该想到什么

## Special handling by topic type

### For graph / link analysis / Markov chain topics
- Explicitly define the graph, adjacency or transition matrix, and meaning of each row/column.
- Show at least one iteration of the vector update.
- If there is convergence, explain the limit intuitively.
- Distinguish clearly between intuition and formal condition.

### For clustering / iterative ML algorithms
- State objective, update rule, stopping condition, and sensitivity to initialization.
- Compare nearby algorithms if the lecture bundles them together.

### For SQL / database or systems algorithms
- Explain the workflow as a pipeline.
- Show one concrete input and output example.
- Call out failure cases and trade-offs.

## Interaction rules
- If the user asks for formulas that render in Markdown, prefer LaTeX math syntax by default.
- If the user says their viewer does not support math rendering, switch to a plaintext-friendly fallback layout.
- Do not ask unnecessary clarification questions if the materials already define the scope.
- If the user says “先讲算法，再用例子算”, follow that exact order.
- If the user says “一个一个讲”, handle one algorithm at a time.
- If the user is clearly studying for an exam, bias toward clarity, step-by-step arithmetic, and contrastive explanations.

## Quality checklist before finalizing
- Did I explain the chapter's main problem first?
- Did I preserve the course notation?
- Did I include formulas and explain symbols?
- Are formulas written in renderable Markdown math rather than fenced code blocks?
- Did I give at least one full worked example?
- Did I point out confusing parts or traps?
- Did I avoid unexplained jumps in the math?
