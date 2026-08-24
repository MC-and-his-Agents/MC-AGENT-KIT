# 方法论参考

## 何时读取

仅在解释理论依据时读取。普通生成任务不需要加载本文件。

## 概念来源映射

| Skill 概念 | 主要领域依据 | 在本 Skill 中的操作化 |
|---|---|---|
| Mise-en-scène | 电影研究与电影制作 | 把人物、造型、道具、空间、色彩和灯光组织为同一个视觉世界 |
| Shot Design / Previsualization | 导演与电影摄影 | 在生成前决定 blocking、景别、机位、构图和可见信息 |
| Motivated Lighting | 电影摄影与摄影布光 | 从场景中的光源推导方向、颜色、表面响应和主体分离 |
| Figure–Ground / Visual Hierarchy | 视觉感知与设计 | 区分主视觉、支撑信息和环境语境 |
| Material Definition | 摄影布光与表面反射 | 根据黑色、金属、玻璃、织物、皮肤等不同表面选择光线与描述 |
| Attribute / Spatial Binding | 文生图组合性研究 | 用“实体 → 属性 → 关系”降低颜色、数量和位置错配 |
| Causal Coherence / Visibility / Decision Closure | 本 skill 的工作综合 | 消除视觉结果无原因、关键信息不可见和最终 prompt 仍在 brainstorming 的问题 |
| Locked / Editable / Failure-aware Prompting | 生成与编辑实践综合 | 控制参考图漂移，并只针对当前构图的主要失败风险加约束 |

## 核心参考

- [*Film Art: An Introduction* — David Bordwell, Kristin Thompson, Jeff Smith](https://www.mheducation.com/highered/product/film-art-an-introduction-bordwell.html)：mise-en-scène、电影摄影、镜头关系和电影形式的基础框架。
- [*Cinematography: Theory and Practice* — Blain Brown](https://www.routledge.com/Cinematography-Theory-and-Practice-For-Cinematographers-and-Directors/Brown/p/book/9780367373467)：构图、镜头、连续性、光线、色彩和视觉叙事的制作实践。
- [*Film Directing: Shot by Shot* — Steven D. Katz](https://mwp.com/product/film-directing-shot-shot-25th-anniversary-edition-visualizing-concept-screen/)：场面设计、blocking、镜头预演和从概念到画面的导演决策。
- [*Light — Science & Magic* — Fil Hunter, Steven Biver, Paul Fuqua, Robin Reid](https://www.routledge.com/Light----Science--Magic-An-Introduction-to-Photographic-Lighting/Hunter-Biver-Fuqua-Reid/p/book/9780367860271)：反射、透射及黑色、金属、玻璃、液体和人像的布光原则。
- [Wagemans et al., *A Century of Gestalt Psychology in Visual Perception I*](https://pmc.ncbi.nlm.nih.gov/articles/PMC3482144/)：视觉分组和 figure–ground 组织的现代综述。
- [T2I-CompBench](https://arxiv.org/abs/2307.06350)：把文生图组合能力分为属性绑定、对象关系、空间关系和复杂组合等可评估问题。
- [Attend-and-Excite](https://arxiv.org/abs/2301.13826)：说明文生图模型可能忽略主体或把属性绑定给错误主体；本 skill 只吸收问题认识，不绑定其特定算法。
