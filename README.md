# Your GitHub Learning Lab Repository for Introducing GitHub

Welcome to **your** repository for your GitHub Learning Lab course. This repository will be used during the different activities that I will be guiding you through. See a word you don't understand? We've included an emoji 📖 next to some key terms. Click on it to see its definition.

Oh! I haven't introduced myself...

I'm the GitHub Learning Lab bot and I'm here to help guide you in your journey to learn and master the various topics covered in this course. I will be using Issue and Pull Request comments to communicate with you. In fact, I already added an issue for you to check out.

![issue tab](https://lab.github.com/public/images/issue_tab.png)

I'll meet you over there, can't wait to get started!

This course is using the :sparkles: open source project [reveal.js](https://github.com/hakimel/reveal.js/). In some cases we’ve made changes to the history so it would behave during class, so head to the original project repo to learn more about the cool people behind this project.

## iPhone 壁纸重绘工具（OpenAI Images API）

新增 `main.py`，可将一张输入图片重绘为同系列的 iPhone 锁屏/桌面壁纸，并生成两张带 UI 预览图。

### 输出文件
运行后会在 `--outdir` 目录输出 4 张图：

1. `lockscreen_wallpaper.png`
2. `homescreen_wallpaper.png`
3. `lockscreen_preview.png`（日期 + 时间 UI）
4. `homescreen_preview.png`（图标网格 + Dock UI）

### 依赖安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 配置 OpenAI API Key

```bash
export OPENAI_API_KEY="你的key"
```

### CLI 用法

```bash
python main.py \
  --input path/to/img.png \
  --outdir out \
  --time "22:48" \
  --date "3月1日周日 · 农历正月十三"
```

批量模式（递归读取目录内图片）：

```bash
python main.py \
  --input-dir path/to/image_dir \
  --outdir out \
  --time "22:48" \
  --date "3月1日周日 · 农历正月十三"
```

批量模式下会递归处理 `jpg/jpeg/png/webp` 文件，并为每张输入图在 `out` 下创建一个“按文件名命名”的子目录（如 `out/sample/`），在子目录内输出 4 张结果图；若同名文件冲突会自动追加 `-2`、`-3` 后缀。
处理时如果某一张失败，不会中断其它图片，最后会打印失败文件汇总。

### 实现说明
- 使用 OpenAI Images API（`gpt-image-1`）执行图生图编辑，分别生成锁屏/桌面两张壁纸。
- 自动分析输入图平均饱和度与亮度对比度，判断“浓郁 / 清淡”并注入不同配色策略提示词。
- 两张壁纸共享同一个风格锚点（主题语义 + 配色规则），保证统一风格；同时分别使用锁屏/桌面专用构图约束，避免构图雷同。
- 使用 Pillow 叠加锁屏时间日期与桌面图标占位，自动根据背景明暗选择浅色/深色文字并添加轻微阴影提升可读性。
- 目标分辨率为竖屏高清比例 `1290x2796`（iPhone Pro Max 常用比例）。

### 错误处理
- 锁屏图、桌面图、两张预览图分别独立 `try/except`，单步失败不会中断整体流程。
- 若 OpenAI 调用失败，会记录日志并继续尝试其他步骤。
