# TrackNarrator SPEC — schema v0.1.2 (Barber‑aligned, unified)
Updated: 2025-10-28

> 此版將 v0.1.1（Barber sample 對齊）與「TRD Telemetry CSV (R1/R2) 長表格匯入說明」合併成單一規格。
> 不破壞 v0.1/v0.1.1 相容性，僅補充欄位與匯入策略。

## 目標
以 TRD 2025 Hackathon 提供之資料為基準，建立 v0 的統一資料結構與匯入標準：
- 來源：TRD/MYLAPS/RaceChrono/GPX/Weather（CSV/ZIP/PDF map）
- 用途：事件偵測（單圈異常、名次變化）、敘事/分享卡、AI‑Native（可關閉）
- 產物：SessionBundle（Session+Lap+Section+Telemetry+Weather）

## 單位與時間
- 時間戳 `*_ts`：UTC ISO8601（例：`2025-04-04T18:10:23.456Z`）；圈內/片段/遙測長度用毫秒（`*_ms`）。
- 速度 `speed_kph`：km/h；煞車 `brake_bar`：bar；轉向角 `steer_deg`：degrees；加速度 `acc_long_g/acc_lat_g`：g。
- 經緯度 `lat_deg/lon_deg`：WGS‑84 十進位度。TRD 欄位 `VBOX_Lat_Min / VBOX_Long_Minutes` 實為十進位度。

## 標準資料結構（Pydantic 形狀）
```python
Session:
  id: str
  source: Literal["trd_csv","mylaps_csv","racechrono_csv","gpx"]
  track: Optional[str]
  track_id: str                         # 例：barber-motorsports-park
  track_map_version: Optional[str]      # 例：pdf:Barber_Circuit_Map
  start_ts: Optional[datetime]
  end_ts: Optional[datetime]
  schema_version: str = "0.1.2"

Lap:
  session_id: str
  lap_no: int
  driver: str
  laptime_ms: int
  start_ts: Optional[datetime]
  end_ts: Optional[datetime]
  position: Optional[int]

Section:
  session_id: str
  lap_no: int
  name: Literal["IM1a","IM1","IM2a","IM2","IM3a","FL"]
  t_start_ms: int
  t_end_ms: int
  delta_ms: Optional[int]
  meta: dict = {"source":"map"}         # "map" | "fallback"

Telemetry:
  session_id: str
  ts_ms: int
  speed_kph: Optional[float]
  throttle_pct: Optional[float]         # aps (%)
  brake_bar: Optional[float]            # pbrake_f; 若缺可回退 pbrake_r
  gear: Optional[int]
  acc_long_g: Optional[float]
  acc_lat_g: Optional[float]
  steer_deg: Optional[float]
  lat_deg: Optional[float]
  lon_deg: Optional[float]

WeatherPoint:
  session_id: str
  ts_ms: int
  air_temp_c: Optional[float]
  track_temp_c: Optional[float]
  humidity_pct: Optional[float]
  pressure_hpa: Optional[float]
  wind_speed: Optional[float]           # m/s
  wind_dir_deg: Optional[float]         # 0-360
  rain_flag: Optional[int]              # 0/1

SessionBundle:
  session: Session
  laps: list[Lap]
  sections: list[Section]
  telemetry: list[Telemetry]
  weather: list[WeatherPoint]
```

## 來源→標準欄位對應（v0）
### TRD（telemetry / lap / time）
- `speed` → Telemetry.speed_kph（~66–190 km/h）
- `gear` → Telemetry.gear（1–5）
- `aps` → Telemetry.throttle_pct（0–100%）；`ath` 可作備援
- `pbrake_f` → Telemetry.brake_bar（0–~150 bar）；若缺則退 `pbrake_r`
- `accx_can`/`accy_can` → Telemetry.acc_long_g/acc_lat_g（約 −1.6~1.5 / −2.9~2.1）
- `Steering_Angle` → Telemetry.steer_deg（約 −114°~+130°）
- `VBOX_Lat_Min`/`VBOX_Long_Minutes` → Telemetry.lat_deg/lon_deg（十進位度）
- `Laptrigger_lapdist_dls` → 切圈/切段輔助指標（不直接入 Telemetry）
- `timestamp`（ECU）與 `meta_time`（接收）：以 `timestamp` 為主，異常時退 `meta_time`

### MYLAPS（official timing CSV）
- `LapTime`/`BestLap` → Lap.laptime_ms（轉毫秒）
- `Position` → Lap.position
- `Driver`/`Car` → Lap.driver（`CarNo` 可作附註）
- 若僅圈時長而無絕對時間，`start_ts/end_ts` 可留空

### RaceChrono（CSV）/ GPX
- `Speed (km/h)` → Telemetry.speed_kph
- `Throttle pos (%)` → Telemetry.throttle_pct
- `Brake pos (%)`（若有）→ 可估算，v0 可先忽略或入備註
- `Longitude/Latitude` → Telemetry.lon_deg/lat_deg
- GPX trackpoints → 轉為 Telemetry（僅 lat/lon + ts_ms），供地圖展示

### Track maps（PDF/表）
- 使用官方 IM 名稱：`IM1a, IM1, IM2a, IM2, IM3a, FL`。
- 有地圖 → `Section.meta.source="map"`；無地圖 → 以 Laptrigger 或時間比例為 **fallback**。

## 匯入策略（包含 TRD R1/R2 長表格）
- **編碼**：支援 `utf-8` / `utf-8-sig` / `latin1`；自動去 BOM。
- **分隔**：`,` 與 `;` 皆可（barber 的 analysis/sections/ weather 多用分號）。
- **時間格式**：`m:ss.mmm`、`ss.mmm` → 毫秒；`timestamp` ISO8601Z → `ts_ms`。
- **TRD 長表格（R1/R2）**：欄位為  
  `expire_at, lap, meta_event, meta_session, meta_source, meta_time, original_vehicle_id, outing, telemetry_name, telemetry_value, timestamp, vehicle_id, vehicle_number`。  
  - 以 `timestamp` 聚合；`telemetry_name → telemetry_value` pivot 成 Telemetry 欄位（見上方對應）。
  - 多車混雜時，**建議每個 vehicle_id 各建一個 SessionBundle**；`vehicle_number==0` 以 `vehicle_id` 為唯一鍵。
- **容錯**：空字串→`None`；非數字→忽略/記警告；圈號 32768/遺失→保留原值並在事件偵測階段容忍離群（v0）。

## 事件偵測（v0 前置）
- **單圈異常**：移動中位數 + IQR/MAD；`z_like > 2.5` 為候選。
- **名次變化**：≤3 圈內變動 ≥2 名為候選；嚴重度由幅度與速度決定。
- **Top‑5 排序**：嚴重度 → 多樣性 → 新近性。

## AI‑Native（v0 可關閉）
- `AI_NATIVE=on|off`；on 時可產生 3 句敘事與簡短 Q&A；off 時完全以規則/統計輸出。
- README 註記 AI 用途、關閉方式與回退策略。

## 提交附註
- README 標註資料來源（TRD/MYLAPS/RaceChrono/GPX/Weather/Track maps）與已知陷阱（timestamp/meta_time、車號 000、圈號 32768）。
- 手機/平板/桌機可用；英文化文件；Devpost 欄位完整。
