# 个人主页自动更新配置

修改根目录的 `profile-config.json` 即可控制收录，不要直接修改 README 中自动生成的项目表格。

## 默认行为

| 设置 | 默认 | 含义 |
| --- | --- | --- |
| `showcase` | false | 新公开仓库不会自动出现在项目列表；现有项目已显式保留 |
| `stats` | true | 自己的公开、非 Fork 仓库参与统计 |
| `notify` | false | 不自动向其他仓库安装通知工作流或写入密钥 |

私有仓库、Fork、其他所有者的仓库及主页仓库本身始终排除。统计卡的 Stars、Forks、仓库数和代码行数使用同一筛选集合，因此首次更新的数字可能变化。排除展示不等于仓库变私有。

## 常见配置

在 `repositories` 中添加或修改对应条目，仓库名匹配不区分大小写：

```json
"my-public-tool": {"showcase": true},
"my-experiment": {"showcase": false, "stats": false, "notify": false}
```

这是对象内条目示例，需注意逗号，保持整个文件为有效 JSON。未填写的开关继承 defaults。删除条目意味着恢复默认，并不等于全部排除。

想恢复所有公开仓库自动展示，可将 `defaults.showcase` 改成 true，再给不想展示的仓库设置 `showcase: false`。分类和描述仍由 `.github/scripts/gen_repos.py` 管理；明确收录但未分类的仓库进入“更多项目”。中文和英文列表共用规则。

## 刷新方式

每天北京时间 10:17 计划刷新（GitHub 可能延迟），配置推送后也会触发。还可以在 Actions → readme-stats → Run workflow 手动刷新。已有仓库通知仍可触发刷新。

跨仓库写入已改为单独手动选择：只有手动运行时勾选 `sync_notifications`，并为目标仓库设置 `notify: true`，才会尝试写入通知工作流和 `PROFILE_REPO_TOKEN`。需要已有的 `SYNC_TOKEN` 权限；普通刷新不使用它。归档仓库不会接入。

**`notify: false` 只阻止今后的接入与更新，不会撤销旧配置。** 之前安装的 `.github/workflows/notify-profile.yml` 和 `PROFILE_REPO_TOKEN` 不会自动删除。若要完全停止某仓库通知，在该仓库移除这个工作流及专用 secret；本次迁移没有自动修改其他仓库。

## 验证

```sh
python -m unittest discover -s tests
```

测试不联网、不访问密钥、不写其他仓库。配置缺失、类型错误或未知字段会令任务失败，不会静默恢复全量收录。配置更新后查看 Actions 日志及 README 自动提交，确认结果符合预期。
