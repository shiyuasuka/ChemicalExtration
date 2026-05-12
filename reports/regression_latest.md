# KnowMat 回归测试报告

**生成时间**: 2026-03-14T23:08:38.710818

**对比论文数**: 6/6

---

## 总体指标

### 结构指标

| 指标 | AI 均值 | GT 均值 | AI/GT 比率 |
|------|---------|---------|------------|
| Materials per paper | 1.67 | 2.0 | 83.5% |
| Samples per paper | 2.33 | 3.0 | 77.7% |
| Properties per paper | 25.7 | 21.0 | 122.4% |

### 字段准确率

| 字段 | 指标 | 数值 | 评价 |
|------|------|------|------|
| DOI | 命中率 | 83.3% | ✅ |
| Main_Phase | AI 填充率 | 100.0% | ✅ |
| Main_Phase | 匹配率 | 78.3% | ✅ |
| Has_Precipitates | 匹配率 | 56.7% | ❌ |
| Process_Category | 匹配率 | 28.3% | ❌ |
| Process_Category | Unknown 占比 | 0.0% | ✅ |
| Grain_Size | AI 填充率 | 83.3% | ✅ |

### 温度质量

- **平均偏移**: 158.95 K
- **最大偏移**: 975.00 K
- **偏移测试数** (>1K): 21
- **评价**: ❌ 存在偏移

### 成分质量

- **非法元素问题**: 0 篇
- **原子百分比和异常**: 5 篇
- **Composition_JSON 为空**: 1 篇
- **评价**: ✅ 成分解析质量良好

---

## 逐篇对比详情

### 论文 1

**AI 文件**: `data\output\1-2024-MSEA-Ti₄₂Hf₂₁Nb₂₁V₁₆-DED\1-2024-MSEA-Ti₄₂Hf₂₁Nb₂₁V₁₆-DED_extraction.json`

**GT 文件**: `手工标注结果\1-data.json`

- **Materials**: AI=1, GT=1 ✅
- **Samples**: AI=1, GT=1 ✅
- **Properties**: AI=19, GT=8 ✅
- **DOI**: ✅ 匹配
- **Main_Phase**: AI填充=1/1, 匹配率=100.0% ✅
- **Has_Precipitates**: 匹配率=100.0% ✅
- **Process_Category**: 匹配率=100.0%, Unknown=0/1 ✅
- **温度偏移**: 平均=0.00K, 最大=0.00K ✅
- **成分问题**: ✅ 无问题

### 论文 2

**AI 文件**: `data\output\2-2025-Acta-Nb₁₅Ta₁₀W₇₅---添加NbC 纳米沉淀\2-2025-Acta-Nb₁₅Ta₁₀W₇₅---添加NbC 纳米沉淀_extraction.json`

**GT 文件**: `手工标注结果\2-data.json`

- **Materials**: AI=2, GT=2 ✅
- **Samples**: AI=4, GT=4 ✅
- **Properties**: AI=66, GT=28 ✅
- **DOI**: ✅ 匹配
- **Main_Phase**: AI填充=4/4, 匹配率=100.0% ✅
- **Has_Precipitates**: 匹配率=0.0% ❌
- **Process_Category**: 匹配率=50.0%, Unknown=0/4 ❌
- **温度偏移**: 平均=140.18K, 最大=975.00K ❌
- **成分问题**: ✅ 无问题

### 论文 3

**AI 文件**: `data\output\3-2024-JMST- Co42Cr20Ni30Ti4Al4\3-2024-JMST- Co42Cr20Ni30Ti4Al4_extraction.json`

**GT 文件**: `手工标注结果\3-data.json`

- **Materials**: AI=1, GT=1 ✅
- **Samples**: AI=2, GT=2 ✅
- **Properties**: AI=18, GT=18 ✅
- **DOI**: ✅ 匹配
- **Main_Phase**: AI填充=2/2, 匹配率=100.0% ✅
- **Has_Precipitates**: 匹配率=100.0% ✅
- **Process_Category**: 匹配率=0.0%, Unknown=0/2 ❌
- **温度偏移**: 平均=0.00K, 最大=0.00K ✅
- **成分问题**: ✅ 无问题

### 论文 4

**AI 文件**: `data\output\4-2025-IJP-Ni₆₁.₃Cr₂₅.₃W₄.₄Mo₁.₄Fe₁.₇Co₁.₄Al₁.₁Mn₀.₄Si₀.₇C₂.₅La₀.₀₁₃\4-2025-IJP-Ni₆₁.₃Cr₂₅.₃W₄.₄Mo₁.₄Fe₁.₇Co₁.₄Al₁.₁Mn₀.₄Si₀.₇C₂.₅La₀.₀₁₃_extraction.json`

**GT 文件**: `手工标注结果\4-data.json`

- **Materials**: AI=1, GT=2 ⚠️
- **Samples**: AI=2, GT=5 ⚠️
- **Properties**: AI=16, GT=24 ⚠️
- **DOI**: ❌ AI="10.1016/j.ijplas.2025.104409" vs GT="10.1016/j.msea.2024.147225"
- **Main_Phase**: AI填充=2/2, 匹配率=20.0% ❌
- **Has_Precipitates**: 匹配率=40.0% ❌
- **Process_Category**: 匹配率=20.0%, Unknown=0/2 ❌
- **温度偏移**: 平均=396.88K, 最大=875.00K ❌
- **成分问题**: ❌
  - Ni68.94Cr21.49W13.13Mo2.22Fe1.57Co1.30Al0.46Mn0.34Si0.30La0.029C0.48: Sum=110.3% (expected ~100%)

### 论文 5

**AI 文件**: `data\output\5-2024-IJP-在 FeCoCrNiMox\5-2024-IJP-在 FeCoCrNiMox_extraction.json`

**GT 文件**: `手工标注结果\5-data.json`

- **Materials**: AI=4, GT=4 ✅
- **Samples**: AI=4, GT=4 ✅
- **Properties**: AI=32, GT=32 ✅
- **DOI**: ✅ 匹配
- **Main_Phase**: AI填充=4/4, 匹配率=100.0% ✅
- **Has_Precipitates**: 匹配率=100.0% ✅
- **Process_Category**: 匹配率=0.0%, Unknown=0/4 ❌
- **温度偏移**: 平均=0.00K, 最大=0.00K ✅
- **成分问题**: ❌
  - FeCoCrNi: Composition_JSON is empty
  - FeCoCrNiMo0.1: Sum=0.1% (expected ~100%)
  - FeCoCrNiMo0.3: Sum=0.3% (expected ~100%)

### 论文 6

**AI 文件**: `data\output\6-2024-MSEA- FeCoCrNiMo0.5\6-2024-MSEA- FeCoCrNiMo0.5_extraction.json`

**GT 文件**: `手工标注结果\6-data.json`

- **Materials**: AI=1, GT=2 ⚠️
- **Samples**: AI=1, GT=2 ⚠️
- **Properties**: AI=3, GT=16 ⚠️
- **DOI**: ✅ 匹配
- **Main_Phase**: AI填充=1/1, 匹配率=50.0% ❌
- **Has_Precipitates**: 匹配率=0.0% ❌
- **Process_Category**: 匹配率=0.0%, Unknown=0/1 ❌
- **温度偏移**: 平均=416.67K, 最大=575.00K ❌
- **成分问题**: ❌
  - FeCoCrNiMo0.5: Sum=0.5% (expected ~100%)

---

*报告生成工具: KnowMat regression_diff.py*
