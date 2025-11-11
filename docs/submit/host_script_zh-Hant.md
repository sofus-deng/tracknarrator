# 評審主持詞（30秒）
大家好，這是 **TrackNarrator**：把賽車遙測變成「事件卡片＋敘事＋教練建議」，並可一鍵匯出 JSON。
我先執行 `make demo` 產出示例，接著呼叫 `/session/{id}/summary?ai_native=on` 看前五大事件與敘事，再呼叫 `/export` 拿到可分享的 JSON 包。重點是：**決定論輸出**（可回歸測試、零隨機）、**雙語支援**（zh-Hant/en）、**一鍵重現**（demo 可離線）。
現在開始示範！