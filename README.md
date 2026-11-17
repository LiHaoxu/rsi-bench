# RSI Atlas · Bench

推荐系统自进化的轻量评测资源入口，和 [RSI Survey](https://LiHaoxu.github.io/rsi-survey/) 独立维护。

- 站点目标地址：<https://LiHaoxu.github.io/rsi-bench/>
- 资源核验截至：2026-11-17。
- 当前内容：8 个数据集、7 个工具、4 套建议协议，0 条本站统一运行结果。
- 本仓库不包含模型训练执行器；不以静态网页生成替代实验复现。

## 页面与数据

- `index.html`：数据集、框架与模拟器，可搜索、筛选、展开来源。
- `protocols.html`：自训练、持续学习、交互策略、智能体反馈四套建议协议。
- `results.html`：实际结果状态、提交说明和模板下载。
- `data/resources.json`：资源描述、适用边界、官方链接和建议协议的唯一内容源。
- `data/results.json`：实测记录数组，当前为空。
- `data/result-template.json`：合法 JSON 格式的未运行模板，包含 `null` 占位值，预期无法通过实测结果校验。
- `config.json`：维护者、GitHub 仓库与 Survey / Bench 入口。
- `scripts/build.py`：Python 标准库静态生成器。
- `scripts/validate_result.py`：结构与数值一致性校验器，不执行实验。

## 生成与预览

Python 3.9 或以上，无第三方依赖。在本仓库目录运行：

```sh
python3 scripts/build.py
python3 -m http.server 8766 --directory ..
```

打开 <http://localhost:8766/rsi-bench/>。这里从父目录提供服务，使并排放置的 Survey / Bench 相对入口也能跳转。单个页面也可直接打开 `index.html` 阅读；目录内容已预渲染，搜索不依赖请求 JSON。线上相对入口适用于同一个 GitHub Pages 用户域名。

`python3 scripts/build.py --stage` 同时生成只含网页、样式、脚本和公开数据的 `_site/`，供 Pages 发布。源码与模板一并提交，`_site/` 不入 Git。

## 更新资源

修改 `data/resources.json`，保留稳定的 `id`。每个数据集和工具必须列出官方 `url`、核验 `sources`、适用边界与 `verified` 日期。不要根据名称猜测代码地址。数据集版本、反馈类型、切分方法和模拟假设需要明确。

Bench 的数据与工具目录是复现资源，收录范围与 Survey 的精选论文范围不同。资源对应的论文链接用于追溯来源，不表示它自动满足 Survey 的论文收录条件。更新内容后运行生成脚本，提交 JSON 和生成 HTML。

## 提交结果

1. 复制 `data/result-template.json`，填写真实测量信息，把 `status` 改为 `measured`。
2. 至少提供 3 个独立 seed，并包含第 0 轮与至少 1 个更新轮次。
3. 每轮使用相同指标名，每个指标包含 `per_seed`、`mean` 和 `std`；`std` 为样本标准差（`ddof=1`），保留足够精度。
4. `cost` 为列出的所有 seed 和轮次的总成本。没有发生的成本填 0；未知成本保留在草稿中，不可用 0 掩盖。
5. 给出完整 40 位 Git commit SHA、数据版本、切分与候选协议，以及包含配置和日志的 `evidence_artifact_url`。
6. 运行 `python3 scripts/validate_result.py path/to/measured-result.json`，通过后追加到 `data/results.json`，用 Pull Request 提交证据。

校验器会拒绝缺字段、空信息、NaN / Infinity、`null`、负标准差、负成本、seed 不足、轮次不足、逐 seed 覆盖不全和汇总值不一致。指标均值与逐 seed 数值允许为负，以记录性能退化、带符号的奖励及估计值；标准差和成本必须非负。具体指标的取值范围仍需按指标定义人工核对。通过只表示结构与数值自洽；它不下载证据、不执行实验、不授予独立复现认证。

不同数据版本、切分、候选池、backbone 或预算的结果不合并为总排名。详细协议见 `protocols.html`；每次实际实验还需冻结具体参数，网站的建议协议本身不构成已执行的预注册。

## GitHub Pages

仓库的 Pages Source 选择 **GitHub Actions**。推送 `main` 后，`.github/workflows/pages.yml` 重新生成并校验静态站点，再上传 `_site/` 到 Pages。发布目录不包含本地实验、私有日志、凭据或训练数据。

## 内容来源

资源均链接到作者、数据提供方、官方代码仓库或正式论文。对模拟环境、数据版本差异以及归档状态做显式记录。论文和代码的版权、许可分别归原作者；数据以原发布方的使用条款为准。
