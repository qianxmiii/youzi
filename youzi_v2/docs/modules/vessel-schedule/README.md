# 船期域（vessel-schedule）

## 模块名称

Vessel Schedule — 航次船期与挂靠监控

## 功能说明

管理船名航次、多港挂靠时间（ETA/ATA/ETD/ATD），支持 Excel 导入、外部数据源同步，并与运单通过 `vessel_voyage` 关联。

## 主要文件

### 后端

| 路径 | 作用 |
|------|------|
| `db/vessel_voyages_table.py` | 航次 + 挂靠表 |
| `db/vessel_schedules_repository.py` | 查询与 upsert |
| `db/port_subscriptions_table.py` | 港口到港订阅 |
| `services/vessel_schedule_excel.py` | Excel 导入 |
| `services/vessel_schedule_sync.py` | 外部同步 |
| `services/maritime_schedule/` | 船期 Provider 注册 |
| `schemas/vessel_schedules.py` | API 模型 |

### 前端

| 路径 | 作用 |
|------|------|
| `views/vessel-schedules/VesselSchedulesView.vue` | 主页面（筛选栏 + 航次横幅 + 挂靠时间轴） |
| `components/vessel-schedules/VesselScheduleActiveBanner.vue` | 当前船舶/航次/承运商/下一港摘要横幅 |
| `components/vessel-schedules/VoyageTimeline.vue` | 挂靠港时间轴表格（分页、订阅、延误高亮） |
| `components/vessel-schedules/VoyageFormModal.vue` | 新建/编辑航次 |
| `components/vessel-schedules/CarrierVesselSelect.vue` | 船司船舶检索 |
| `api/vesselSchedules.ts` | API 客户端 |

## 数据结构

- `vessel_voyages`：航次主表，`vessel_voyage` 唯一
- `voyage_port_calls`：挂靠港，`sequence` 排序

见 [database.md](../../database.md#vessel_voyages--voyage_port_calls船期)。

## API 接口

前缀 `/api/v1/vessel-schedules`，详见 [api.md](../../api.md#船期-vessel-schedules)。

## 业务流程

```text
Excel/手工录入/外部同步 → upsert 航次 + 挂靠港
                        → 运单 vessel_voyage 匹配 → 展示关联运单
                        → 港口订阅 → 海运预警
```

## 注意事项

- 同一 `vessel_voyage` Excel 多行 = 多港挂靠
- 导入为 upsert，以 `vessel_voyage` 为键
- 外部船期 Provider 见 `GET /providers`
